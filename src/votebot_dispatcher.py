# cybergov_dispatcher_v2.py
"""
Enhanced dispatcher with:
- Initial setup mode: fetch ALL active proposals
- Continuous mode: monitor for new proposals only
- Smart cache invalidation (24hr rule)
- Proper pipeline orchestration
"""

import datetime
from typing import List, Optional, Dict, Set
from prefect import flow, task, get_run_logger
import httpx
import os
import json
from prefect.blocks.system import String, Secret
from prefect.server.schemas.filters import (
    FlowRunFilter,
    FlowRunFilterState,
    FlowRunFilterStateType,
    DeploymentFilter,
    DeploymentFilterId,
    FlowRunFilterName,
)
from prefect.client.orchestration import get_client
from prefect.states import Scheduled
from prefect.client.schemas.objects import StateType
import firebase_admin
from firebase_admin import credentials as fb_credentials
from firebase_admin import firestore as admin_firestore

from utils.constants import (
    SCRAPING_SCHEDULE_DELAY_DAYS,
    DATA_SCRAPER_DEPLOYMENT_ID,
    CYBERGOV_PARAMS,
    NETWORK_MAP,
)


# ==================== Firestore Helpers ====================

def initialize_firebase_app_if_needed():
    """Initialize Firebase app if not already done."""
    if firebase_admin._apps:
        return
    
    try:
        # Try loading from Prefect Secret
        block = Secret.load("firebase-credentials-json")
        raw = block.get()
        
        if isinstance(raw, dict):
            creds_dict = raw
        else:
            # Clean and parse JSON string
            cleaned = raw.strip()
            if cleaned.startswith('"""') and cleaned.endswith('"""'):
                cleaned = cleaned[3:-3].strip()
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1].strip()
            creds_dict = json.loads(cleaned)
        
        cred = fb_credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        # Fallback to default credentials
        firebase_admin.initialize_app()


def get_firestore_client():
    """Return Firestore client."""
    initialize_firebase_app_if_needed()
    return admin_firestore.client()


# ==================== Active Proposals Fetcher ====================

@task(name="Fetch All Active Proposals", retries=3)
async def fetch_active_proposals(network: str) -> List[int]:
    """
    Fetch ALL currently active proposals from Polkassembly.
    
    Active statuses: 
    - DecisionDepositPlaced
    - Submitted  
    - Deciding
    - ConfirmStarted
    
    Returns list of proposal IDs.
    """
    logger = get_run_logger()
    
    if network not in NETWORK_MAP:
        logger.error(f"Invalid network: {network}")
        return []
    
    base_url = NETWORK_MAP[network].rstrip("/")
    
    # Build query with all active statuses
    statuses = ["DecisionDepositPlaced", "Submitted", "Deciding", "ConfirmStarted"]
    status_params = "&".join([f"status={s}" for s in statuses])
    
    all_proposal_ids: Set[int] = set()
    page = 1
    limit = 50
    
    logger.info(f"Fetching active proposals for {network}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                url = f"{base_url}?page={page}&limit={limit}&{status_params}"
                logger.debug(f"Fetching page {page}: {url}")
                
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                proposals = data.get("data", [])
                
                if not proposals:
                    break
                
                for prop in proposals:
                    # Extract proposal ID (could be 'id', 'proposalId', 'post_id', etc.)
                    prop_id = (
                        prop.get("post_id") or 
                        prop.get("proposalId") or 
                        prop.get("id")
                    )
                    if prop_id is not None:
                        all_proposal_ids.add(int(prop_id))
                
                logger.info(f"Page {page}: found {len(proposals)} proposals")
                
                # Check if more pages exist
                total = data.get("total", 0)
                if page * limit >= total:
                    break
                
                page += 1
        
        proposal_list = sorted(list(all_proposal_ids))
        logger.info(f"✅ Found {len(proposal_list)} active proposals for {network}")
        return proposal_list
        
    except Exception as e:
        logger.error(f"Failed to fetch active proposals for {network}: {e}", exc_info=True)
        return []


# ==================== Firestore Cache Checker ====================

@task(name="Check Proposal Cache Freshness")
def check_proposal_cache(network: str, proposal_id: int) -> Dict[str, any]:
    """
    Check if proposal exists in Firestore and if data is fresh.
    
    Returns dict with:
    - exists: bool
    - is_fresh: bool (< 24hrs old)
    - needs_rescrape: bool
    - last_updated: datetime or None
    """
    logger = get_run_logger()
    
    try:
        db = get_firestore_client()
        doc_id = f"{network}-{proposal_id}"
        doc_ref = db.collection("proposals").document(doc_id)
        snapshot = doc_ref.get()
        
        if not snapshot.exists:
            logger.info(f"Proposal {doc_id} not in cache")
            return {
                "exists": False,
                "is_fresh": False,
                "needs_rescrape": True,
                "last_updated": None
            }
        
        doc = snapshot.to_dict()
        updated_at_str = doc.get("updatedAt")
        
        if not updated_at_str:
            logger.warning(f"Proposal {doc_id} missing updatedAt timestamp")
            return {
                "exists": True,
                "is_fresh": False,
                "needs_rescrape": True,
                "last_updated": None
            }
        
        # Parse timestamp
        try:
            last_updated = datetime.datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
        except Exception:
            logger.warning(f"Invalid timestamp format: {updated_at_str}")
            return {
                "exists": True,
                "is_fresh": False,
                "needs_rescrape": True,
                "last_updated": None
            }
        
        # Check if data is < 24 hours old
        now = datetime.datetime.now(datetime.timezone.utc)
        age = now - last_updated
        is_fresh = age < datetime.timedelta(hours=24)
        
        logger.info(
            f"Proposal {doc_id}: exists={True}, "
            f"age={age.total_seconds()/3600:.1f}hrs, "
            f"is_fresh={is_fresh}"
        )
        
        return {
            "exists": True,
            "is_fresh": is_fresh,
            "needs_rescrape": not is_fresh,
            "last_updated": last_updated
        }
        
    except Exception as e:
        logger.error(f"Error checking cache for {network}-{proposal_id}: {e}")
        return {
            "exists": False,
            "is_fresh": False,
            "needs_rescrape": True,
            "last_updated": None
        }


# ==================== Latest Proposal ID Fetcher ====================

@task(name="Get Latest Proposal ID from Network")
async def get_latest_proposal_id(network: str) -> Optional[int]:
    """
    Fetch the latest proposal ID from the chain via sidecar API.
    This gives us the total referendum count.
    """
    logger = get_run_logger()
    
    try:
        network_sidecar_block = await Secret.load(f"{network}-sidecar-url")
        network_sidecar_url = network_sidecar_block.get()
    except Exception as e:
        logger.error(f"Failed to load sidecar URL for {network}: {e}")
        return None
    
    url = f"{network_sidecar_url}/pallets/referenda/storage/referendumCount"
    headers = {"Accept": "application/json"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=15.0)
            response.raise_for_status()
            
            data = response.json()
            last_proposal_id = data.get("value")
            
            if last_proposal_id is not None:
                last_proposal_id = int(last_proposal_id)
                logger.info(f"Latest proposal ID for {network}: {last_proposal_id}")
                return last_proposal_id
            
            return None
            
    except Exception as e:
        logger.error(f"Failed to fetch latest proposal ID for {network}: {e}")
        return None


# ==================== Last Processed Tracker ====================

@task(name="Get Last Processed ID from Firestore")
def get_last_processed_from_firestore(network: str) -> int:
    """
    Query Firestore to find the highest proposal ID we've processed.
    This replaces the S3 check.
    """
    logger = get_run_logger()
    
    try:
        db = get_firestore_client()
        
        # Query all proposal docs for this network
        query = (
            db.collection("proposals")
            .where("network", "==", network)
            .order_by("proposalId", direction=admin_firestore.Query.DESCENDING)
            .limit(1)
        )
        
        docs = query.stream()
        
        for doc in docs:
            data = doc.to_dict()
            prop_id = data.get("proposalId")
            if prop_id is not None:
                logger.info(f"Last processed proposal for {network}: {prop_id}")
                return int(prop_id)
        
        logger.info(f"No processed proposals found for {network}, starting from 0")
        return 0
        
    except Exception as e:
        logger.error(f"Error querying Firestore for last processed: {e}")
        return 0


# ==================== Scheduler Checks ====================

@task
async def check_if_scraper_already_scheduled(proposal_id: int, network: str) -> bool:
    """Check if scraper run already exists for this proposal."""
    logger = get_run_logger()
    
    async with get_client() as client:
        existing_runs = await client.read_flow_runs(
            flow_run_filter=FlowRunFilter(
                name=FlowRunFilterName(like_=f"scrape-{network}-{proposal_id}"),
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
                id=DeploymentFilterId(any_=[DATA_SCRAPER_DEPLOYMENT_ID])
            ),
        )
    
    if existing_runs:
        logger.info(f"Scraper already scheduled/completed for {network}-{proposal_id}")
        return True
    
    return False


@task
async def check_if_inference_already_scheduled(proposal_id: int, network: str) -> bool:
    """Check if inference run already exists for this proposal."""
    logger = get_run_logger()
    
    # Import here to avoid circular dependency
    from utils.constants import INFERENCE_TRIGGER_DEPLOYMENT_ID
    
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
        logger.info(f"Inference already scheduled/completed for {network}-{proposal_id}")
        return True
    
    return False


# ==================== Task Schedulers ====================

@task
async def schedule_scraping_task(proposal_id: int, network: str):
    """Schedule the data scraper flow."""
    logger = get_run_logger()
    
    delay = datetime.timedelta(days=SCRAPING_SCHEDULE_DELAY_DAYS)
    scheduled_time = datetime.datetime.now(datetime.timezone.utc) + delay
    
    logger.info(
        f"Scheduling scraper for {network}-{proposal_id} at {scheduled_time.isoformat()}"
    )
    
    async with get_client() as client:
        await client.create_flow_run_from_deployment(
            name=f"scrape-{network}-{proposal_id}",
            deployment_id=DATA_SCRAPER_DEPLOYMENT_ID,
            parameters={"proposal_id": proposal_id, "network": network},
            state=Scheduled(),
        )


@task
async def schedule_inference_task(proposal_id: int, network: str):
    """Schedule the inference (evaluation) flow directly."""
    logger = get_run_logger()
    
    from utils.constants import INFERENCE_TRIGGER_DEPLOYMENT_ID, INFERENCE_SCHEDULE_DELAY_MINUTES
    
    delay = datetime.timedelta(minutes=INFERENCE_SCHEDULE_DELAY_MINUTES)
    scheduled_time = datetime.datetime.now(datetime.timezone.utc) + delay
    
    logger.info(
        f"Scheduling inference for {network}-{proposal_id} at {scheduled_time.isoformat()}"
    )
    
    async with get_client() as client:
        await client.create_flow_run_from_deployment(
            name=f"inference-{network}-{proposal_id}",
            deployment_id=INFERENCE_TRIGGER_DEPLOYMENT_ID,
            parameters={"proposal_id": proposal_id, "network": network},
            state=Scheduled(),
        )


# ==================== Main Dispatcher Flow ====================

@flow(name="CyberGov Enhanced Dispatcher", log_prints=True)
async def cybergov_dispatcher_enhanced(
    networks: List[str] = ["paseo"],
    mode: str = "continuous",  # "initial_setup" or "continuous"
    proposal_id: Optional[int] = None,
    network: Optional[str] = None,
):
    """
    Enhanced dispatcher with two modes:
    
    1. initial_setup: Fetch ALL active proposals and process them
    2. continuous: Only check for new proposals since last run
    
    Also supports manual override mode if proposal_id + network provided.
    """
    logger = get_run_logger()
    
    # ========== Manual Override Mode ==========
    if proposal_id is not None and network is not None:
        logger.warning(f"MANUAL OVERRIDE: Processing single proposal {network}-{proposal_id}")
        
        cache_info = check_proposal_cache(network=network, proposal_id=proposal_id)
        
        if cache_info["is_fresh"]:
            logger.info(f"Cache is fresh for {network}-{proposal_id}, scheduling inference directly")
            already_scheduled = await check_if_inference_already_scheduled(
                proposal_id=proposal_id, network=network
            )
            if not already_scheduled:
                await schedule_inference_task(proposal_id=proposal_id, network=network)
        else:
            logger.info(f"Cache stale/missing for {network}-{proposal_id}, scheduling scraper first")
            already_scheduled = await check_if_scraper_already_scheduled(
                proposal_id=proposal_id, network=network
            )
            if not already_scheduled:
                await schedule_scraping_task(proposal_id=proposal_id, network=network)
        
        return
    
    # ========== Initial Setup Mode ==========
    if mode == "initial_setup":
        logger.info("🚀 INITIAL SETUP MODE: Fetching all active proposals")
        
        for net in networks:
            active_proposals = await fetch_active_proposals(network=net)
            
            if not active_proposals:
                logger.warning(f"No active proposals found for {net}")
                continue
            
            logger.info(f"Processing {len(active_proposals)} active proposals for {net}")
            
            for prop_id in active_proposals:
                cache_info = check_proposal_cache(network=net, proposal_id=prop_id)
                
                if cache_info["is_fresh"]:
                    # Data is fresh, go straight to inference
                    logger.info(f"{net}-{prop_id}: Using fresh cache, scheduling inference")
                    already_scheduled = await check_if_inference_already_scheduled(
                        proposal_id=prop_id, network=net
                    )
                    if not already_scheduled:
                        await schedule_inference_task(proposal_id=prop_id, network=net)
                else:
                    # Need to scrape first
                    logger.info(f"{net}-{prop_id}: Cache stale/missing, scheduling scraper")
                    already_scheduled = await check_if_scraper_already_scheduled(
                        proposal_id=prop_id, network=net
                    )
                    if not already_scheduled:
                        await schedule_scraping_task(proposal_id=prop_id, network=net)
        
        logger.info("✅ Initial setup complete")
        return
    
    # ========== Continuous Mode (default) ==========
    logger.info("🔄 CONTINUOUS MODE: Checking for new proposals")
    
    for net in networks:
        # Get last processed from Firestore
        last_known_id = get_last_processed_from_firestore(network=net)
        
        # Get latest from chain
        latest_id = await get_latest_proposal_id(network=net)
        
        if latest_id is None:
            logger.warning(f"Could not fetch latest proposal ID for {net}")
            continue
        
        # Apply minimum threshold from config
        min_threshold = CYBERGOV_PARAMS.get("min_proposal_id", {}).get(net, 0)
        start_from_id = max(last_known_id, min_threshold)
        
        if latest_id <= start_from_id:
            logger.info(f"No new proposals for {net} (latest={latest_id}, last_processed={start_from_id})")
            continue
        
        # Found new proposals
        new_proposal_ids = list(range(start_from_id + 1, latest_id + 1))
        logger.info(f"Found {len(new_proposal_ids)} new proposals for {net}: {new_proposal_ids}")
        
        for prop_id in new_proposal_ids:
            cache_info = check_proposal_cache(network=net, proposal_id=prop_id)
            
            if cache_info["is_fresh"]:
                logger.info(f"{net}-{prop_id}: Using fresh cache")
                already_scheduled = await check_if_inference_already_scheduled(
                    proposal_id=prop_id, network=net
                )
                if not already_scheduled:
                    await schedule_inference_task(proposal_id=prop_id, network=net)
            else:
                logger.info(f"{net}-{prop_id}: Scheduling scraper")
                already_scheduled = await check_if_scraper_already_scheduled(
                    proposal_id=prop_id, network=net
                )
                if not already_scheduled:
                    await schedule_scraping_task(proposal_id=prop_id, network=net)
    
    logger.info("✅ Continuous check complete")


# ==================== CLI Entrypoint ====================

if __name__ == "__main__":
    import sys
    import asyncio
    
    if len(sys.argv) == 1:
        # No args: run continuous mode for default networks
        asyncio.run(cybergov_dispatcher_enhanced(
            networks=["paseo"],
            mode="continuous"
        ))
    
    elif len(sys.argv) == 2:
        # One arg: mode selection
        mode = sys.argv[1]
        if mode not in ["initial_setup", "continuous"]:
            print("Usage: python cybergov_dispatcher_v2.py [initial_setup|continuous]")
            print("   OR: python cybergov_dispatcher_v2.py <network> <proposal_id>")
            sys.exit(1)
        
        asyncio.run(cybergov_dispatcher_enhanced(
            networks=["paseo"],
            mode=mode
        ))
    
    elif len(sys.argv) == 3:
        # Two args: manual override
        network_arg = sys.argv[1]
        proposal_id_arg = int(sys.argv[2])
        
        asyncio.run(cybergov_dispatcher_enhanced(
            network=network_arg,
            proposal_id=proposal_id_arg
        ))
    
    else:
        print("Usage: python cybergov_dispatcher_v2.py [initial_setup|continuous]")
        print("   OR: python cybergov_dispatcher_v2.py <network> <proposal_id>")
        sys.exit(1)