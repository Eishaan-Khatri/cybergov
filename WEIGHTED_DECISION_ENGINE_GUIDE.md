# Weighted Decision Engine - Implementation Guide

## Overview
The weighted decision engine applies template-based weighting to tri-agent (Balthazar, Caspar, Melchior) votes with safety overrides.

## Architecture

### Single Source of Truth
- **`src/utils/strategies.py`**: Defines all voting templates (TEMPLATES dict)
- **`src/utils/weighted_decision_engine.py`**: Imports templates and implements decision logic
- **`src/votebot_evaluate_single_proposal_and_vote.py`**: Uses engine for final vote consolidation

## Configuration

### Environment Variable
```bash
CYBERGOV_VOTING_STRATEGY=risk-averse
```

### Available Strategies
| Strategy | Balthazar | Caspar | Melchior | Use Case |
|----------|-----------|--------|----------|----------|
| `neutral` (default) | 33% | 33% | 34% | Balanced, equal weight |
| `risk-averse` | 20% | 60% | 20% | Conservative, treasury-focused |
| `aggressive` | 30% | 20% | 50% | Growth-oriented, community-first |
| `conservative` | 30% | 50% | 20% | Moderate risk management |
| `technical` | 40% | 40% | 20% | Technical merit focus |
| `community-focused` | 20% | 30% | 50% | Community engagement priority |
| `treasury-watchdog` | 20% | 60% | 20% | Strict financial oversight |
| `validator-aligned` | 40% | 40% | 20% | Technical + financial balance |
| `growth-oriented` | 30% | 20% | 50% | Ecosystem expansion |
| `experimental` | 25% | 15% | 60% | High-risk, high-reward |

## Decision Rules (Applied in Order)

1. **Low Margin Override** (threshold: 0.15)
   - If top score - runner-up < 0.15 → Abstain
   - Ensures clear winner before committing

2. **Abstain Dominance** (threshold: 0.40)
   - If Abstain score ≥ 0.40 → Abstain
   - Respects agent uncertainty

3. **Weak Confidence Override** (threshold: 0.60)
   - If top score < 0.60 → Abstain
   - Requires minimum confidence level

4. **Tie Rule**
   - If multiple decisions have same top score → Abstain
   - Avoids arbitrary selection

5. **Clear Winner**
   - If all checks pass → Use weighted result
   - Confidence: Strong (≥0.70), Moderate (≥0.60), Weak (<0.60)

## Robustness Features

### Input Normalization
- **Case-insensitive**: "aye", "AYE", "Aye" all work
- **Synonyms**: "yes" → Aye, "no" → Nay
- **Missing keys**: Defaults to Abstain for missing decisions, 0.0 weight for missing agents
- **Empty votes**: Handles gracefully, returns Abstain

### Error Handling
- **Zero-sum weights**: Automatically falls back to neutral template
- **Invalid template names**: Falls back to neutral template
- **Missing agents in template**: Logs warning, treats as 0.0 weight
- **Firestore upload failures**: Logs error with full traceback before raising

## Output Format

### vote.json Structure
```json
{
  "timestamp_utc": "2025-11-21T...",
  "is_conclusive": true,
  "final_decision": "Aye",
  "is_unanimous": false,
  "summary_rationale": "<HTML summary>",
  "votes_breakdown": [
    {"model": "balthazar", "decision": "Aye", "confidence": 0.85},
    {"model": "melchior", "decision": "Aye", "confidence": 0.78},
    {"model": "caspar", "decision": "Nay", "confidence": 0.92}
  ],
  "weighted_decision_metadata": {
    "engine_version": "WeightedGovernanceDecisionEngine_v1",
    "strategy_used": "risk-averse",
    "template_weights": {
      "balthazar": 0.2,
      "caspar": 0.6,
      "melchior": 0.2
    },
    "weighted_scores": {
      "Aye": 0.4,
      "Nay": 0.6,
      "Abstain": 0.0
    },
    "margin": 0.2,
    "confidence": "Moderate",
    "rules_triggered": ["weighted_decision"],
    "decision_reasoning": "Nay has clear weighted majority (0.600) with margin 0.200",
    "agent_votes_with_weights": [
      {"agent": "balthazar", "vote": "Aye", "weight_applied": 0.2},
      {"agent": "melchior", "vote": "Aye", "weight_applied": 0.2},
      {"agent": "caspar", "vote": "Nay", "weight_applied": 0.6}
    ]
  }
}
```

## Usage Examples

### Basic Usage
```python
from utils.weighted_decision_engine import compute_weighted_decision

votes = [
    {"agent": "balthazar", "decision": "Aye"},
    {"agent": "melchior", "decision": "Aye"},
    {"agent": "caspar", "decision": "Nay"}
]

result = compute_weighted_decision(votes, template_name="risk-averse")
print(f"Decision: {result.final_decision}")
print(f"Confidence: {result.confidence}")
```

### Custom Weights
```python
custom = {"balthazar": 0.5, "caspar": 0.3, "melchior": 0.2}
result = compute_weighted_decision(votes, custom_weights=custom)
```

### In Production (votebot_evaluate)
The engine is automatically used in `consolidate_vote()`:
1. Reads `CYBERGOV_VOTING_STRATEGY` from environment
2. Collects agent votes from analysis files
3. Applies weighted decision engine
4. Saves full metadata to Firestore

## Testing

### Quick Test
```python
from utils.weighted_decision_engine import compute_weighted_decision

# Test unanimous
votes = [
    {"agent": "balthazar", "decision": "Aye"},
    {"agent": "caspar", "decision": "Aye"},
    {"agent": "melchior", "decision": "Aye"}
]
result = compute_weighted_decision(votes, "neutral")
assert result.final_decision == "Aye"

# Test risk-averse override
votes2 = [
    {"agent": "balthazar", "decision": "Aye"},
    {"agent": "melchior", "decision": "Aye"},
    {"agent": "caspar", "decision": "Nay"}  # 60% weight
]
result2 = compute_weighted_decision(votes2, "risk-averse")
assert result2.final_decision == "Nay"  # Caspar overrides
```

## Logging

The engine logs:
- Template selection and weights applied
- Weighted scores for each decision
- Margin between top choices
- Rules triggered
- Decision reasoning
- Warnings for missing agents or zero-sum weights

## Best Practices

1. **Set strategy explicitly**: Don't rely on default, set `CYBERGOV_VOTING_STRATEGY`
2. **Monitor logs**: Check for warnings about missing agents or fallbacks
3. **Review metadata**: Use `weighted_decision_metadata` in vote.json for transparency
4. **Test edge cases**: Verify behavior with ties, abstains, and edge margins
5. **Document strategy choice**: Record why you chose a particular strategy for governance

## Troubleshooting

### Issue: Wrong decision despite majority
- **Check**: Which strategy is active? Risk-averse gives Caspar 60% weight
- **Solution**: Verify `CYBERGOV_VOTING_STRATEGY` matches your intent

### Issue: Too many Abstain results
- **Check**: Margin threshold (0.15) might be too strict
- **Solution**: Review thresholds in `weighted_decision_engine.py` or adjust strategy

### Issue: Missing agent warnings
- **Check**: Template definition in `strategies.py`
- **Solution**: Ensure all templates have balthazar, caspar, melchior keys

### Issue: Zero-sum fallback triggered
- **Check**: Custom weights or template definition
- **Solution**: Ensure weights sum to > 0, engine will normalize to 1.0
