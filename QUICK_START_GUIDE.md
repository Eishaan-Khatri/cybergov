# CyberGov - Quick Start Guide

## 🎯 What is CyberGov?

CyberGov is an autonomous AI governance system that uses three independent LLM agents (inspired by Evangelion's MAGI system) to analyze and vote on Polkadot governance proposals. All execution is transparent and verifiable through public GitHub Actions logs and cryptographic attestation.

---

## 🚀 Quick Setup (Local Testing)

### Prerequisites

```bash
# Required
- Python 3.11+
- Git
- S3-compatible storage account (Scaleway, AWS, etc.)
- OpenRouter API key (for LLM access)

# Optional (for full deployment)
- Docker & Docker Compose (for Prefect)
- GitHub account (for transparent inference)
```

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/KarimJedda/cybergov.git
cd cybergov

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Proposal to analyze
PROPOSAL_ID=1234
NETWORK=polkadot  # or kusama, paseo

# S3 Storage (required)
S3_BUCKET_NAME=your-bucket-name
S3_ACCESS_KEY_ID=your-access-key
S3_ACCESS_KEY_SECRET=your-secret-key
S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud  # Scaleway example

# LLM API (required for inference)
OPENROUTER_API_KEY=your-openrouter-key

# GitHub (optional, for production inference)
GITHUB_TOKEN=your-github-pat
GITHUB_REPOSITORY=YourUsername/cybergov
```

### 3. Test Individual Components

#### Test 1: Scrape Proposal Data

```bash
# Fetch proposal data from Subsquare
python src/cybergov_data_scraper.py polkadot 1234
```

**Expected Output**:
- Creates `workspace/` directory
- Downloads proposal data to S3
- Generates `content.md` for LLM analysis

**Check S3**:
```
s3://your-bucket/proposals/polkadot/1234/
├── raw_subsquare_data.json
└── content.md
```

#### Test 2: Run LLM Inference (Local)

```bash
# Set environment variables
export PROPOSAL_ID=1234
export NETWORK=polkadot
export S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud
export S3_BUCKET_NAME=your-bucket
export S3_ACCESS_KEY_ID=your-key
export S3_ACCESS_KEY_SECRET=your-secret
export OPENROUTER_API_KEY=your-key

# Run inference
python src/cybergov_evaluate_single_proposal_and_vote.py
```

**Expected Output**:
```
CyberGov V0 ... initializing.
01 - Performing pre-flight data checks...
✅ raw_subsquare.json found and validated.
✅ content.md found.
✅ All local system prompts found.
02 - Running MAGI V0 Evaluation...
--- Processing Magi: BALTHAZAR ---
  Compiling agent using model: openai/gpt-4o...
  Running inference for balthazar...
✅ Generated analysis for balthazar
--- Processing Magi: MELCHIOR ---
  ...
03 - Consolidating vote...
✅ Vote consolidated into workspace/vote.json.
04 - Attesting, signing, and uploading outputs...
🎉 CyberGov V0 processing complete!
```

**Check S3**:
```
s3://your-bucket/proposals/polkadot/1234/
├── raw_subsquare_data.json
├── content.md
├── llm_analyses/
│   ├── balthazar.json
│   ├── melchior.json
│   └── caspar.json
├── vote.json
└── manifest.json
```

#### Test 3: Inspect Results

```bash
# View individual agent decisions
cat workspace/llm_analyses/balthazar.json
cat workspace/llm_analyses/melchior.json
cat workspace/llm_analyses/caspar.json

# View final consolidated vote
cat workspace/vote.json
```

**Example `vote.json`**:
```json
{
  "timestamp_utc": "2024-01-01T12:00:00Z",
  "is_conclusive": true,
  "final_decision": "Aye",
  "is_unanimous": false,
  "summary_rationale": "HTML formatted rationale...",
  "votes_breakdown": [
    {"model": "balthazar", "decision": "Aye", "confidence": null},
    {"model": "melchior", "decision": "Aye", "confidence": null},
    {"model": "caspar", "decision": "Nay", "confidence": null}
  ]
}
```

---

## 🔐 Setting Up for Production

### 1. Configure Substrate Accounts

You need two accounts per network:

1. **Main Account** - Holds funds, sets up proxy
2. **Proxy Account** - Signs transactions

```bash
# Generate new accounts (or use existing)
# Main account: Keep mnemonic OFFLINE
# Proxy account: Store mnemonic in Prefect Secrets

# On Polkadot/Kusama, set up proxy relationship:
# 1. Go to https://polkadot.js.org/apps
# 2. Developer > Extrinsics
# 3. proxy.addProxy(delegate, proxyType, delay)
#    - delegate: Your proxy account address
#    - proxyType: Governance
#    - delay: 0
```

### 2. Set Up Prefect (Orchestration)

```bash
# Start Prefect server
cd infra
docker-compose up -d

# Access UI
open http://localhost:4200

# Create Prefect blocks (secrets)
# Via UI or CLI:
prefect block register -m prefect.blocks.system

# Create secrets for each network
prefect block create secret \
  --name "polkadot-rpc-url" \
  --value "wss://rpc.polkadot.io"

prefect block create secret \
  --name "polkadot-sidecar-url" \
  --value "https://polkadot-sidecar.example.com"

prefect block create secret \
  --name "polkadot-cybergov-mnemonic" \
  --value "your proxy account mnemonic"

# ... repeat for kusama, paseo
```

### 3. Deploy Workflows

```bash
# Deploy all workflows
prefect deploy --all

# Or deploy individually
prefect deploy src/cybergov_dispatcher.py:cybergov_dispatcher_flow
prefect deploy src/cybergov_data_scraper.py:fetch_proposal_data
prefect deploy src/cybergov_inference.py:github_action_trigger_and_monitor
prefect deploy src/cybergov_voter.py:vote_on_opengov_proposal
prefect deploy src/cybergov_commenter.py:post_magi_comment_to_subsquare
```

### 4. Configure GitHub Actions

```bash
# 1. Fork the repository
# 2. Add repository secrets:
#    - S3_BUCKET_NAME
#    - S3_ACCESS_KEY_ID
#    - S3_ACCESS_KEY_SECRET
#    - S3_ENDPOINT_URL
#    - OPENROUTER_API_KEY

# 3. Enable GitHub Actions
# 4. Test manual trigger:
#    Actions > Polkadot - Cybergov Proposal Processor > Run workflow
```

---

## 📊 Understanding the Output

### Individual Agent Analysis

Each agent produces a JSON file with:

```json
{
  "model_name": "openai/gpt-4o",
  "timestamp_utc": "2024-01-01T12:00:00Z",
  "decision": "Aye",  // or "Nay", "Abstain"
  "confidence": null,
  "rationale": "This proposal strengthens Polkadot's competitive advantage...",
  "raw_api_response": {}
}
```

### Vote Consolidation

The system uses a truth table to consolidate votes:

```
2 Aye + 1 Abstain = Aye
2 Nay + 1 Abstain = Nay
2 Aye + 1 Nay = Abstain
1 Aye + 1 Nay + 1 Abstain = Abstain
3 Aye = Aye (unanimous)
3 Nay = Nay (unanimous)
```

### Manifest (Attestation)

The manifest provides cryptographic proof:

```json
{
  "provenance": {
    "github_repository": "KarimJedda/cybergov",
    "github_run_id": "12345",
    "github_commit_sha": "abc123",
    "timestamp_utc": "2024-01-01T12:00:00Z"
  },
  "inputs": [
    {
      "logical_name": "raw_subsquare_data",
      "s3_path": "s3://bucket/proposals/polkadot/1234/raw_subsquare_data.json",
      "hash": "sha256:abc123..."
    }
  ],
  "outputs": [
    {
      "logical_name": "vote",
      "s3_path": "s3://bucket/proposals/polkadot/1234/vote.json",
      "hash": "sha256:def456..."
    }
  ]
}
```

**Verification**:
1. Download manifest from S3
2. Calculate SHA256: `sha256(manifest.json)`
3. Compare with on-chain remark in transaction
4. Verify all input/output hashes

---

## 🧪 Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_cybergov_voter.py::TestCreateVoteParameters -v

# Run with coverage
pytest --cov=src tests/
```

---

## 🔍 Debugging Tips

### Check Logs

```bash
# Prefect logs (if using Prefect)
prefect flow-run logs <flow-run-id>

# GitHub Actions logs
# Go to: https://github.com/YourUsername/cybergov/actions

# Local logs
# Check console output when running scripts
```

### Common Issues

#### "S3 file not found"
```bash
# Solution: Run scraper first
python src/cybergov_data_scraper.py polkadot 1234
```

#### "OpenRouter API error"
```bash
# Check API key
echo $OPENROUTER_API_KEY

# Check balance
curl https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

#### "Invalid track ID"
```bash
# This is expected - system only votes on specific tracks
# Check constants.py for ALLOWED_TRACK_IDS
```

#### "Transaction failed"
```bash
# Check account balance
# Check RPC endpoint is accessible
# Verify proxy relationship is set up correctly
```

### Verify Data Flow

```bash
# 1. Check S3 structure
aws s3 ls s3://your-bucket/proposals/polkadot/1234/ --recursive

# 2. Verify manifest hash
python scripts/verify_hash.py polkadot 1234

# 3. Verify vote logic
python scripts/verify_vote.py polkadot 1234
```

---

## 📈 Monitoring Production

### Prefect Dashboard

```
http://localhost:4200
```

Monitor:
- Flow run status
- Task execution times
- Error rates
- Scheduled runs

### S3 CDN

Make your S3 bucket public (or use CDN) for transparency:

```
https://your-cdn.com/proposals/{network}/{id}/manifest.json
```

### Subscan

Track on-chain transactions:

```
https://polkadot.subscan.io/account/YOUR_PROXY_ADDRESS
```

---

## 🎓 Next Steps

### Learn More

1. Read `CODEBASE_OVERVIEW.md` for detailed architecture
2. Study the MAGI system prompts in `templates/system_prompts/`
3. Review the truth table logic in `cybergov_evaluate_single_proposal_and_vote.py`
4. Understand DSPy framework: https://dspy-docs.vercel.app/

### Customize

1. **Modify Agent Personalities**
   - Edit `templates/system_prompts/*.md`
   - Adjust voting criteria

2. **Change LLM Models**
   - Edit `utils/run_magi_eval.py`
   - Update `magi_llms` dictionary

3. **Adjust Vote Logic**
   - Edit `consolidate_vote()` in `cybergov_evaluate_single_proposal_and_vote.py`
   - Modify truth table

4. **Add New Networks**
   - Update `constants.py`
   - Add network-specific secrets
   - Create GitHub workflow

### Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 🆘 Getting Help

### Resources

- **GitHub Issues**: https://github.com/KarimJedda/cybergov/issues
- **Discussions**: https://github.com/KarimJedda/cybergov/discussions
- **Forum**: https://forum.polkadot.network/t/cybergov-v0-automating-trust-verifiable-llm-governance-on-polkadot/14796

### Community

- Follow updates: [@KarimJDDA](https://x.com/KarimJDDA)
- Watch the repo for announcements
- Join discussions on Polkadot forum

---

## ⚠️ Important Notes

1. **This is experimental software** - Use at your own risk
2. **LLMs can make mistakes** - Always verify decisions
3. **Start with test networks** - Use Paseo before mainnet
4. **Keep keys secure** - Never commit mnemonics to git
5. **Monitor costs** - LLM API calls can be expensive

---

## ✅ Checklist for First Run

- [ ] Python 3.11+ installed
- [ ] Repository cloned
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] S3 bucket created and configured
- [ ] OpenRouter API key obtained
- [ ] Environment variables set
- [ ] Test scraper: `python src/cybergov_data_scraper.py polkadot 1234`
- [ ] Test inference: `python src/cybergov_evaluate_single_proposal_and_vote.py`
- [ ] Verify output in S3
- [ ] Review `vote.json` and `manifest.json`

---

**Ready to run?** Start with the scraper and work through each component step by step. Good luck! 🚀
