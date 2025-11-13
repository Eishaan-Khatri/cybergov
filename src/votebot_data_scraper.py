# cybergov_data_scraper.py  (FULL REPLACEMENT)
import json
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials as fb_credentials
from firebase_admin import firestore as admin_firestore
import httpx
from prefect import flow, task, get_run_logger
from prefect.blocks.system import Secret
from prefect.tasks import exponential_backoff
from prefect.server.schemas.states import Completed, Failed
import datetime
from prefect.server.schemas.filters import (
    FlowRunFilter,
    FlowRunFilterState,
    FlowRunFilterStateType,
    DeploymentFilter,
    DeploymentFilterId,
    FlowRunFilterName,
)
from prefect.client.orchestration import get_client
from prefect.client.schemas.objects import StateType
from utils.constants import (
    NETWORK_MAP,
    INFERENCE_SCHEDULE_DELAY_MINUTES,
    INFERENCE_TRIGGER_DEPLOYMENT_ID,
    ALLOWED_TRACK_IDS,
)
from utils.proposal_augmentation import generate_content_for_magis


# --- Exceptions ----------------------------------------------------------------
class ProposalFetchError(Exception):
    pass


class ProposalParseError(Exception):
    pass


class InvalidTrackError(Exception):
    pass


class FirestoreError(Exception):
    pass


# --- Firebase / Firestore helpers ----------------------------------------------
@task(name="Load Firestore Credentials", retries=1)
async def load_firestore_credentials() -> Dict[str, Any]:
    """
    Load Firestore service account JSON from Prefect Secret.
    Handles cases where the secret is stored as:
    - raw dict (Value type = JSON)
    - raw JSON string
    - triple-quoted JSON string
    """
    logger = get_run_logger()

    try:
        block = await Secret.load("firebase-credentials-json")
        raw = block.get()   # could be dict OR string
        logger.info(f"Loaded raw firebase credentials type: {type(raw)}")

        # Case 1: Prefect stored JSON directly as dict
        if isinstance(raw, dict):
            return raw

        # Case 2: Prefect stored JSON as string
        if isinstance(raw, str):
            cleaned = raw.strip()

            # Remove accidental triple quotes
            if cleaned.startswith('"""') and cleaned.endswith('"""'):
                cleaned = cleaned[3:-3].strip()

            # Remove accidental single quotes
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1].strip()

            return json.loads(cleaned)

        raise FirestoreError("Invalid firebase credentials format. Expected dict or JSON string.")

    except Exception as e:
        logger.error(f"Failed to load firebase credentials from Prefect Secret: {e}")
        raise FirestoreError("Failed to load firebase credentials") from e



def initialize_firebase_app_if_needed(creds_dict: Dict[str, Any]):
    """
    Initialize firebase_admin app with the provided service account dictionary.
    This is idempotent (safe to call multiple times).
    """
    if not firebase_admin._apps:
        cred = fb_credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    # firebase_admin firestore client will be used via admin_firestore.client()


def get_firestore_client():
    """
    Return a Firestore client via firebase_admin SDK.
    (Assumes firebase_admin.initialize_app() already called.)
    """
    return admin_firestore.client()


# --- Polkassembly fetch task ---------------------------------------------------
@task(
    name="Fetch Proposal JSON from Polkassembly ReferendumV2",
    retries=3,
    retry_delay_seconds=exponential_backoff(backoff_factor=10),
    retry_jitter_factor=0.2,
)
def fetch_polkassembly_proposal_data(network: str, proposal_id: int) -> Dict[str, Any]:
    """
    Fetches and parses proposal data from Polkassembly ReferendumV2 API endpoint.

    Endpoint format (determined from NETWORK_MAP entries):
        GET <base_url>/<proposal_id>
    where NETWORK_MAP[network] should point to the base ReferendumV2 path, e.g.
        https://paseo.polkassembly.io/api/v2/ReferendumV2
    """
    logger = get_run_logger()

    if network not in NETWORK_MAP:
        msg = f"Invalid network '{network}' - not present in NETWORK_MAP"
        logger.error(msg)
        raise ProposalFetchError(msg)

    base_url = NETWORK_MAP[network].rstrip("/")
    proposal_url = f"{base_url}/{proposal_id}"

    # retrieve user agent from Prefect Secret (synchronous here, task context)
    try:
        ua_block = Secret.load("cybergov-scraper-user-agent")
        user_agent = ua_block.get()
    except Exception:
        user_agent = "cybergov-scraper/1.0"

    headers = {"User-Agent": user_agent, "Accept": "application/json"}

    logger.info(f"Fetching Polkassembly data from: {proposal_url}")

    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(proposal_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched JSON for {network}/{proposal_id}")
            return data
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching {proposal_url}: {e} - status {getattr(e, 'response', None)}")
        raise ProposalFetchError(f"HTTP error fetching {proposal_url}") from e
    except httpx.RequestError as e:
        logger.error(f"Request error fetching {proposal_url}: {e}")
        raise ProposalFetchError(f"Request failed for {proposal_url}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from {proposal_url}: {e}")
        raise ProposalParseError(f"Invalid JSON from {proposal_url}") from e


# --- Firestore write/update tasks ---------------------------------------------
@task(name="Save Raw Data to Firestore", retries=2, retry_delay_seconds=5)
def save_raw_data_to_firestore(raw_data: Dict[str, Any], network: str, proposal_id: int):
    """
    Create (or overwrite) a Firestore document for this proposal with raw data.
    Document id: "{network}-{proposal_id}"
    """
    logger = get_run_logger()
    try:
        db = get_firestore_client()
        doc_id = f"{network}-{proposal_id}"
        doc_ref = db.collection("proposals").document(doc_id)

        now_iso = datetime.datetime.utcnow().isoformat() + "Z"

        payload = {
            "network": network,
            "proposalId": int(proposal_id),
            "status": "discovered",
            "discoveredAt": now_iso,
            "createdAt": now_iso,
            "updatedAt": now_iso,
            "createdBy": "cybergov-dispatcher",
            "lastModifiedBy": "cybergov-dispatcher",
            "version": 1,
            "files": {"rawData": raw_data},
        }

        doc_ref.set(payload)
        logger.info(f"Saved raw proposal data to Firestore: proposals/{doc_id}")
    except Exception as e:
        logger.error(f"Failed to save raw data to Firestore for {network}-{proposal_id}: {e}")
        raise FirestoreError("Failed to write raw data to Firestore") from e


@task(name="Archive previous Firestore version", retries=1)
def archive_previous_firestore_version(network: str, proposal_id: int):
    """
    If a document already exists, copy its current content to a 'versions' subcollection
    with a timestamp, then increment the 'version' field in the parent doc when new data is written.
    This is a minimal filesystem-like archive replacement for S3 mv.
    """
    logger = get_run_logger()
    try:
        db = get_firestore_client()
        doc_id = f"{network}-{proposal_id}"
        doc_ref = db.collection("proposals").document(doc_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            logger.info(f"No existing Firestore doc to archive for {doc_id}")
            return

        current = snapshot.to_dict()
        rev_ts = datetime.datetime.utcnow().isoformat() + "Z"
        versions_col = doc_ref.collection("versions")
        # use proposal version if available, else timestamped
        version_index = current.get("version", None)
        if version_index is None:
            version_index = rev_ts

        versions_col.document(str(version_index)).set({
            "archivedAt": rev_ts,
            "archivedBy": "cybergov-dispatcher",
            "payload": current,
        })
        logger.info(f"Archived existing document into proposals/{doc_id}/versions/{version_index}")
    except Exception as e:
        logger.error(f"Failed to archive Firestore doc for {network}-{proposal_id}: {e}")
        # non-fatal: allow processing to continue, but log
        raise FirestoreError("Failed to archive existing Firestore doc") from e


@task(name="Update Firestore with Generated Content", retries=2, retry_delay_seconds=5)
def update_firestore_with_content(content_md: str, network: str, proposal_id: int):
    """
    Update the proposal document to add generated content and bump version/updatedAt.
    """
    logger = get_run_logger()
    try:
        db = get_firestore_client()
        doc_id = f"{network}-{proposal_id}"
        doc_ref = db.collection("proposals").document(doc_id)

        now_iso = datetime.datetime.utcnow().isoformat() + "Z"

        update_payload = {
            "files.content": content_md,
            "updatedAt": now_iso,
            "lastModifiedBy": "cybergov-dispatcher",
        }

        doc_ref.update(update_payload)
        logger.info(f"Updated proposals/{doc_id} with generated content.")
    except Exception as e:
        logger.error(f"Failed to update Firestore content for {network}-{proposal_id}: {e}")
        raise FirestoreError("Failed to update Firestore with content") from e


# --- Enrichment and prompt generation (in-memory) -----------------------------
@task(name="Enrich proposal data (placeholder)")
def enrich_proposal_data(raw_proposal_data: Dict[str, Any], network: str, proposal_id: int):
    """
    Placeholder: enrich the raw proposal data with additional on-chain metadata.
    This function receives the raw data (dict) and should return an updated dict if needed.
    For now it returns the input unchanged.
    """
    logger = get_run_logger()
    logger.info(f"Enriching proposal {network}/{proposal_id} (placeholder)")
    # Implement enrichment logic as needed (identities, proposer stats, etc.)
    return raw_proposal_data


@task(name="Generate Prompt Content for LLM")
def generate_prompt_content(raw_proposal_data: Dict[str, Any], network: str) -> str:
    """
    Generate the markdown content for MAGIS based on the raw proposal data.
    Returns markdown string content.
    """
    logger = get_run_logger()
    logger.info(f"Generating content for {network} proposal {raw_proposal_data.get('proposalId')}")

    try:
        # openrouter api key (if used by generate_content_for_magis)
        openrouter_block = Secret.load("openrouter-api-key")
        openrouter_api_key = openrouter_block.get()
    except Exception:
        openrouter_api_key = None

    content_md = generate_content_for_magis(
        proposal_data=raw_proposal_data,
        logger=logger,
        openrouter_model="openrouter/anthropic/claude-sonnet-4",
        openrouter_api_key=openrouter_api_key,
        network=network,
    )

    logger.info("Content generation completed.")
    return content_md


# --- Validation helper --------------------------------------------------------
def extract_track_value(proposal_data: Dict[str, Any]) -> Optional[int]:
    """
    Extract track id from Polkassembly ReferendumV2 response.
    Tries commonly used fields in decreasing certainty order.
    """
    # Polkassembly store on-chain metadata in onchainData (often nested)
    try:
        # onchainData may be dict or list - handle common shapes
        onchain = proposal_data.get("onchainData") or {}
        # If onchain is a list with dicts, try first entry
        if isinstance(onchain, list) and len(onchain) > 0 and isinstance(onchain[0], dict):
            onchain = onchain[0]

        # common keys
        candidates = [
            onchain.get("track"),
            onchain.get("trackNumber"),
            onchain.get("track_number"),
            proposal_data.get("track_number"),
            proposal_data.get("track"),
        ]

        for val in candidates:
            if val is None:
                continue
            try:
                return int(val)
            except Exception:
                # if not an int, skip
                continue
    except Exception:
        pass
    return None


def validate_proposal_track_polkassembly(proposal_data: Dict[str, Any]) -> bool:
    """
    Validate that the proposal track (extracted) is in the allowed list.
    """
    logger = get_run_logger()
    track = extract_track_value(proposal_data)
    if track is None:
        logger.warning("Could not extract track id from proposal_data.")
        return False
    if track not in ALLOWED_TRACK_IDS:
        logger.warning(f"Proposal track {track} not in allowed tracks {ALLOWED_TRACK_IDS}")
        return False
    logger.info(f"✅ Proposal track {track} is valid")
    return True


# --- Prefect tasks to check/schedule remain unchanged -------------------------
@task
async def check_if_already_scheduled(proposal_id: int, network: str) -> bool:
    """
    Checks the Prefect API to see if a scraper run for this proposal
    already exists (in a non-failed state).
    """
    logger = get_run_logger()
    logger.info(
        f"Checking for existing flow runs for inference-{network}-{proposal_id}..."
    )

    async with get_client() as client:
        existing_runs = await client.read_flow_runs(
            flow_run_filter=FlowRunFilter(
                name=FlowRunFilterName(like_=f"inference-{network}-{proposal_id}"),
                state=FlowRunFilterState(
                    type=FlowRunFilterStateType(
                        any_=[
                            StateType.RUNNING,
                            StateType.COMPLETED,
                            StateType.PENDING,
                            StateType.SCHEDULED,
                        ]
                    )
                ),
            ),
            deployment_filter=DeploymentFilter(
                id=DeploymentFilterId(any_=[INFERENCE_TRIGGER_DEPLOYMENT_ID])
            ),
        )

    if existing_runs:
        logger.warning(
            f"Found {len(existing_runs)} existing inference run(s) for proposal {proposal_id} on '{network}'. Skipping scheduling."
        )
        return True

    logger.info(
        f"No existing inference runs found for proposal {proposal_id} on '{network}'. It's safe to schedule."
    )
    return False


@task
async def schedule_inference_task(proposal_id: int, network: str):
    """Schedules the MAGI inference flow to run in the future."""
    logger = get_run_logger()

    delay = datetime.timedelta(minutes=INFERENCE_SCHEDULE_DELAY_MINUTES)
    scheduled_time = datetime.datetime.now(datetime.timezone.utc) + delay
    logger.info(
        f"Scheduling MAGI inference for proposal {proposal_id} on '{network}' "
        f"to run at {scheduled_time.isoformat()}"
    )

    async with get_client() as client:
        await client.create_flow_run_from_deployment(
            name=f"inference-{network}-{proposal_id}",
            deployment_id=INFERENCE_TRIGGER_DEPLOYMENT_ID,
            parameters={"proposal_id": proposal_id, "network": network},
            # state=Scheduled(scheduled_time=scheduled_time)
        )


# --- Main flow ---------------------------------------------------------------
@flow(name="Fetch Proposal Data (Polkassembly to Firestore)")
async def fetch_proposal_data(
    network: str,
    proposal_id: int,
    schedule_inference: bool = True
):
    """
    Fetch relevant data for a ReferendumV2 proposal from Polkassembly,
    store raw data in Firestore, optionally generate LLM prompt content,
    and schedule inference.
    """
    logger = get_run_logger()

    if network not in NETWORK_MAP:
        logger.error(
            f"Invalid network '{network}'. Must be one of {list(NETWORK_MAP.keys())}"
        )
        return Failed(message=f"Invalid network: {network}")

    try:
        # 1) Load credentials & initialize Firebase
        logger.info("Loading Firestore credentials and initializing Firebase...")
        creds = await load_firestore_credentials()
        # load_firestore_credentials returns dict (task -> its return value is awaited)
        # But since we call from flow, value returned is already available.
        # ensure firebase app initialized (idempotent)
        initialize_firebase_app_if_needed(creds)

        # 2) Archive previous Firestore doc (if exists)
        logger.info("Archiving previous Firestore doc if exists...")
        archive_previous_firestore_version(network=network, proposal_id=proposal_id)

        # 3) Fetch raw data from Polkassembly
        logger.info(f"Fetching data for proposal {proposal_id} on {network}")
        raw_proposal_data = fetch_polkassembly_proposal_data(network=network, proposal_id=proposal_id)

        # 4) Save raw data to Firestore
        save_raw_data_to_firestore(raw_data=raw_proposal_data, network=network, proposal_id=proposal_id)

        # 5) Validate track
        logger.info("Validating proposal track...")
        if not validate_proposal_track_polkassembly(raw_proposal_data):
            track_id = extract_track_value(raw_proposal_data) or "unknown"
            message = f"Not scheduling inference for this proposal, track_id {track_id} is not delegated to CyberGov"
            logger.warning(message)
            return Completed(message=message)

        # 6) Enrich data (placeholder)
        enriched_data = enrich_proposal_data(raw_proposal_data=raw_proposal_data, network=network, proposal_id=proposal_id)

        # 7) Generate prompt content (in-memory)
        content_md = generate_prompt_content(raw_proposal_data=enriched_data, network=network)

        # 8) Update Firestore with generated content
        update_firestore_with_content(content_md=content_md, network=network, proposal_id=proposal_id)

        # 9) Optionally schedule inference
        if schedule_inference:
            logger.info("All good! Scheduling inference if not already scheduled.")
            is_already_scheduled = await check_if_already_scheduled(proposal_id=proposal_id, network=network)
            if not is_already_scheduled:
                await schedule_inference_task(proposal_id=proposal_id, network=network)
        else:
            logger.info("✅ Data fetching completed! Skipping inference scheduling (schedule_inference=False)")

        return Completed(message=f"Successfully processed {network}/{proposal_id}")

    except (ProposalFetchError, ProposalParseError, FirestoreError) as e:
        message = f"Failed processing {network} proposal {proposal_id}: {e}"
        logger.error(message, exc_info=True)
        return Failed(message=message)
    except Exception as e:
        message = f"Unexpected error processing {network} proposal {proposal_id}: {e}"
        logger.error(message, exc_info=True)
        return Failed(message=message)


# --- CLI entrypoint ----------------------------------------------------------
if __name__ == "__main__":
    import sys
    import asyncio

    if len(sys.argv) != 3:
        print("Usage: python cybergov_data_scraper.py <network> <proposal_id>")
        sys.exit(1)

    network_arg = sys.argv[1]
    proposal_id_arg = int(sys.argv[2])

    asyncio.run(
        fetch_proposal_data(
            network=network_arg,
            proposal_id=proposal_id_arg,
            schedule_inference=False
        )
    )
