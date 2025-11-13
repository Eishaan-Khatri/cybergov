# Firebase Migration Guide - Complete S3 to Firebase Replacement

This guide shows you **exactly** where S3 is used in CyberGov and how to replace it with Firebase Storage and Firestore.

---

## 📊 Current S3 Usage Overview

### What S3 Does in CyberGov

S3 is used as the **primary data storage layer** for:

1. **Proposal data** (raw JSON from Subsquare API)
2. **LLM analysis results** (3 JSON files per proposal)
3. **Vote decisions** (consolidated vote.json)
4. **Manifest files** (cryptographic attestation)
5. **Content markdown** (formatted proposal for LLMs)

### S3 File Structure

```
s3://bucket-name/
└── proposals/
    └── {network}/          # polkadot, kusama, paseo
        └── {proposal_id}/  # e.g., 1234
            ├── raw_subsquare_data.json
            ├── content.md
            ├── llm_analyses/
            │   ├── balthazar.json
            │   ├── melchior.json
            │   └── caspar.json
            ├── vote.json
            └── manifest.json
```

---

## 🔥 Firebase Replacement Strategy

### Firebase Services You'll Need

1. **Firebase Storage** - For file storage (replaces S3 file operations)
2. **Firestore** - For structured data and metadata (optional but recommended)
3. **Firebase Admin SDK** - For Python backend operations

### Proposed Firebase Structure

```
Firebase Storage:
/proposals/
  /{network}/
    /{proposal_id}/
      /raw_subsquare_data.json
      /content.md
      /llm_analyses/
        /balthazar.json
        /melchior.json
        /caspar.json
      /vote.json
      /manifest.json

Firestore (optional, for faster queries):
proposals/
  {network}_{proposal_id}/
    - network: "polkadot"
    - proposalId: 1234
    - status: "voted"
    - finalDecision: "Aye"
    - timestamp: <timestamp>
    - manifestHash: "abc123..."
    - files: {
        rawData: "proposals/polkadot/1234/raw_subsquare_data.json",
        vote: "proposals/polkadot/1234/vote.json",
        ...
      }
```

---

## 📝 Step-by-Step Migration

### Step 1: Setup Firebase Project

```bash
# Install Firebase Admin SDK
pip install firebase-admin

# Create a Firebase project at https://console.firebase.google.com/
# Download service account key JSON
# Save it as firebase-credentials.json (add to .gitignore!)
```

### Step 2: Create Firebase Helper Module

Create `src/utils/firebase_storage.py`:

```python
import firebase_admin
from firebase_admin import credentials, storage, firestore
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class FirebaseStorage:
    """Replacement for S3FileSystem using Firebase Storage"""
    
    def __init__(self, credentials_path: str = None, bucket_name: str = None):
        """
        Initialize Firebase Storage client.
        
        Args:
            credentials_path: Path to Firebase service account JSON
            bucket_name: Firebase Storage bucket name (e.g., 'your-app.appspot.com')
        """
        if not firebase_admin._apps:
            cred_path = credentials_path or os.getenv('FIREBASE_CREDENTIALS_PATH')
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                'storageBucket': bucket_name or os.getenv('FIREBASE_BUCKET_NAME')
            })
        
        self.bucket = storage.bucket()
        self.db = firestore.client()  # Optional: for metadata
    
    def exists(self, path: str) -> bool:
        """Check if a file exists in Firebase Storage"""
        blob = self.bucket.blob(path)
        return blob.exists()
    
    def open(self, path: str, mode: str = 'r'):
        """
        Open a file from Firebase Storage.
        Returns a file-like object.
        """
        blob = self.bucket.blob(path)
        
        if 'r' in mode:
            # Read mode
            content = blob.download_as_bytes()
            if 'b' in mode:
                from io import BytesIO
                return BytesIO(content)
            else:
                from io import StringIO
                return StringIO(content.decode('utf-8'))
        elif 'w' in mode:
            # Write mode - return a custom writer
            return FirebaseWriter(blob, mode)
        else:
            raise ValueError(f"Unsupported mode: {mode}")
    
    def upload(self, local_path: str, remote_path: str):
        """Upload a local file to Firebase Storage"""
        blob = self.bucket.blob(remote_path)
        blob.upload_from_filename(local_path)
        logger.info(f"Uploaded {local_path} to {remote_path}")
    
    def download(self, remote_path: str, local_path: str):
        """Download a file from Firebase Storage to local"""
        blob = self.bucket.blob(remote_path)
        blob.download_to_filename(local_path)
        logger.info(f"Downloaded {remote_path} to {local_path}")
    
    def ls(self, path: str, detail: bool = False, refresh: bool = False):
        """List files in a directory"""
        # Ensure path ends with /
        if not path.endswith('/'):
            path += '/'
        
        blobs = self.bucket.list_blobs(prefix=path)
        
        if detail:
            return [{'name': blob.name, 'size': blob.size} for blob in blobs]
        else:
            return [blob.name for blob in blobs]
    
    def mv(self, source: str, destination: str, recursive: bool = False):
        """Move/rename a file or directory"""
        if recursive:
            # Move directory
            blobs = self.bucket.list_blobs(prefix=source)
            for blob in blobs:
                new_name = blob.name.replace(source, destination, 1)
                self.bucket.rename_blob(blob, new_name)
        else:
            # Move single file
            blob = self.bucket.blob(source)
            self.bucket.rename_blob(blob, destination)
        
        logger.info(f"Moved {source} to {destination}")


class FirebaseWriter:
    """File-like writer for Firebase Storage"""
    
    def __init__(self, blob, mode):
        self.blob = blob
        self.mode = mode
        self.buffer = []
    
    def write(self, data):
        """Write data to buffer"""
        self.buffer.append(data)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Upload on close"""
        if exc_type is None:
            content = ''.join(self.buffer)
            if 'b' in self.mode:
                self.blob.upload_from_string(content, content_type='application/octet-stream')
            else:
                self.blob.upload_from_string(content, content_type='text/plain')
```

---

## 🔄 File-by-File Changes

### 1. `src/cybergov_data_scraper.py`

**Lines to change:**

```python
# OLD (lines 8-9):
import s3fs

# NEW:
from utils.firebase_storage import FirebaseStorage

# OLD (lines 44-56):
async def load_s3_credentials():
    """Load S3 credentials from Prefect blocks."""
    s3_bucket_block = await Secret.load("scaleway-bucket-name")
    endpoint_block = await Secret.load("scaleway-s3-endpoint-url")
    access_key_block = await Secret.load("scaleway-write-access-key-id")
    secret_key_block = await Secret.load("scaleway-write-secret-access-key")
    
    return {
        "s3_bucket": s3_bucket_block.value,
        "endpoint_url": endpoint_block.value,
        "access_key": access_key_block.get(),
        "secret_key": secret_key_block.get(),
    }

# NEW:
async def load_firebase_credentials():
    """Load Firebase credentials from Prefect blocks."""
    creds_path_block = await Secret.load("firebase-credentials-path")
    bucket_block = await Secret.load("firebase-bucket-name")
    
    return {
        "credentials_path": creds_path_block.get(),
        "bucket_name": bucket_block.value,
    }

# OLD (lines 58-67):
def setup_s3_filesystem(access_key: str, secret_key: str, endpoint_url: str):
    """Create and return an S3FileSystem instance."""
    return s3fs.S3FileSystem(
        key=access_key,
        secret=secret_key,
        client_kwargs={
            "endpoint_url": endpoint_url,
        },
    )

# NEW:
def setup_firebase_storage(credentials_path: str, bucket_name: str):
    """Create and return a FirebaseStorage instance."""
    return FirebaseStorage(
        credentials_path=credentials_path,
        bucket_name=bucket_name
    )

# OLD (lines 127-145):
@task(name="Save JSON to S3", retries=2, retry_delay_seconds=5)
def save_to_s3(
    data: Dict[str, Any],
    s3_bucket: str,
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    full_s3_path: str,
):
    """Saves the extracted JSON data to a specified S3 path."""
    logger = get_run_logger()
    logger.info(f"Saving JSON to {full_s3_path}...")
    try:
        s3 = s3fs.S3FileSystem(
            key=access_key,
            secret=secret_key,
            client_kwargs={
                "endpoint_url": endpoint_url,
            },
        )

        with s3.open(full_s3_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"✅ Success! Proposal data saved to {full_s3_path}")
    except Exception as e:
        logger.error(f"❌ Failed to write to S3 at {full_s3_path}: {e}")
        raise

# NEW:
@task(name="Save JSON to Firebase", retries=2, retry_delay_seconds=5)
def save_to_firebase(
    data: Dict[str, Any],
    credentials_path: str,
    bucket_name: str,
    full_path: str,
):
    """Saves the extracted JSON data to Firebase Storage."""
    logger = get_run_logger()
    logger.info(f"Saving JSON to {full_path}...")
    try:
        fb = FirebaseStorage(credentials_path, bucket_name)

        with fb.open(full_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"✅ Success! Proposal data saved to {full_path}")
    except Exception as e:
        logger.error(f"❌ Failed to write to Firebase at {full_path}: {e}")
        raise
```

**Update all function calls** that use `s3_bucket`, `endpoint_url`, `access_key`, `secret_key` to use `credentials_path` and `bucket_name` instead.

---

### 2. `src/cybergov_evaluate_single_proposal_and_vote.py`

```python
# OLD (line 4):
import s3fs

# NEW:
from utils.firebase_storage import FirebaseStorage

# OLD (lines 217-232):
def setup_s3_and_workspace(config):
    """
    Initialize S3 filesystem and create local workspace.
    Returns S3 filesystem, proposal S3 path, and local workspace path.
    """
    proposal_id = config["PROPOSAL_ID"]
    network = config["NETWORK"]
    s3_bucket = config["S3_BUCKET_NAME"]

    try:
        s3 = s3fs.S3FileSystem(
            key=config["S3_ACCESS_KEY_ID"],
            secret=config["S3_ACCESS_KEY_SECRET"],
            client_kwargs={"endpoint_url": config["S3_ENDPOINT_URL"]},
            asynchronous=False,
            loop=None,
        )
        s3.ls(s3_bucket, detail=False, refresh=True)
    except Exception as e:
        logger.error("Something went wrong during S3 initialization")
        sys.exit(1)

    proposal_s3_path = f"{s3_bucket}/proposals/{network}/{proposal_id}"
    logger.info(f"Working with S3 path: {proposal_s3_path}")

    local_workspace = Path("workspace")
    local_workspace.mkdir(exist_ok=True)
    
    return s3, proposal_s3_path, local_workspace, proposal_id, network

# NEW:
def setup_firebase_and_workspace(config):
    """
    Initialize Firebase Storage and create local workspace.
    Returns Firebase storage, proposal path, and local workspace path.
    """
    proposal_id = config["PROPOSAL_ID"]
    network = config["NETWORK"]

    try:
        fb = FirebaseStorage(
            credentials_path=config["FIREBASE_CREDENTIALS_PATH"],
            bucket_name=config["FIREBASE_BUCKET_NAME"]
        )
        # Test connection
        fb.ls("proposals/", detail=False, refresh=True)
    except Exception as e:
        logger.error("Something went wrong during Firebase initialization")
        sys.exit(1)

    proposal_path = f"proposals/{network}/{proposal_id}"
    logger.info(f"Working with Firebase path: {proposal_path}")

    local_workspace = Path("workspace")
    local_workspace.mkdir(exist_ok=True)
    
    return fb, proposal_path, local_workspace, proposal_id, network
```

**Replace all `s3` variable references with `fb` (Firebase) throughout the file.**

---

### 3. `src/cybergov_voter.py`

```python
# OLD (line 13):
import s3fs

# NEW:
from utils.firebase_storage import FirebaseStorage

# OLD (lines 38-49):
def setup_s3_filesystem(access_key: str, secret_key: str, endpoint_url: str) -> s3fs.S3FileSystem:
    """
    Initialize S3 filesystem with consistent configuration.
    """
    return s3fs.S3FileSystem(
        key=access_key,
        secret=secret_key,
        client_kwargs={"endpoint_url": endpoint_url},
        asynchronous=False,
        loop=None,
    )

# NEW:
def setup_firebase_storage(credentials_path: str, bucket_name: str) -> FirebaseStorage:
    """
    Initialize Firebase Storage with consistent configuration.
    """
    return FirebaseStorage(
        credentials_path=credentials_path,
        bucket_name=bucket_name
    )

# OLD (lines 52-66):
async def load_s3_credentials() -> tuple[str, str, str, str]:
    """
    Load S3 credentials from Prefect blocks.
    Returns: (s3_bucket, endpoint_url, access_key, secret_key)
    """
    s3_bucket_block = await String.load("scaleway-bucket-name")
    endpoint_block = await String.load("scaleway-s3-endpoint-url")
    access_key_block = await Secret.load("scaleway-access-key-id")
    secret_key_block = await Secret.load("scaleway-secret-access-key")

    return (
        s3_bucket_block.value,
        endpoint_block.value,
        access_key_block.get(),
        secret_key_block.get(),
    )

# NEW:
async def load_firebase_credentials() -> tuple[str, str]:
    """
    Load Firebase credentials from Prefect blocks.
    Returns: (credentials_path, bucket_name)
    """
    creds_path_block = await Secret.load("firebase-credentials-path")
    bucket_block = await String.load("firebase-bucket-name")

    return (
        creds_path_block.get(),
        bucket_block.value,
    )
```

---

### 4. `src/cybergov_commenter.py`

```python
# OLD (line 6):
import s3fs

# NEW:
from utils.firebase_storage import FirebaseStorage

# Replace all s3fs.S3FileSystem instantiations with FirebaseStorage
```

---

### 5. Update `src/utils/helpers.py`

```python
# OLD (lines 18-27):
def get_config_from_env() -> Dict[str, str]:
    logger = setup_logging()

    required_vars = [
        "PROPOSAL_ID",
        "NETWORK",
        "S3_BUCKET_NAME",
        "S3_ACCESS_KEY_ID",
        "S3_ACCESS_KEY_SECRET",
        "S3_ENDPOINT_URL",
    ]

# NEW:
def get_config_from_env() -> Dict[str, str]:
    logger = setup_logging()

    required_vars = [
        "PROPOSAL_ID",
        "NETWORK",
        "FIREBASE_CREDENTIALS_PATH",
        "FIREBASE_BUCKET_NAME",
    ]
```

---

## 🔐 Environment Variables Changes

### OLD (.env file):
```bash
# S3 Storage
S3_BUCKET_NAME=your-bucket-name
S3_ACCESS_KEY_ID=your-access-key
S3_ACCESS_KEY_SECRET=your-secret-key
S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud
```

### NEW (.env file):
```bash
# Firebase Storage
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
FIREBASE_BUCKET_NAME=your-app.appspot.com
```

---

## 🧪 Testing Your Migration

### Test Script

Create `test_firebase_migration.py`:

```python
from utils.firebase_storage import FirebaseStorage
import json

def test_firebase_operations():
    """Test basic Firebase operations"""
    
    # Initialize
    fb = FirebaseStorage(
        credentials_path="./firebase-credentials.json",
        bucket_name="your-app.appspot.com"
    )
    
    # Test write
    test_data = {"test": "data", "proposal_id": 9999}
    test_path = "proposals/test/9999/test.json"
    
    with fb.open(test_path, "w") as f:
        json.dump(test_data, f, indent=2)
    
    print("✅ Write test passed")
    
    # Test read
    with fb.open(test_path, "r") as f:
        loaded_data = json.load(f)
    
    assert loaded_data == test_data
    print("✅ Read test passed")
    
    # Test exists
    assert fb.exists(test_path)
    print("✅ Exists test passed")
    
    # Test list
    files = fb.ls("proposals/test/9999/")
    assert test_path in files
    print("✅ List test passed")
    
    print("\n🎉 All Firebase tests passed!")

if __name__ == "__main__":
    test_firebase_operations()
```

---

## 📋 Migration Checklist

- [ ] Create Firebase project
- [ ] Download service account credentials
- [ ] Install `firebase-admin` package
- [ ] Create `firebase_storage.py` helper
- [ ] Update `cybergov_data_scraper.py`
- [ ] Update `cybergov_evaluate_single_proposal_and_vote.py`
- [ ] Update `cybergov_voter.py`
- [ ] Update `cybergov_commenter.py`
- [ ] Update `utils/helpers.py`
- [ ] Update environment variables
- [ ] Update Prefect secrets (if using Prefect)
- [ ] Test with `test_firebase_migration.py`
- [ ] Run end-to-end test with a real proposal
- [ ] Update documentation

---

## 🚨 Important Notes

1. **Firebase Storage URLs**: Firebase Storage files are accessible via URLs like:
   ```
   https://firebasestorage.googleapis.com/v0/b/{bucket}/o/{path}?alt=media
   ```

2. **Security Rules**: Set up Firebase Storage security rules:
   ```javascript
   rules_version = '2';
   service firebase.storage {
     match /b/{bucket}/o {
       match /proposals/{network}/{proposalId}/{allPaths=**} {
         allow read: if true;  // Public read
         allow write: if request.auth != null;  // Authenticated write
       }
     }
   }
   ```

3. **Cost**: Firebase has a free tier, but monitor usage:
   - Storage: 5GB free
   - Downloads: 1GB/day free
   - Uploads: 20K/day free

4. **CDN**: Firebase Storage has built-in CDN, no need for separate CDN setup

---

## 🎯 Summary

**Files that need changes:**
1. `src/cybergov_data_scraper.py` - 6 functions
2. `src/cybergov_evaluate_single_proposal_and_vote.py` - 4 functions
3. `src/cybergov_voter.py` - 3 functions
4. `src/cybergov_commenter.py` - 1 function
5. `src/utils/helpers.py` - 1 function

**New files to create:**
1. `src/utils/firebase_storage.py` - Firebase wrapper class

**Configuration changes:**
- Replace 4 S3 env vars with 2 Firebase env vars
- Update Prefect secrets (if using)
- Add Firebase service account JSON

The migration is straightforward - Firebase Storage API is similar to S3, so most changes are just swapping the client initialization and credential loading!
