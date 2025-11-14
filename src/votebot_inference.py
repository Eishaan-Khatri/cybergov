# src/votebot_inference.py
from typing import Tuple, Optional
from prefect import flow, task, get_run_logger
from prefect.blocks.system import Secret
import httpx
from datetime import datetime, timedelta, timezone
import time
from prefect.client.orchestration import get_client
from prefect.server.schemas.filters import (
    FlowRunFilter,
    FlowRunFilterState,
    FlowRunFilterStateType,
    DeploymentFilter,
    DeploymentFilterId,
    FlowRunFilterName,
)
from prefect.client.schemas.objects import StateType
import os

# To ensure transparency, this has to run on GitHub actions
# That way it is public, and the data + logic used to vote are transparent
from utils.constants import (
    VOTING_DEPLOYMENT_ID,
    VOTING_SCHEDULE_DELAY_MINUTES,
    GH_POLL_INTERVAL_SECONDS,
    GH_POLL_STATUS_TIMEOUT_SECONDS,
    GITHUB_REPO,
    INFERENCE_FIND_RUN_TIMEOUT_SECONDS,
    GH_WORKFLOW_NETWORK_MAPPING,
)


# ---------- Helper: get token from Prefect Secret or env ----------
def get_github_pat() -> str:
    """
    Try to read Prefect Secret 'github-pat' first (if Prefect is available).
    Otherwise fall back to environment variable GITHUB_PAT.

    Returns:
        str: GitHub Personal Access Token
    Raises:
        RuntimeError if token not found.
    """
    # 1) Prefer Prefect Secret (if Prefect is configured)
    try:
        block = Secret.load("github-pat")  # will raise if block missing
        val = block.get()
        if val:
            return val
    except Exception:
        # ignore - we will try env var next
        pass

    # 2) Environment variable fallback (useful for local CLI runs)

    env_val = os.getenv("GH_PAT")

    if env_val:
        return env_val

    # Not found — tell user what to do
    raise RuntimeError(
        "GitHub PAT not found. Create Prefect Secret 'github-pat' or set environment variable GITHUB_PAT."
    )


# ---------- Tasks (unchanged semantics but use get_github_pat, not .run) ----------
@task
def trigger_github_action_worker(proposal_id: int, network: str) -> Tuple[str, datetime]:
    """
    Trigger the configured GitHub workflow (via workflow_dispatch).
    Returns (workflow_file_name, trigger_time).
    """
    logger = get_run_logger()
    logger.info("Triggering GitHub Action for proposal %s on '%s'", proposal_id, network)

    pat = get_github_pat()

    workflow_file_name = GH_WORKFLOW_NETWORK_MAPPING.get(network)
    if not workflow_file_name:
        logger.error("No workflow mapping for network: %s", network)
        raise ValueError(f"No workflow mapping for network '{network}'")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{workflow_file_name}/dispatches"
    headers = {"Accept": "application/vnd.github.v3+json", "Authorization": f"Bearer {pat}"}
    data = {"ref": "main", "inputs": {"proposal_id": str(proposal_id)}}

    trigger_time = datetime.now(timezone.utc)
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, headers=headers, json=data)

    if resp.status_code == 204:
        logger.info("GitHub Action triggered (workflow: %s)", workflow_file_name)
        return workflow_file_name, trigger_time
    else:
        logger.error("Failed to trigger GitHub Action. Status=%s Body=%s", resp.status_code, resp.text)
        resp.raise_for_status()


@task
def find_workflow_run(network: str, proposal_id: int, workflow_file_name: str, trigger_time: datetime) -> int:
    """
    Poll list of workflow runs and return the run id matching our trigger (created after trigger_time).
    """
    logger = get_run_logger()
    logger.info("Searching for workflow run for '%s' (workflow=%s)...", network, workflow_file_name)

    pat = get_github_pat()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{workflow_file_name}/runs"
    headers = {"Accept": "application/vnd.github.v3+json", "Authorization": f"Bearer {pat}"}
    params = {"event": "workflow_dispatch", "branch": "main", "per_page": 10}

    start = datetime.now(timezone.utc)
    while datetime.now(timezone.utc) - start < timedelta(seconds=INFERENCE_FIND_RUN_TIMEOUT_SECONDS):
        with httpx.Client(timeout=30) as client:
            r = client.get(url, headers=headers, params=params)
            r.raise_for_status()
            runs = r.json().get("workflow_runs", [])

        for run in runs:
            created_at = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            display_title = (run.get("display_title") or run.get("name") or "").lower()
            if created_at >= trigger_time and f"#{proposal_id}" in display_title and network.lower() in display_title:
                logger.info("Found matching workflow run id=%s (created=%s)", run["id"], created_at.isoformat())
                return int(run["id"])

        logger.debug("No matching run yet. Sleeping %s seconds...", GH_POLL_INTERVAL_SECONDS)
        time.sleep(GH_POLL_INTERVAL_SECONDS)

    raise TimeoutError("Timed out waiting for workflow run to appear.")


@task
def poll_workflow_run_status(run_id: int) -> str:
    """
    Polls single workflow run status until completion. Returns 'success' or raises on failure/timeout.
    """
    logger = get_run_logger()
    logger.info("Polling workflow run status for id=%s", run_id)

    pat = get_github_pat()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs/{run_id}"
    headers = {"Accept": "application/vnd.github.v3+json", "Authorization": f"Bearer {pat}"}

    start = datetime.now(timezone.utc)
    while datetime.now(timezone.utc) - start < timedelta(seconds=GH_POLL_STATUS_TIMEOUT_SECONDS):
        with httpx.Client(timeout=30) as client:
            r = client.get(url, headers=headers)
            r.raise_for_status()
            run_data = r.json()

        status = run_data.get("status")
        conclusion = run_data.get("conclusion")
        logger.info("Workflow run %s status=%s conclusion=%s", run_id, status, conclusion)

        if status == "completed":
            if conclusion == "success":
                logger.info("Workflow run %s succeeded.", run_id)
                return "success"
            else:
                logger.error("Workflow run %s completed but did not succeed: %s", run_id, conclusion)
                raise RuntimeError(f"Workflow run {run_id} failed, conclusion={conclusion}")

        time.sleep(GH_POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"Timed out waiting for workflow run {run_id} to finish.")


@task
async def check_if_voting_already_scheduled(proposal_id: int, network: str) -> bool:
    """
    Query the Prefect API to find existing flow runs named vote-<network>-<proposal_id>
    in non-failed states for the configured VOTING_DEPLOYMENT_ID.
    """
    logger = get_run_logger()
    logger.info("Checking Prefect for existing vote runs for %s-%s", network, proposal_id)

    async with get_client() as client:
        existing_runs = await client.read_flow_runs(
            flow_run_filter=FlowRunFilter(
                name=FlowRunFilterName(like_=f"vote-{network}-{proposal_id}"),
                state=FlowRunFilterState(
                    type=FlowRunFilterStateType(
                        any_=[StateType.RUNNING, StateType.COMPLETED, StateType.PENDING, StateType.SCHEDULED]
                    )
                ),
            ),
            deployment_filter=DeploymentFilter(id=DeploymentFilterId(any_=[VOTING_DEPLOYMENT_ID])),
        )

    if existing_runs:
        logger.warning("Found %s existing vote run(s).", len(existing_runs))
        return True

    logger.info("No existing vote runs found; safe to schedule.")
    return False


@task
async def schedule_voting_task(proposal_id: int, network: str):
    logger = get_run_logger()
    scheduled_time = datetime.now(timezone.utc) + timedelta(minutes=VOTING_SCHEDULE_DELAY_MINUTES)
    logger.info("Scheduling vote flow for %s-%s at %s", network, proposal_id, scheduled_time.isoformat())

    async with get_client() as client:
        await client.create_flow_run_from_deployment(
            name=f"vote-{network}-{proposal_id}",
            deployment_id=VOTING_DEPLOYMENT_ID,
            parameters={"proposal_id": proposal_id, "network": network},
        )
    logger.info("Scheduled vote flow.")


@flow(name="GitHub Action Trigger and Monitor", log_prints=True)
async def github_action_trigger_and_monitor(proposal_id: int, network: str, schedule_vote: bool = True):
    """
    Top-level flow:
      1. trigger GitHub action (workflow_dispatch)
      2. find the corresponding run ID
      3. poll the run until success
      4. optionally schedule a vote in Prefect (if not already scheduled)
    """
    logger = get_run_logger()
    logger.info("Starting inference trigger for proposal=%s network=%s", proposal_id, network)

    wf_name, trigger_time = trigger_github_action_worker(proposal_id=proposal_id, network=network)
    run_id = find_workflow_run(network=network, proposal_id=proposal_id, workflow_file_name=wf_name, trigger_time=trigger_time)
    conclusion = poll_workflow_run_status(run_id=run_id)

    if conclusion != "success":
        raise RuntimeError("Triggered workflow did not succeed")

    if schedule_vote:
        already = await check_if_voting_already_scheduled(proposal_id=proposal_id, network=network)
        if not already:
            await schedule_voting_task(proposal_id=proposal_id, network=network)
            logger.info("Magi inference succeeded and vote scheduled.")
        else:
            logger.info("Magi inference succeeded but vote already scheduled.")
    else:
        logger.info("Magi inference succeeded; vote scheduling skipped (schedule_vote=False).")


# ---------- CLI wrapper so you can run this locally without Prefect server ----------
if __name__ == "__main__":
    import asyncio, sys

    if len(sys.argv) != 3:
        print("Usage: python src/votebot_inference.py <network> <proposal_id>")
        sys.exit(1)

    net = sys.argv[1]
    pid = int(sys.argv[2])

    # If you don't want to require Prefect server / deployments, run with schedule_vote=False
    asyncio.run(github_action_trigger_and_monitor(proposal_id=pid, network=net, schedule_vote=False))
