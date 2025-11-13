# Polkassembly API Quick Reference

## 🚀 Quick Commands

```bash
# Test all APIs
python scripts/test_working_apis.py

# Get enhanced context for a proposal
python scripts/practical_api_integration.py polkadot 1783

# Compare Subsquare vs Polkassembly
python scripts/compare_api_sources.py polkadot 1783

# Explore proposal data
python scripts/explore_proposal_data.py polkadot 1783
```

## 📡 API Endpoints Cheat Sheet

### Base URLs
```
Polkadot:  https://polkadot.polkassembly.io/api
Kusama:    https://kusama.polkassembly.io/api
Paseo:     https://paseo.polkassembly.io/api
```

### Working Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v2/meta/treasury-stats` | GET | Treasury balance & burn |
| `/v2/track-counts` | GET | Active proposals per track |
| `/v2/delegation/stats` | GET | Delegation metrics |
| `/v2/votes/all?proposalType=referendums_v2&proposalIndex={id}` | GET | Votes on proposal |
| `/v2/bounties/stats` | GET | Bounty statistics |
| `/v2/activity-feed?page=1&limit=10` | GET | Recent activity |
| `/v2/meta/tags` | GET | Available tags |
| `/v2/preimages?page=1&limit=10` | GET | Recent preimages |

## 💻 Code Snippets

### Initialize Client
```python
from scripts.practical_api_integration import PolkassemblyClient

client = PolkassemblyClient("polkadot")
```

### Get Treasury Stats
```python
treasury = client.get_treasury_stats()
balance_dot = int(treasury['relayChain']['nativeToken']) / 1e10
print(f"Treasury: {balance_dot:,.2f} DOT")
```

### Get Voting Patterns
```python
votes = client.get_proposal_votes(1783)
aye_count = sum(1 for v in votes['items'] if v['decision'] == 'aye')
print(f"Aye votes: {aye_count}")
```

### Get Delegation Stats
```python
delegations = client.get_delegation_stats()
total_delegated = int(delegations['totalDelegatedTokens']) / 1e10
print(f"Delegated: {total_delegated:,.2f} DOT")
```

## 🎯 Use Cases by MAGI

### Balthazar (Strategic)
```python
# Check community sentiment
votes = client.get_proposal_votes(proposal_id)
aye_count = sum(1 for v in votes['items'] if v['decision'] == 'aye')
nay_count = sum(1 for v in votes['items'] if v['decision'] == 'nay')

if aye_count > nay_count * 2:
    sentiment = "strong_support"
```

### Caspar (Sustainability)
```python
# Check treasury health
treasury = client.get_treasury_stats()
balance = int(treasury['relayChain']['nativeToken']) / 1e10
proposal_cost = 100000  # DOT

if proposal_cost > balance * 0.01:  # More than 1% of treasury
    risk = "high"
```

### Melchior (Growth)
```python
# Check delegation participation
delegations = client.get_delegation_stats()
total_delegated = int(delegations['totalDelegatedTokens']) / 1e10

if total_delegated > 400_000_000:
    participation = "high"
```

## 📊 Data Conversions

### Planck to DOT
```python
planck = 152927039530114988
dot = planck / 1e10  # = 15,292,703.95 DOT
```

### Planck to KSM
```python
planck = 152927039530114988
ksm = planck / 1e12  # = 152,927.04 KSM
```

## 🔍 Response Examples

### Treasury Stats
```json
{
  "relayChain": {
    "nativeToken": "152927039530114988",
    "nextBurn": "1529270395301149",
    "nextSpendAt": "2025-11-17T19:40:45.091Z"
  }
}
```

### Votes
```json
{
  "items": [{
    "voter": "15MUBw...",
    "decision": "aye",
    "balance": {"value": "5000000000000"},
    "lockPeriod": 2
  }]
}
```

### Delegation Stats
```json
{
  "totalDelegatedTokens": "4492275018335415805",
  "totalDelegates": 160,
  "totalDelegators": 555
}
```

## ⚡ Quick Integration

### Add to cybergov_data_scraper.py
```python
@task
def fetch_governance_context(network: str, proposal_id: int):
    client = PolkassemblyClient(network)
    return {
        "treasury": client.get_treasury_stats(),
        "votes": client.get_proposal_votes(proposal_id),
        "delegations": client.get_delegation_stats()
    }
```

### Use in MAGI evaluation
```python
# In generate_content_for_magis()
governance_context = fetch_governance_context(network, proposal_id)
enhanced_content = f"{proposal_content}\n\n{format_context(governance_context)}"
```

## 🐛 Common Issues

### 400 Error
- Check `proposalType=referendums_v2` parameter
- Verify network name is correct

### 404 Error
- Endpoint might not exist for that network
- Try v1 endpoints instead

### Timeout
- Increase timeout to 15-30 seconds
- Some endpoints are slower

## 📚 Full Documentation

- Complete Guide: `docs/POLKASSEMBLY_API_INTEGRATION.md`
- Summary: `POLKASSEMBLY_INTEGRATION_SUMMARY.md`
- Test Scripts: `scripts/` directory

## 🎯 Next Steps

1. Run `python scripts/practical_api_integration.py polkadot 1783`
2. Review the output
3. Integrate into your data scraper
4. Enhance MAGI context
5. Test with real proposals

---

**Pro Tip**: Start with `practical_api_integration.py` - it shows everything working together!
