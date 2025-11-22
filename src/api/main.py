
import os
import sys
import logging
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Security, Depends, status, Header
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path so we can import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.firestore_helper import FirestoreHelper
from utils.weighted_decision_engine import compute_weighted_decision, list_available_templates
from utils.comment_generator import generate_comment, extract_agent_reasons
from utils.constants import GOV_BOT_VERSION

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GovBotAPI")

app = FastAPI(
    title="Gov Bot API Service",
    description="The Brain for DelegateX: Handles strategies, user bots, and voting logic.",
    version="1.0.0"
)

# --- Security & Headers ---
API_KEY_NAME = "x-passcode"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_passcode(api_key_header: str = Security(api_key_header)):
    """
    Validates the x-passcode header against the GOV_BOT_API_KEY env var.
    """
    expected_key = os.getenv("GOV_BOT_API_KEY")
    
    if not expected_key:
        logger.error("GOV_BOT_API_KEY not set in environment! Blocking all requests.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: API Key not set."
        )

    if api_key_header == expected_key:
        return api_key_header
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid passcode"
    )

def get_network(x_network: Optional[str] = Header(None)):
    """
    Extracts x-network header. Defaults to 'polkadot' if missing.
    """
    return x_network.lower() if x_network else "polkadot"

# Initialize Firestore Helper
# We rely on env vars for credentials (FIREBASE_CREDENTIALS_JSON or default)
try:
    db_helper = FirestoreHelper()
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {e}")
    db_helper = None

# --- Pydantic Models ---

class CreateBotRequest(BaseModel):
    user_id: str
    strategy_id: str = "neutral"
    signature_link: Optional[str] = None
    contact_link: Optional[str] = None
    wallet_address: Optional[str] = None # Kept for backward compatibility/internal use
    preferences: Optional[Dict[str, Any]] = None

class VoteRequest(BaseModel):
    user_id: str
    proposal_id: str
    # network is now handled via header, but keeping optional here just in case
    network: Optional[str] = None 
    dry_run: bool = False

class VoteResponse(BaseModel):
    user_id: str
    proposal_id: str
    decision: int # 0=Nay, 1=Aye, 2=Abstain
    reason: Dict[str, List[str]] # {caspar: [...], ...}
    comment: str
    
    # Extra metadata (optional but helpful for debugging)
    strategy_used: str
    confidence: str
    is_conclusive: bool

# --- Endpoints ---

@app.get("/")
def health_check():
    return {"status": "ok", "version": GOV_BOT_VERSION, "service": "GovBot API"}

@app.get("/strategies", dependencies=[Depends(get_passcode)])
def get_strategies():
    """
    List available voting strategies/templates.
    Protected by API Key.
    """
    templates = list_available_templates()
    return {
        "strategies": templates,
        "count": len(templates)
    }

@app.post("/create-bot", dependencies=[Depends(get_passcode)])
def create_user_bot(request: CreateBotRequest):
    """
    Configure a user's voting bot (Strategy, Wallet, etc.).
    Protected by API Key.
    """
    if not db_helper:
        raise HTTPException(status_code=500, detail="Database connection not available")

    try:
        # Validate strategy
        if request.strategy_id not in list_available_templates():
            raise HTTPException(status_code=400, detail=f"Invalid strategy: {request.strategy_id}")

        db_helper.create_user(
            user_id=request.user_id,
            strategy_id=request.strategy_id,
            wallet_address=request.wallet_address,
            signature_link=request.signature_link,
            contact_link=request.contact_link,
            preferences=request.preferences
        )
        return {"status": "success", "message": f"Bot configured for user {request.user_id} with strategy {request.strategy_id}"}
    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vote-delegate-x", response_model=VoteResponse, dependencies=[Depends(get_passcode)])
def calculate_vote(request: VoteRequest, network: str = Depends(get_network)):
    """
    The 'Brain' Endpoint:
    1. Fetches User Strategy
    2. Fetches Proposal Base Evaluation (3 Magi)
    3. Calculates Weighted Vote
    4. Saves Vote to User's Collection
    5. Returns Decision
    
    Protected by API Key.
    """
    if not db_helper:
        raise HTTPException(status_code=500, detail="Database connection not available")

    try:
        # 1. Fetch User Profile
        user_ref = db_helper.db.collection("users").document(request.user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User bot not found. Please call /create-bot first.")
        
        user_data = user_doc.to_dict()
        strategy_id = user_data.get("strategyId", "neutral")
        
        # 2. Fetch Proposal Base Evaluation
        # Use network from header, or fallback to request body if provided
        target_network = request.network or network
        firestore_proposal_id = f"{target_network}-{request.proposal_id}"
        proposal_ref = db_helper.db.collection("proposals").document(firestore_proposal_id)
        proposal_snap = proposal_ref.get()
        
        if not proposal_snap.exists:
            raise HTTPException(status_code=404, detail=f"Proposal {firestore_proposal_id} not found or not yet evaluated.")
        
        proposal_data = proposal_snap.to_dict()
        
        # Extract Agent Votes from the 'files.outputs' or similar path
        # We need to look for the JSON outputs of balthazar, caspar, melchior
        files = proposal_data.get("files", {})
        outputs = files.get("outputs", {})
        
        agent_votes = []
        missing_agents = []
        
        for agent in ["balthazar", "caspar", "melchior"]:
            agent_file_data = outputs.get(agent)
            if not agent_file_data:
                missing_agents.append(agent)
                continue
            
            # The content is stored as a string in Firestore
            try:
                content_str = agent_file_data.get("content", "{}")
                if isinstance(content_str, dict):
                    content_json = content_str
                else:
                    content_json = json.loads(content_str)
                    
                decision = content_json.get("decision", "Abstain")
                agent_votes.append({"agent": agent, "decision": decision})
            except Exception as e:
                logger.error(f"Failed to parse agent {agent} data: {e}")
                missing_agents.append(agent)

        if not agent_votes:
             raise HTTPException(status_code=400, detail="No AI evaluations found for this proposal. Has it been processed?")

        # 3. Calculate Weighted Vote
        result = compute_weighted_decision(
            agent_votes=agent_votes,
            template_name=strategy_id
        )
        
        # 3b. Generate Comment
        # We need to reconstruct the vote_data dict expected by generate_comment
        # or we can just pass the result if we adjust the function.
        # The current generate_comment expects a dict with "final_decision" and "weighted_decision_metadata"
        
        # Let's extract agent reasons first
        agent_reasons = extract_agent_reasons(proposal_data)
        
        # Construct a temporary vote_data dict for the generator
        temp_vote_data = {
            "final_decision": result.final_decision,
            "weighted_decision_metadata": {
                "strategy_used": result.template_used,
                "decision_reasoning": result.decision_reasoning
            }
        }
        
        try:
            generated_comment = generate_comment(temp_vote_data, agent_reasons)
        except Exception as e:
            logger.error(f"Comment generation failed: {e}")
            generated_comment = result.decision_reasoning # Fallback

        # 4. Save Vote (if not dry run)
        if not request.dry_run:
            provenance = {
                "api_version": "1.0.0",
                "timestamp": datetime.utcnow().isoformat(),
                "triggered_by": "api_request"
            }
            
            # We need some proposal metadata for the snapshot
            # Try to get it from rawData if available, or top level fields
            raw_data = files.get("rawData", {})
            if isinstance(raw_data, str):
                 try:
                     raw_data = json.loads(raw_data)
                 except:
                     raw_data = {}
            
            # Fallback for title/amount
            proposal_snapshot_data = {
                "title": raw_data.get("title") or proposal_data.get("title", "Unknown Title"),
                "onChainInfo": raw_data.get("onChainInfo", {}),
                "requestedAmount": raw_data.get("requestedAmount", "0"),
                "trackNumber": raw_data.get("trackNumber", "0")
            }

            db_helper.save_user_vote(
                user_id=request.user_id,
                proposal_id=request.proposal_id,
                weighted_result=result,
                proposal_data=proposal_snapshot_data,
                provenance=provenance
            )
        
        # 5. Return Response
        # Map decision to int
        vote_map = {"Nay": 0, "Aye": 1, "Abstain": 2}
        vote_val = vote_map.get(result.final_decision, 2)
        
        return VoteResponse(
            user_id=request.user_id,
            proposal_id=request.proposal_id,
            decision=vote_val,
            reason=agent_reasons,
            comment=generated_comment,
            strategy_used=result.template_used,
            confidence=result.confidence,
            is_conclusive=(result.confidence in ["Strong", "Moderate"])
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Vote calculation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
