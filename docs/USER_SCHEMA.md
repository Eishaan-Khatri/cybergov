
# User Collection Schema

This document defines the schema for the `users` collection in Firestore.

## 1. User Profile Document
**Path:** `users/{user_id}`

| Field | Type | Description |
|-------|------|-------------|
| `userId` | String | Unique identifier for the user (e.g., Wallet Address or UUID). |
| `strategyId` | String | The ID of the selected strategy (e.g., "aggressive", "neutral"). |
| `walletAddress` | String | (Optional) The user's Polkadot wallet address. |
| `createdAt` | Timestamp | When the user was created. |
| `updatedAt` | Timestamp | When the profile was last updated. |
| `email` | String | (Optional) Contact email. |
| `preferences` | Map | (Optional) Custom settings (e.g., notification preferences). |

### Example JSON
```json
{
  "userId": "user_123",
  "strategyId": "aggressive",
  "walletAddress": "15oF4...",
  "createdAt": "2025-11-22T10:00:00Z",
  "updatedAt": "2025-11-22T10:00:00Z"
}
```

---

## 2. User Votes Subcollection
**Path:** `users/{user_id}/votes/{proposal_id}`

This collection stores the **personalized, weighted vote** for each proposal.

| Field | Type | Description |
|-------|------|-------------|
| `proposal_id` | String | ID of the proposal (e.g., "123"). |
| `user_id` | String | ID of the user. |
| `voted_at` | Timestamp | When the vote was calculated/cast. |
| `strategy_used` | String | The strategy active at the time of voting. |
| `vote` | Map | Contains the complex vote content and metadata. |
| `provenance` | Map | Link to the GitHub run/commit that generated this. |
| `proposal_snapshot` | Map | Key details about the proposal (Title, Amount). |

### Example JSON (The "Complex" Structure)
```json
{
  "proposal_id": "1796",
  "user_id": "user_123",
  "voted_at": "2025-11-22T10:05:00Z",
  "strategy_used": "aggressive",
  "vote": {
    "content": "{\"timestamp_utc\": \"...\", \"final_decision\": \"Aye\", ...}", 
    "hash": "sha256:...",
    "timestamp_utc": "2025-11-22T10:05:00Z"
  },
  "provenance": {
    "github_run_id": "19572037771",
    "model_name": "delegate-x-v1"
  },
  "proposal_snapshot": {
    "title": "ink! Alliance Proposal",
    "requested_amount": "362500"
  }
}
```

### The `vote.content` JSON String
The `content` field inside `vote` is a **stringified JSON** containing the full reasoning:

```json
{
  "timestamp_utc": "2025-11-22T10:05:00Z",
  "is_conclusive": true,
  "final_decision": "Aye",
  "summary_rationale": "Weighted score (0.8) exceeds threshold...",
  "votes_breakdown": [
    {"model": "balthazar", "decision": "Aye"},
    {"model": "melchior", "decision": "Nay"}
  ],
  "weighted_decision_metadata": {
    "strategy_used": "aggressive",
    "weighted_scores": {"Aye": 0.8, "Nay": 0.2},
    "rules_triggered": ["weighted_decision"]
  }
}
```
