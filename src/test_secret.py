import json

# Test loading Firebase credentials directly from file
with open("gov-bot-5fdc3-firebase-adminsdk-fbsvc-230323ffc9.json", "r") as f:
    creds = json.load(f)

print("TYPE:", type(creds))
print("Project ID:", creds.get("project_id"))
print("Client Email:", creds.get("client_email"))
print("Credentials loaded successfully!")
