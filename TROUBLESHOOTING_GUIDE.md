# CyberGov Troubleshooting Guide

Common issues and their solutions.

## 📋 Table of Contents

1. [Installation Issues](#installation-issues)
2. [S3 Storage Issues](#s3-storage-issues)
3. [LLM API Issues](#llm-api-issues)
4. [Prefect Issues](#prefect-issues)
5. [GitHub Actions Issues](#github-actions-issues)
6. [Substrate/Blockchain Issues](#substrateblockchain-issues)
7. [Data Processing Issues](#data-processing-issues)
8. [Performance Issues](#performance-issues)

---

## Installation Issues

### Python Version Mismatch

**Error**: `Python 3.11 or higher is required`

**Solution**:
```bash
# Check Python version
python --version

# Install Python 3.11+ from python.org
# Or use pyenv
pyenv install 3.11.0
pyenv local 3.11.0
```

### Dependency Installation Fails

**Error**: `ERROR: Could not find a version that satisfies the requirement...`

**Solution**:
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v

# If specific package fails, install separately
pip install substrate-interface==1.7.11
```

### substrate-interface Installation Error

**Error**: `error: Microsoft Visual C++ 14.0 or greater is required`

**Solution (Windows)**:
1. Install Visual Studio Build Tools
2. Or use pre-built wheels:
```bash
pip install --only-binary :all: substrate-interface
```

**Solution (Linux)**:
```bash
# Install build dependencies
sudo apt-get install build-essential python3-dev
```

---

## S3 Storage Issues

### "S3 file not found"

**Error**: `FileNotFoundError: s3://bucket/proposals/polkadot/1234/...`

**Diagnosis**:
```bash
# Check if scraper ran
python -c "
import s3fs
s3 = s3fs.S3FileSystem(
    key='YOUR_KEY',
    secret='YOUR_SECRET',
    client_kwargs={'endpoint_url': 'YOUR_ENDPOINT'}
)
print(s3.ls('YOUR_BUCKET/proposals/polkadot/1234'))
"
```

**Solution**:
```bash
# Run scraper first
python src/cybergov_data_scraper.py polkadot 1234
```

### "Access Denied" to S3

**Error**: `botocore.exceptions.ClientError: An error occurred (403) when calling...`

**Diagnosis**:
```bash
# Test credentials
aws s3 ls s3://your-bucket --endpoint-url YOUR_ENDPOINT
```

**Solutions**:
1. **Check credentials**:
   ```bash
   echo $S3_ACCESS_KEY_ID
   echo $S3_ACCESS_KEY_SECRET
   ```

2. **Verify bucket permissions**:
   - Read access for most operations
   - Write access for scraper/inference

3. **Check endpoint URL**:
   ```bash
   # Scaleway example
   S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud
   
   # AWS example
   S3_ENDPOINT_URL=https://s3.amazonaws.com
   ```

### S3 Connection Timeout

**Error**: `ReadTimeoutError: Read timed out`

**Solutions**:
1. **Check network connectivity**
2. **Increase timeout**:
   ```python
   s3 = s3fs.S3FileSystem(
       key=access_key,
       secret=secret_key,
       client_kwargs={
           "endpoint_url": endpoint_url,
           "config": {"read_timeout": 60}
       }
   )
   ```

3. **Use different region/endpoint**

---

## LLM API Issues

### "OpenRouter API key invalid"

**Error**: `401 Unauthorized: Invalid API key`

**Solutions**:
1. **Verify API key**:
   ```bash
   curl https://openrouter.ai/api/v1/auth/key \
     -H "Authorization: Bearer $OPENROUTER_API_KEY"
   ```

2. **Check key format**:
   - Should start with `sk-or-v1-`
   - No extra spaces or quotes

3. **Regenerate key** at https://openrouter.ai/keys

### "Insufficient credits"

**Error**: `402 Payment Required: Insufficient credits`

**Solutions**:
1. **Check balance**: https://openrouter.ai/credits
2. **Add credits** to your account
3. **Use cheaper models** (edit `src/utils/run_magi_eval.py`)

### "Rate limit exceeded"

**Error**: `429 Too Many Requests`

**Solutions**:
1. **Wait and retry** (automatic with retries)
2. **Increase delays** in `constants.py`:
   ```python
   INFERENCE_SCHEDULE_DELAY_MINUTES = 60  # Longer delay
   ```
3. **Use different models** with higher limits

### LLM Response Timeout

**Error**: `ReadTimeout: Request timed out`

**Solutions**:
1. **Increase timeout** in DSPy:
   ```python
   lm = dspy.LM(
       model=model_id,
       api_base="https://openrouter.ai/api/v1",
       api_key=api_key,
       timeout=120  # Increase timeout
   )
   ```

2. **Use faster models**
3. **Reduce proposal content length**

---

## Prefect Issues

### "Cannot connect to Prefect server"

**Error**: `httpx.ConnectError: [Errno 111] Connection refused`

**Diagnosis**:
```bash
# Check if Prefect is running
docker ps | grep prefect

# Check logs
docker-compose logs prefect-server
```

**Solutions**:
1. **Start Prefect**:
   ```bash
   cd infra
   docker-compose up -d
   ```

2. **Check port**:
   ```bash
   # Should be accessible
   curl http://localhost:4200/api/health
   ```

3. **Set API URL**:
   ```bash
   export PREFECT_API_URL=http://localhost:4200/api
   ```

### "Block not found"

**Error**: `ValueError: Block 'polkadot-rpc-url' not found`

**Diagnosis**:
```bash
# List all blocks
prefect block ls

# Check specific block
prefect block inspect secret/polkadot-rpc-url
```

**Solutions**:
1. **Create missing block**:
   ```bash
   prefect block create secret \
     --name "polkadot-rpc-url" \
     --value "wss://rpc.polkadot.io"
   ```

2. **Check block name** (case-sensitive, use hyphens)

3. **Register block types**:
   ```bash
   prefect block register -m prefect.blocks.system
   ```

### "Deployment not found"

**Error**: `ValueError: Deployment with id '...' not found`

**Solutions**:
1. **Deploy workflows**:
   ```bash
   prefect deploy --all
   ```

2. **Update deployment IDs** in `constants.py`:
   ```bash
   # Get deployment IDs
   prefect deployment ls
   
   # Copy IDs to constants.py
   DATA_SCRAPER_DEPLOYMENT_ID = "your-uuid-here"
   ```

### Flow Run Stuck in "Scheduled"

**Diagnosis**:
```bash
# Check work pools
prefect work-pool ls

# Check workers
prefect worker ls
```

**Solutions**:
1. **Start worker**:
   ```bash
   prefect worker start --pool cybergov-dispatcher-pool
   ```

2. **Check work pool exists**:
   ```bash
   prefect work-pool create cybergov-dispatcher-pool
   ```

---

## GitHub Actions Issues

### Workflow Not Triggering

**Diagnosis**:
1. Check workflow file syntax
2. Verify workflow is enabled
3. Check repository permissions

**Solutions**:
1. **Enable workflows**:
   - Settings → Actions → General
   - Allow all actions

2. **Check workflow file**:
   ```bash
   # Validate YAML
   yamllint .github/workflows/run_polkadot.yml
   ```

3. **Manual trigger**:
   - Actions → Select workflow → Run workflow

### "Secret not found"

**Error**: Workflow fails with missing environment variable

**Solutions**:
1. **Add secrets**:
   - Settings → Secrets and variables → Actions
   - New repository secret

2. **Check secret names** match workflow file:
   ```yaml
   env:
     S3_BUCKET_NAME: ${{ secrets.S3_BUCKET_NAME }}
   ```

3. **Use GitHub Environments** (optional):
   - Settings → Environments → New environment
   - Add environment-specific secrets

### Workflow Timeout

**Error**: `Error: The operation was canceled.`

**Solutions**:
1. **Increase timeout** in workflow:
   ```yaml
   jobs:
     cybergov:
       timeout-minutes: 60  # Increase from default 360
   ```

2. **Check LLM API** (most common cause)
3. **Optimize proposal content** (reduce length)

### "Permission denied" in Workflow

**Error**: `Error: Resource not accessible by integration`

**Solutions**:
1. **Update workflow permissions**:
   ```yaml
   permissions:
     contents: read
     actions: write
   ```

2. **Check repository settings**:
   - Settings → Actions → General
   - Workflow permissions → Read and write

---

## Substrate/Blockchain Issues

### "Transaction failed"

**Error**: Various transaction errors

**Diagnosis**:
```bash
# Check account balance
# Go to https://polkadot.js.org/apps
# Accounts → Your address

# Check proxy relationship
# Developer → Chain state → proxy.proxies
```

**Solutions**:
1. **Insufficient balance**:
   - Transfer DOT/KSM to main account
   - Need balance for: vote amount + transaction fees

2. **Proxy not set up**:
   ```bash
   # Set up proxy via polkadot.js.org/apps
   # Developer → Extrinsics → proxy.addProxy
   ```

3. **Wrong proxy type**:
   - Must be "Governance" proxy type

4. **Network congestion**:
   - Wait and retry
   - Increase transaction priority

### "RPC endpoint not responding"

**Error**: `ConnectionError: Cannot connect to RPC`

**Diagnosis**:
```bash
# Test RPC endpoint
wscat -c wss://rpc.polkadot.io

# Or with curl
curl -H "Content-Type: application/json" \
  -d '{"id":1, "jsonrpc":"2.0", "method": "system_health"}' \
  https://rpc.polkadot.io
```

**Solutions**:
1. **Use different RPC**:
   ```python
   # Public RPCs
   wss://rpc.polkadot.io
   wss://polkadot-rpc.dwellir.com
   wss://polkadot.api.onfinality.io/public-ws
   ```

2. **Check network status**: https://polkadot.subscan.io

3. **Use Substrate Sidecar** (more reliable)

### "Invalid mnemonic"

**Error**: `ValueError: Invalid mnemonic phrase`

**Solutions**:
1. **Check mnemonic format**:
   - Should be 12 or 24 words
   - Separated by spaces
   - No extra characters

2. **Verify in Prefect block**:
   ```bash
   prefect block inspect secret/polkadot-cybergov-mnemonic
   ```

3. **Test mnemonic**:
   ```python
   from substrateinterface import Keypair
   keypair = Keypair.create_from_mnemonic("your mnemonic here")
   print(keypair.ss58_address)
   ```

---

## Data Processing Issues

### "Invalid track ID"

**Message**: `Not scheduling inference for this proposal, track_id X is not delegated`

**This is expected behavior!** The system only votes on specific tracks.

**Check allowed tracks**:
```python
# In constants.py
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

**To vote on different tracks**: Edit `ALLOWED_TRACK_IDS` in `constants.py`

### "Proposal content too long"

**Error**: `Content truncated due to excessive length`

**This is handled automatically**:
```python
# In cybergov_data_scraper.py
if len(proposal_content) > 60000:
    proposal_content = proposal_content[:60000] + "\n\n...[TRUNCATED]..."
```

**Solutions**:
1. **Increase limit** (may increase LLM costs)
2. **Summarize content** before sending to LLMs
3. **Flag as "too verbose"** (already done by DSPy)

### "Vote consolidation error"

**Error**: Issues with vote.json format

**Diagnosis**:
```bash
# Check vote.json structure
cat workspace/vote.json | jq .

# Verify individual analyses
cat workspace/llm_analyses/balthazar.json | jq .decision
```

**Solutions**:
1. **Check decision format**:
   - Must be: "Aye", "Nay", or "Abstain"
   - Case-insensitive but normalized

2. **Verify all agents ran**:
   ```bash
   ls workspace/llm_analyses/
   # Should have: balthazar.json, melchior.json, caspar.json
   ```

3. **Re-run inference** if files missing

---

## Performance Issues

### Slow Scraping

**Symptoms**: Scraper takes too long

**Solutions**:
1. **Check network speed**
2. **Use faster S3 region**
3. **Reduce retry delays**:
   ```python
   @task(
       retries=3,
       retry_delay_seconds=5  # Reduce from 10
   )
   ```

### Slow Inference

**Symptoms**: LLM analysis takes >5 minutes

**Solutions**:
1. **Use faster models**:
   ```python
   magi_llms = {
       "balthazar": "openai/gpt-4o-mini",  # Faster
       "melchior": "anthropic/claude-3-haiku",  # Faster
       "caspar": "openrouter/x-ai/grok-code-fast-1"
   }
   ```

2. **Reduce proposal content**
3. **Parallel execution** (already implemented)

### High LLM Costs

**Symptoms**: OpenRouter bills too high

**Solutions**:
1. **Use cheaper models**:
   - GPT-4o-mini instead of GPT-4o
   - Claude Haiku instead of Opus
   - Gemini Flash instead of Pro

2. **Reduce proposal content length**

3. **Limit processing**:
   ```python
   # In constants.py
   CYBERGOV_PARAMS = {
       "max_proposal_id": {"polkadot": 2000}  # Stop at ID 2000
   }
   ```

4. **Monitor usage**: https://openrouter.ai/activity

---

## Debugging Tips

### Enable Verbose Logging

```python
# In any script
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Prefect Logs

```bash
# Via CLI
prefect flow-run logs <flow-run-id>

# Via UI
http://localhost:4200 → Flow Runs → Select run → Logs
```

### Inspect S3 Data

```bash
# List files
aws s3 ls s3://bucket/proposals/polkadot/1234/ --recursive

# Download file
aws s3 cp s3://bucket/proposals/polkadot/1234/vote.json ./

# View file
cat vote.json | jq .
```

### Test Individual Components

```bash
# Test scraper only
python src/cybergov_data_scraper.py polkadot 1234

# Test inference only (requires scraped data)
python src/cybergov_evaluate_single_proposal_and_vote.py

# Test voter only (requires vote.json)
python src/cybergov_voter.py polkadot 1234
```

### Verify Data Integrity

```bash
# Check manifest hash
python scripts/verify_hash.py polkadot 1234

# Check vote logic
python scripts/verify_vote.py polkadot 1234
```

---

## Getting Help

### Before Asking for Help

1. **Check logs** (Prefect, GitHub Actions, console)
2. **Verify configuration** (environment variables, secrets)
3. **Test components individually**
4. **Search existing issues**: https://github.com/KarimJedda/cybergov/issues

### When Asking for Help

Include:
1. **Error message** (full traceback)
2. **What you tried** (steps to reproduce)
3. **Environment** (OS, Python version)
4. **Configuration** (sanitized, no secrets)
5. **Logs** (relevant portions)

### Where to Ask

- **GitHub Issues**: https://github.com/KarimJedda/cybergov/issues
- **Discussions**: https://github.com/KarimJedda/cybergov/discussions
- **Forum**: https://forum.polkadot.network/

---

## Common Error Messages Reference

| Error | Likely Cause | Quick Fix |
|-------|--------------|-----------|
| `FileNotFoundError: s3://...` | Scraper not run | Run scraper first |
| `401 Unauthorized` | Invalid API key | Check OpenRouter key |
| `403 Forbidden` | S3 permissions | Check S3 credentials |
| `429 Too Many Requests` | Rate limit | Wait or use different model |
| `Connection refused` | Prefect not running | Start Prefect server |
| `Block not found` | Missing Prefect block | Create block |
| `Invalid mnemonic` | Wrong format | Check mnemonic phrase |
| `Transaction failed` | Insufficient balance | Fund account |
| `Proxy not found` | Proxy not set up | Set up proxy relationship |
| `Invalid track ID` | Expected behavior | Only votes on allowed tracks |

---

**Still stuck?** Open an issue with full details: https://github.com/KarimJedda/cybergov/issues/new
