
# CyberGov Configuration Guide

Complete guide to configuring CyberGov for your environment.

## 📋 Table of Contents

1. [Environment Variables](#environment-variables)
2. [Prefect Blocks (Secrets)](#prefect-blocks-secrets)
3. [Constants Configuration](#constants-configuration)
4. [Network-Specific Settings](#network-specific-settings)
5. [GitHub Actions Secrets](#github-actions-secrets)
6. [S3 Storage Setup](#s3-storage-setup)
7. [Substrate Accounts Setup](#substrate-accounts-setup)

---

## Environment Variables

### Required for Local Inference

```bash
# Proposal Information
PROPOSAL_ID=1234                    # The proposal ID to process
NETWORK=polkadot                    # Network: polkadot, kusama, or paseo

# S3 Storage Configuration
S3_BUCKET_NAME=cybergov             # Your S3 bucket name
S3_ACCESS_KEY_ID=SCWXXXXXXXXXX      # S3 access key
S3_ACCESS_KEY_SECRET=xxxxxxxx       # S3 secret key
S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud  # S3 endpoint

# LLM API
OPENROUTER_API_KEY=sk-or-v1-xxxxx  # OpenRouter API key for LLM access
```

### Optional for GitHub Actions

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxx      # GitHub Personal Access Token
GITHUB_REPOSITORY=YourUser/cybergov # Your forked repository
GITHUB_RUN_ID=123456789            # Auto-set by GitHub Actions
GITHUB_SHA=abc123def456            # Auto-set by GitHub Actions
```

### Setting Environment Variables

**Windows (PowerShell)**:
```powershell
$env:PROPOSAL_ID="1234"
$env:NETWORK="polkadot"
$env:S3_BUCKET_NAME="cybergov"
# ... etc
```

**Linux/Mac (Bash)**:
```bash
export PROPOSAL_ID=1234
export NETWORK=polkadot
export S3_BUCKET_NAME=cybergov
# ... etc
```

**Using .env file** (recommended):
```bash
# Create .env file
cat > .env << EOF
PROPOSAL_ID=1234
NETWORK=polkadot
S3_BUCKET_NAME=cybergov
S3_ACCESS_KEY_ID=xxx
S3_ACCESS_KEY_SECRET=xxx
S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud
OPENROUTER_API_KEY=sk-or-v1-xxx
EOF

# Load with python-dotenv
pip install python-dotenv
```

---

## Prefect Blocks (Secrets)

Prefect uses "blocks" to store configuration and secrets securely.

### Creating Blocks via CLI

```bash
# 1. Start Prefect server
cd infra
docker-compose up -d

# 2. Register block types
prefect block register -m prefect.blocks.system

# 3. Create secrets
prefect block create secret \
  --name "polkadot-rpc-url" \
  --value "wss://rpc.polkadot.io"

prefect block create secret \
  --name "polkadot-sidecar-url" \
  --value "https://polkadot-sidecar.example.com"

prefect block create secret \
  --name "polkadot-cybergov-mnemonic" \
  --value "your twelve word mnemonic phrase here for proxy account"

prefect block create secret \
  --name "polkadot-cybergov-parent-pubkey" \
  --value "13Q56KnUmLNe8fomKD3hoY38ZwLKZgRGdY4RTovRNFjMSwKw"
```

### Creating Blocks via UI

1. Open Prefect UI: http://localhost:4200
2. Navigate to "Blocks" in sidebar
3. Click "+" to create new block
4. Select "Secret" type
5. Enter block name and value
6. Click "Create"

### Required Blocks

#### Network-Specific (repeat for each network)

```python
# RPC Endpoints
{network}-rpc-url              # WebSocket RPC endpoint
{network}-sidecar-url          # Substrate Sidecar HTTP endpoint

# Account Information
{network}-cybergov-mnemonic    # Proxy account mnemonic (12 words)
{network}-cybergov-parent-pubkey  # Main account public key

# Examples:
polkadot-rpc-url = "wss://rpc.polkadot.io"
kusama-rpc-url = "wss://kusama-rpc.polkadot.io"
paseo-rpc-url = "wss://paseo-rpc.polkadot.io"
```

#### S3 Storage

```python
# Read-only access (for most operations)
scaleway-bucket-name           # Bucket name
scaleway-s3-endpoint-url       # S3 endpoint URL
scaleway-access-key-id         # Access key ID
scaleway-secret-access-key     # Secret access key

# Write access (for scraper and inference)
scaleway-write-access-key-id   # Write access key ID
scaleway-write-secret-access-key  # Write secret key
```

#### API Keys

```python
openrouter-api-key             # OpenRouter API key
github-pat                     # GitHub Personal Access Token
cybergov-scraper-user-agent    # User agent for API requests
```

### Block Naming Convention

- Use lowercase with hyphens
- Network-specific blocks: `{network}-{purpose}`
- Global blocks: `{service}-{purpose}`

---

## Constants Configuration

Edit `src/utils/constants.py` to customize system behavior.

### Proposal Processing

```python
CYBERGOV_PARAMS = {
    # Skip proposals before this ID
    "min_proposal_id": {
        "polkadot": 1740,
        "kusama": 585,
        "paseo": 103
    },
    # Future: max_proposal_id for testing
    "max_proposal_id": {}
}
```

### Scheduling Delays

```python
# Wait 2 days before scraping (let proposer add details)
SCRAPING_SCHEDULE_DELAY_DAYS = 2

# Wait 30 minutes between steps
INFERENCE_SCHEDULE_DELAY_MINUTES = 30
VOTING_SCHEDULE_DELAY_MINUTES = 30
COMMENTING_SCHEDULE_DELAY_MINUTES = 30
```

### GitHub Configuration

```python
GITHUB_REPO = "KarimJedda/cybergov"

GH_WORKFLOW_NETWORK_MAPPING = {
    "polkadot": "run_polkadot.yml",
    "kusama": "run_kusama.yml",
    "paseo": "run_paseo.yml"
}

# Polling intervals
GH_POLL_INTERVAL_SECONDS = 15
INFERENCE_FIND_RUN_TIMEOUT_SECONDS = 300
GH_POLL_STATUS_TIMEOUT_SECONDS = 700
```

### Prefect Deployment IDs

```python
# These are UUIDs generated when you deploy workflows
DATA_SCRAPER_DEPLOYMENT_ID = "00b42f26-0ccf-4d18-b127-a273b2006838"
INFERENCE_TRIGGER_DEPLOYMENT_ID = "327f24eb-04db-4d30-992d-cce455b4b241"
VOTING_DEPLOYMENT_ID = "c202dacd-2461-4aac-8ac1-83dd9f27ccc5"
COMMENTING_DEPLOYMENT_ID = "36bdbe3d-82c0-4a80-a7c3-8ee5e485c51c"
```

**Note**: You'll need to update these after deploying your own workflows.

### Network Endpoints

```python
NETWORK_MAP = {
    "polkadot": "https://polkadot-api.subsquare.io/gov2/referendums",
    "kusama": "https://kusama-api.subsquare.io/gov2/referendums",
    "paseo": "https://paseo-api.subsquare.io/gov2/referendums"
}
```

### Voting Configuration

```python
# Conviction levels (lock periods)
CONVICTION_MAPPING = {
    0: "None",      # No lock
    1: "Locked1x",  # 7 days
    2: "Locked2x",  # 14 days
    3: "Locked3x",  # 28 days
    4: "Locked4x",  # 56 days
    5: "Locked5x",  # 112 days
    6: "Locked6x"   # 224 days
}

# Voting power (in Planck/smallest unit)
voting_power = {
    "paseo": 1 * 10**10,      # 1 PAS
    "polkadot": 1 * 10**10,   # 1 DOT
    "kusama": 1 * 10**12      # 1 KSM
}
```

### Allowed Tracks

```python
# Only vote on these governance tracks
ALLOWED_TRACK_IDS = [
    2,   # Wish for change
    11,  # Treasurer
    30,  # Small Tipper
    31,  # Big Tipper
    32,  # Small Spender
    33,  # Medium spender
    34,  # Big Spender
]
```

---

## Network-Specific Settings

### Polkadot Configuration

```python
# In constants.py
CYBERGOV_POLKADOT_MAIN_PUBKEY = "13Q56KnUmLNe8fomKD3hoY38ZwLKZgRGdY4RTovRNFjMSwKw"
CYBERGOV_POLKADOT_PROXY_PUBKEY = "15DbGtWxaAU6tDPpdZhP9QyVZZWdSXaGCjD88cRZhhdCKTjE"

# Prefect blocks needed:
polkadot-rpc-url = "wss://rpc.polkadot.io"
polkadot-sidecar-url = "https://polkadot-sidecar.example.com"
polkadot-cybergov-mnemonic = "your mnemonic"
polkadot-cybergov-parent-pubkey = "13Q56KnUmLNe8fomKD3hoY38ZwLKZgRGdY4RTovRNFjMSwKw"
```

### Kusama Configuration

```python
# In constants.py
CYBERGOV_KUSAMA_MAIN_PUBKEY = "EyPcJsHXv86Snch8GokZLZyrucug3gK1RAghBD2HxvL1YRZ"
CYBERGOV_KUSAMA_PROXY_PUBKEY = "GWUyiyVmA6pbubhM9h7A6qGDqTJKJK3L3YoJsWe6DP7m67a"

# Prefect blocks needed:
kusama-rpc-url = "wss://kusama-rpc.polkadot.io"
kusama-sidecar-url = "https://kusama-sidecar.example.com"
kusama-cybergov-mnemonic = "your mnemonic"
kusama-cybergov-parent-pubkey = "EyPcJsHXv86Snch8GokZLZyrucug3gK1RAghBD2HxvL1YRZ"
```

### Paseo Configuration (Testnet)

```python
# In constants.py
CYBERGOV_PASEO_MAIN_PUBKEY = "13Q56KnUmLNe8fomKD3hoY38ZwLKZgRGdY4RTovRNFjMSwKw"
CYBERGOV_PASEO_PROXY_PUBKEY = "14zNhvyLnJKtYRmfptavEPWHuV9qEXZQNqXCjDmnvjrg1gtL"

# Prefect blocks needed:
paseo-rpc-url = "wss://paseo-rpc.polkadot.io"
paseo-sidecar-url = "https://paseo-sidecar.example.com"
paseo-cybergov-mnemonic = "your mnemonic"
paseo-cybergov-parent-pubkey = "13Q56KnUmLNe8fomKD3hoY38ZwLKZgRGdY4RTovRNFjMSwKw"
```

---

## GitHub Actions Secrets

Configure these in your GitHub repository settings.

### Repository Settings

1. Go to your forked repository
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"

### Required Secrets

```yaml
# S3 Storage
S3_BUCKET_NAME: cybergov
S3_ACCESS_KEY_ID: SCWXXXXXXXXXX
S3_ACCESS_KEY_SECRET: xxxxxxxxxxxxxxxx
S3_ENDPOINT_URL: https://s3.fr-par.scw.cloud

# LLM API
OPENROUTER_API_KEY: sk-or-v1-xxxxxxxxxxxxxxxx
```

### Workflow Configuration

Edit `.github/workflows/run_polkadot.yml`:

```yaml
name: 'Polkadot - Cybergov Proposal Processor'

on:
  workflow_dispatch:
    inputs:
      proposal_id:
        description: 'The proposal ID to process'
        required: true
        type: string

jobs:
  cybergov:
    runs-on: ubuntu-latest
    environment: Cybergov  # Optional: use GitHub Environments
    
    env:
      PROPOSAL_ID: ${{ inputs.proposal_id }}
      NETWORK: 'polkadot'
      S3_BUCKET_NAME: ${{ secrets.S3_BUCKET_NAME }}
      S3_ACCESS_KEY_ID: ${{ secrets.S3_ACCESS_KEY_ID }}
      S3_ACCESS_KEY_SECRET: ${{ secrets.S3_ACCESS_KEY_SECRET }}
      S3_ENDPOINT_URL: ${{ secrets.S3_ENDPOINT_URL }}
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

---

## S3 Storage Setup

### Scaleway Object Storage (Recommended)

1. **Create Account**: https://console.scaleway.com/
2. **Create Bucket**:
   - Go to Object Storage
   - Click "Create bucket"
   - Name: `cybergov` (or your choice)
   - Region: `fr-par` (Paris) or nearest
   - Visibility: Public (for transparency)

3. **Generate API Keys**:
   - Go to IAM → API Keys
   - Create new key
   - Save Access Key ID and Secret Key

4. **Configure CORS** (optional, for web access):
```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET"],
      "AllowedHeaders": ["*"]
    }
  ]
}
```

### AWS S3 (Alternative)

```bash
# Create bucket
aws s3 mb s3://cybergov --region us-east-1

# Set public read policy
aws s3api put-bucket-policy --bucket cybergov --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::cybergov/*"
  }]
}'

# Endpoint URL
S3_ENDPOINT_URL=https://s3.amazonaws.com
```

### Testing S3 Connection

```python
import s3fs

s3 = s3fs.S3FileSystem(
    key="YOUR_ACCESS_KEY",
    secret="YOUR_SECRET_KEY",
    client_kwargs={"endpoint_url": "https://s3.fr-par.scw.cloud"}
)

# Test connection
print(s3.ls("cybergov"))
```

---

## Substrate Accounts Setup

### Creating Accounts

**Option 1: Polkadot.js Extension**
1. Install: https://polkadot.js.org/extension/
2. Create new account
3. Save mnemonic securely
4. Export account JSON (optional)

**Option 2: Subkey CLI**
```bash
# Install subkey
cargo install --force subkey --git https://github.com/paritytech/substrate

# Generate new account
subkey generate

# Output:
# Secret phrase: word1 word2 ... word12
# Public key (hex): 0x...
# Account ID: 0x...
# SS58 Address: 5...
```

**Option 3: Python (substrate-interface)**
```python
from substrateinterface import Keypair

# Generate new keypair
keypair = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())

print(f"Mnemonic: {keypair.mnemonic}")
print(f"Address: {keypair.ss58_address}")
```

### Setting Up Proxy Relationship

1. **Fund Main Account**: Transfer DOT/KSM to main account
2. **Create Proxy Account**: Generate new account (keep mnemonic)
3. **Set Up Proxy**:
   - Go to https://polkadot.js.org/apps
   - Connect main account
   - Developer → Extrinsics
   - Select: `proxy.addProxy`
   - Parameters:
     - `delegate`: Proxy account address
     - `proxyType`: Governance
     - `delay`: 0
   - Sign and submit

4. **Verify Proxy**:
   - Developer → Chain state
   - Select: `proxy.proxies`
   - Input: Main account address
   - Should show proxy account in list

### Account Security

**Main Account**:
- Keep mnemonic OFFLINE (paper backup)
- Use hardware wallet if possible
- Never expose in code or logs

**Proxy Account**:
- Store mnemonic in Prefect secrets
- Can be rotated if compromised
- Limited to governance actions only

---

## Configuration Checklist

### Local Development

- [ ] Python 3.11+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with all variables
- [ ] S3 bucket created and accessible
- [ ] OpenRouter API key obtained
- [ ] Test scraper works
- [ ] Test inference works locally

### Production Deployment

- [ ] Prefect server running (`docker-compose up -d`)
- [ ] All Prefect blocks created
- [ ] Substrate accounts created
- [ ] Proxy relationship established
- [ ] Accounts funded
- [ ] GitHub Actions secrets configured
- [ ] Workflows deployed (`prefect deploy --all`)
- [ ] Test manual workflow trigger
- [ ] Monitor first automated run

### Security Checklist

- [ ] Mnemonics stored securely (not in code)
- [ ] API keys in secrets (not in code)
- [ ] S3 bucket has appropriate permissions
- [ ] GitHub secrets configured correctly
- [ ] Proxy account has limited permissions
- [ ] Main account mnemonic offline

---

## Troubleshooting Configuration

### "Cannot connect to S3"

```bash
# Test S3 credentials
python -c "
import s3fs
s3 = s3fs.S3FileSystem(
    key='YOUR_KEY',
    secret='YOUR_SECRET',
    client_kwargs={'endpoint_url': 'YOUR_ENDPOINT'}
)
print(s3.ls('YOUR_BUCKET'))
"
```

### "Prefect block not found"

```bash
# List all blocks
prefect block ls

# Check specific block
prefect block inspect secret/polkadot-rpc-url
```

### "GitHub Actions failing"

1. Check secrets are set: Settings → Secrets → Actions
2. Verify workflow file syntax
3. Check GitHub Actions logs
4. Test locally first

### "Transaction failed"

1. Check account balance
2. Verify proxy relationship
3. Test RPC endpoint
4. Check network connectivity

---

## Advanced Configuration

### Custom LLM Models

Edit `src/utils/run_magi_eval.py`:

```python
magi_llms = {
    "balthazar": "openai/gpt-4o",
    "melchior": "anthropic/claude-3-opus",  # Change model
    "caspar": "openrouter/x-ai/grok-2",     # Change model
}
```

### Custom Vote Logic

Edit `src/cybergov_evaluate_single_proposal_and_vote.py`:

```python
def consolidate_vote(analysis_files, ...):
    # Modify truth table logic here
    if aye == 3:
        final_decision = "Aye"
    # ... your custom logic
```

### Custom Scheduling

Edit `src/utils/constants.py`:

```python
SCRAPING_SCHEDULE_DELAY_DAYS = 1  # Faster scraping
INFERENCE_SCHEDULE_DELAY_MINUTES = 5  # Faster inference
```

---

## Configuration Templates

### .env Template

```bash
# Copy this to .env and fill in your values
PROPOSAL_ID=
NETWORK=
S3_BUCKET_NAME=
S3_ACCESS_KEY_ID=
S3_ACCESS_KEY_SECRET=
S3_ENDPOINT_URL=
OPENROUTER_API_KEY=
GITHUB_TOKEN=
GITHUB_REPOSITORY=
```

### Prefect Blocks Script

```bash
#!/bin/bash
# create_prefect_blocks.sh

# S3 Storage
prefect block create string --name "scaleway-bucket-name" --value "cybergov"
prefect block create string --name "scaleway-s3-endpoint-url" --value "https://s3.fr-par.scw.cloud"
prefect block create secret --name "scaleway-access-key-id" --value "YOUR_KEY"
prefect block create secret --name "scaleway-secret-access-key" --value "YOUR_SECRET"

# Polkadot
prefect block create secret --name "polkadot-rpc-url" --value "wss://rpc.polkadot.io"
prefect block create secret --name "polkadot-sidecar-url" --value "YOUR_SIDECAR_URL"
prefect block create secret --name "polkadot-cybergov-mnemonic" --value "YOUR_MNEMONIC"
prefect block create secret --name "polkadot-cybergov-parent-pubkey" --value "YOUR_PUBKEY"

# Add more as needed...
```

---

**Next Steps**: After configuration, proceed to testing with QUICK_START_GUIDE.md
