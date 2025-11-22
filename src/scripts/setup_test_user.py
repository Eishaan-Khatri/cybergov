import os
import sys
import logging
import json
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.firestore_helper import FirestoreHelper
from utils.weighted_decision_engine import WeightedDecisionResult

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SetupUser")

def load_firestore_credentials_from_prefect():
    """
    Load Firestore credentials from Prefect Secret (same as your scraper).
    """
    try:
        from prefect.blocks.system import Secret
        
        block = Secret.load("firebase-credentials-json")
        raw = block.get()
        
        logger.info(f"Loaded raw firebase credentials type: {type(raw)}")
        
        # Case 1: Already a dict
        if isinstance(raw, dict):
            return raw
        
        # Case 2: JSON string
        if isinstance(raw, str):
            cleaned = raw.strip()
            
            # Remove triple quotes if present
            if cleaned.startswith('"""') and cleaned.endswith('"""'):
                cleaned = cleaned[3:-3].strip()
            
            # Remove single quotes if present
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1].strip()
            
            return json.loads(cleaned)
        
        raise ValueError("Invalid firebase credentials format")
        
    except Exception as e:
        logger.error(f"Failed to load firebase credentials from Prefect: {e}")
        raise

def setup_test_user():
    """
    Creates a test user and a dummy vote to verify the Firestore schema.
    """
    print("🚀 Starting User Setup...")
    
    # 1. Load credentials from Prefect Secret (same as scraper)
    try:
        print("Loading Firestore credentials from Prefect Secret...")
        creds = load_firestore_credentials_from_prefect()
        
        # Initialize Firebase with the credentials
        import firebase_admin
        from firebase_admin import credentials
        
        if not firebase_admin._apps:
            cred = credentials.Certificate(creds)
            firebase_admin.initialize_app(cred)
        
        print("✅ Firestore connected via Prefect Secret.")
        
    except Exception as e:
        print(f"❌ Failed to connect to Firestore: {e}")
        print("Make sure 'firebase-credentials-json' Prefect Secret is configured.")
        return

    # 2. Initialize Helper (now Firebase is already initialized)
    try:
        db_helper = FirestoreHelper()
        print("✅ FirestoreHelper initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize FirestoreHelper: {e}")
        return

    # 3. Define Test Data
    USER_ID = "user_test_123"
    STRATEGY = "aggressive"
    PROPOSAL_ID = "1796"
    
    # 4. Create User Profile
    print(f"Creating/Updating User: {USER_ID}...")
    db_helper.create_user(
        user_id=USER_ID,
        strategy_id=STRATEGY,
        wallet_address="5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
        preferences={"notifications": True}
    )
    print("✅ User profile created.")

    # 5. Create a Dummy Vote
    print(f"Creating Vote for Proposal {PROPOSAL_ID}...")
    
    dummy_result = WeightedDecisionResult(
        final_decision="Aye",
        weighted_scores={"Aye": 0.8, "Nay": 0.2, "Abstain": 0.0},
        margin=0.6,
        confidence="Strong",
        rules_triggered=["weighted_decision"],
        decision_reasoning="Test vote created by setup script.",
        template_used=STRATEGY,
        template_weights={"balthazar": 1.0},
        agent_votes=[{"agent": "balthazar", "vote": "Aye", "weight_applied": 1.0}]
    )
    
    dummy_proposal_data = {
        "title": "Test Proposal for ink! Alliance",
        "requestedAmount": "10000",
        "trackNumber": "10"
    }
    
    dummy_provenance = {
        "script": "setup_test_user.py",
        "timestamp": datetime.utcnow().isoformat()
    }

    db_helper.save_user_vote(
        user_id=USER_ID,
        proposal_id=PROPOSAL_ID,
        weighted_result=dummy_result,
        proposal_data=dummy_proposal_data,
        provenance=dummy_provenance
    )
    
    print(f"✅ Vote saved to users/{USER_ID}/votes/{PROPOSAL_ID}")
    print("🎉 Success! The schema is valid and working.")

if __name__ == "__main__":
    setup_test_user()