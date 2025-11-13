# Polkassembly API Integration Guide

## Overview

This guide shows you how to integrate Polkassembly APIs into your CyberGov system to enhance MAGI decision-making with real-time governance context.

## Working APIs

### ✅ Confirmed Working Endpoints

1. **Treasury Statistics** - `GET /v2/meta/treasury-stats`
   - Current treasury balance across all chains
   - Next burn amount and date
   - Asset Hub balances (USDC, USDT, etc.)

2. **Track Counts** - `GET /v2/track-counts`
   - Active proposal counts per governance track
   - Useful for understanding governance load

3. **Delegation Stats** - `GET /v2/delegation/stats`
   - Total delegated tokens
   - Number of delegates and delegators
   - Delegation participation metrics

4. **Proposal Votes** - `GET /v2/votes/all?proposalType=referendums_v2&proposalIndex={id}`
   - All votes cast on a specific proposal
   - Vote decisions (Aye/Nay/Abstain)
   - Voting power and conviction levels

5. **Bounties Stats** - `GET /v2/bounties/stats`
   - Active bounties count
   - Total bounty pool
   - Rewards distributed

6. **Preimages** - `GET /v2/preimages?page=1&limit=10`
   - Recent preimages submitted
   - Preimage hashes and methods

7. **Activity Feed** - `GET /v2/activity-feed?page=1&limit=10`
   - Recent governance activity
   - New proposals and updates

8. **Tags** - `GET /v2/meta/tags`
   - Available proposal tags
   - Tag usage statistics

## Quick Start

### 1. Test the APIs

```bash
# Test all working APIs
python scripts/test_working_apis.py

# Explore specific proposal data
python scripts/explore_proposal_data.py polkadot 1783

# Compare Subsquare vs Polkassembly
python scripts/compare_api_sources.py polkadot 1783

# Get enhanced governance context
python scripts/practical_api_integration.py polkadot 1783
```

### 2. Integration Example

```python
from scripts.practical_api_integration import PolkassemblyClient

# Initialize client
client = PolkassemblyClient("polkadot")

# Get treasury health
treasury = client.get_treasury_stats()
print(f"Treasury Balance: {treasury['relayChain']['nativeToken']} Planck")

# Get voting patterns
votes = client.get_proposal_votes(1783)
print(f"Total votes: {len(votes['items'])}")

# Get delegation stats
delegations = client.get_delegation_stats()
print(f"Total delegates: {delegations['totalDelegates']}")
```

## Integration into CyberGov

### Phase 1: Enhance Data Scraper

Add Polkassembly data fetching to `cybergov_data_scraper.py`:

```python
@task
def fetch_polkassembly_context(network: str, proposal_id: int):
    """Fetch additional context from Polkassembly"""
    client = PolkassemblyClient(network)
    
    return {
        "treasury_stats": client.get_treasury_stats(),
        "voting_patterns": client.get_proposal_votes(proposal_id),
        "delegation_stats": client.get_delegation_stats(),
        "track_counts": client.get_track_counts()
    }
```

### Phase 2: Enhance MAGI Context

Modify `utils/proposal_augmentation.py` to include governance context:

```python
def generate_content_for_magis(
    proposal_data: Dict[str, Any], 
    logger, 
    openrouter_model, 
    openrouter_api_key, 
    network,
    polkassembly_context: Dict = None  # NEW
):
    # ... existing code ...
    
    # Add governance context to the markdown
    if polkassembly_context:
        governance_section = format_governance_context(polkassembly_context)
        content_md += f"\n\n{governance_section}"
    
    return content_md
```

### Phase 3: Update MAGI Evaluation

Enhance `utils/run_magi_eval.py` with governance context:

```python
class EnhancedMAGIVoteSignature(dspy.Signature):
    """Enhanced with governance context"""
    
    personality = dspy.InputField(desc="The guiding principle")
    proposal_text = dspy.InputField(desc="The proposal content")
    governance_context = dspy.InputField(desc="Current governance state")  # NEW
    
    # ... rest of signature
```

## Use Cases

### 1. Treasury Health Check (Caspar)

```python
def should_approve_spending(proposal_cost: float, treasury_stats: Dict) -> bool:
    """Caspar checks if treasury can afford this"""
    treasury_balance = int(treasury_stats['relayChain']['nativeToken']) / 1e10
    next_burn = int(treasury_stats['relayChain']['nextBurn']) / 1e10
    
    # Don't approve if it's more than 1% of treasury
    if proposal_cost > treasury_balance * 0.01:
        return False
    
    # Check if treasury is healthy
    if treasury_balance < 10_000_000:  # Less than 10M DOT
        return False
    
    return True
```

### 2. Voting Momentum Analysis (Balthazar)

```python
def analyze_community_sentiment(votes_data: Dict) -> str:
    """Balthazar checks if community supports this"""
    votes = votes_data.get('items', [])
    
    aye_count = sum(1 for v in votes if v['decision'] == 'aye')
    nay_count = sum(1 for v in votes if v['decision'] == 'nay')
    
    if aye_count > nay_count * 3:
        return "strong_community_support"
    elif nay_count > aye_count * 3:
        return "strong_community_opposition"
    else:
        return "contested"
```

### 3. Delegation Context (Melchior)

```python
def assess_delegation_impact(delegation_stats: Dict) -> Dict:
    """Melchior checks delegation health"""
    total_delegated = int(delegation_stats['totalDelegatedTokens']) / 1e10
    total_delegates = delegation_stats['totalDelegates']
    
    return {
        "delegation_participation": "high" if total_delegated > 400_000_000 else "low",
        "delegate_diversity": "good" if total_delegates > 100 else "concentrated",
        "avg_delegation": total_delegated / total_delegates if total_delegates > 0 else 0
    }
```

## API Response Examples

### Treasury Stats Response

```json
{
  "network": "polkadot",
  "relayChain": {
    "nativeToken": "152927039530114988",
    "nextBurn": "1529270395301149",
    "nextSpendAt": "2025-11-17T19:40:45.091Z"
  },
  "assetHub": {
    "usdc": "55000000000",
    "usdt": "54999726904"
  }
}
```

### Votes Response

```json
{
  "items": [
    {
      "voter": "15MUBwP6dyVw5CXF9PjSSv7SdXQuDSwjX86v1kBodCSWVR7c",
      "decision": "aye",
      "balance": {
        "value": "5000000000000"
      },
      "lockPeriod": 2,
      "createdAt": "2025-11-12T12:02:54.000000Z"
    }
  ]
}
```

## Best Practices

1. **Cache API Responses**: Treasury stats don't change frequently
2. **Handle Timeouts**: Some endpoints can be slow
3. **Batch Requests**: Fetch all context data at once
4. **Error Handling**: Always have fallbacks if APIs fail
5. **Rate Limiting**: Be respectful of API limits

## Next Steps

1. ✅ Test the APIs with the provided scripts
2. ✅ Understand the data structure
3. 🔄 Integrate into `cybergov_data_scraper.py`
4. 🔄 Enhance MAGI context generation
5. 🔄 Update MAGI evaluation logic
6. 🔄 Test with real proposals
7. 🔄 Monitor and iterate

## Troubleshooting

### API Returns 400 Error
- Check the proposal type parameter: `referendums_v2`
- Verify the network name is correct

### API Returns 404 Error
- The endpoint might not exist for that network
- Try the v1 endpoints instead

### Timeout Errors
- Increase timeout to 15-30 seconds
- Some endpoints are slower than others

## Resources

- [Polkassembly API Docs](https://polkadot.polkassembly.io/api-docs)
- [Subsquare API Docs](https://docs.subsquare.io/)
- [CyberGov Repository](https://github.com/KarimJedda/cybergov)

## Support

For questions or issues:
- Open an issue on GitHub
- Check the scripts in `scripts/` directory
- Review the examples in this guide
