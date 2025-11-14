import firebase_admin
from firebase_admin import credentials, firestore
import json

# Load firebase credentials the same way your flow does
with open("L:\cybergov\gov-bot-5fdc3-firebase-adminsdk-fbsvc-230323ffc9.json", "r") as f:
    creds_data = json.load(f)

# Initialize
cred = credentials.Certificate(creds_data)
firebase_admin.initialize_app(cred)
db = firestore.client()

network = "polkadot"
proposal_id = "1770"

doc_ref = db.collection("proposals").document(f"{network}-{proposal_id}")
snapshot = doc_ref.get()

if not snapshot.exists:
    print("Document does not exist")
    exit()

current = snapshot.to_dict()

print("\n=== Raw document from Firestore ===\n")
print(json.dumps(current, indent=2, default=str))
