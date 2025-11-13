# Firestore Design Answers - Complete System Analysis

After reading the entire CyberGov codebase line by line, here are the detailed answers to design a proper Firestore schema.

---

## 1. How do you query proposals today?

### Current Query Patterns (from code analysis):

**A. Dispatcher queries (cybergov_dispatcher.py):**
- **"Get highest proposal ID for a network"** - Scans S3 to find max proposal ID
  ```python
  # Lines 26-67: get_last_processed_id_from_s3()
  # Lists all folders in s3://bucket/proposals/{network}/
  # Extracts numeric IDs, returns max(proposal_ids)
  ```

- **"Find new proposals after ID X"** - Queries Substrate sidecar API
  ```python
  # Lines 70-135: find_new_proposals()
  # Gets referendumCount from blockchain
  # Generates list of IDs between last_known_id and current
  ```

- **"Check if proposal already scheduled"** - Queries Prefect API
  ```python
  # Lines 138-175: check_if_already_scheduled()
  # Searches Prefect flow runs by name pattern: "scrape-{network}-{proposal_id}"
  # Filters by state: RUNNING, COMPLETED, PENDING, SCHEDULED
  ```

**B. Voter queries (cybergov_voter.py):**
- **"Get vote decision for proposal"** - Reads vote.json from S3
  ```python
  # Lines 100-155: get_inference_result()
  # Reads: s3://bucket/proposals/{network}/{proposal_id}/vote.json
  # Returns: vote_result, conviction, remark_hash, vote_data
  ```

- **"Check if proposal should be voted on"** - Reads raw_subsquare_data.json
  ```python
  # Lines 330-375: should_we_vote()
  # Reads: s3://bucket/proposals/{network}/{proposal_id}/raw_subsquare_data.json
  # Checks: track ID is in ALLOWED_TRACK_IDS [2, 11, 30, 31, 32, 33, 34]
  ```

- **"Check if voting already scheduled"** - Queries Prefect API
  ```python
  # Lines 158-190: check_if_voting_already_scheduled()
  # Searches: "vote-{network}-{proposal_id}"
  ```

**C. Commenter queries (cybergov_commenter.py):**
- **"Get comment data for proposal"** - Reads vote.json + raw_subsquare_data.json
  ```python
  # Lines 11-60: get_infos_for_substrate_comment()
  # Reads vote.json for summary_rationale
  # Reads raw_subsquare_data.json for indexer.blockHeight
  ```

**D. Inference queries (cybergov_inference.py):**
- **"Check if inference already scheduled"** - Queries Prefect API
  ```python
  # Lines 95-127: check_if_already_scheduled()
  # Searches: "inference-{network}-{proposal_id}"
  ```

### Required Firestore Queries:

```
1. Get max proposal ID by network
   WHERE network == "polkadot" ORDER BY proposalId DESC LIMIT 1

2. Get proposals by status
   WHERE network == "polkadot" AND status == "pending_analysis"

3. Get proposals by track
   WHERE network == "polkadot" AND track IN [2, 11, 30, 31, 32, 33, 34]

4. Get proposal by network + ID (primary lookup)
   WHERE network == "polkadot" AND proposalId == 1234

5. Get proposals by final decision
   WHERE finalDecision == "Aye"

6. Get proposals by timestamp range
   WHERE network == "polkadot" AND createdAt >= timestamp ORDER BY createdAt

7. Get proposals missing files
   WHERE status == "incomplete" OR manifestHash == null

8. Get proposals with disagreement
   WHERE isUnanimous == false

9. Check if proposal exists
   Document ID: "{network}_{proposalId}"
```

---

## 2. What is the lifecycle of a proposal?

### Complete Pipeline (from code analysis):

```
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: DISCOVERY (cybergov_dispatcher.py)                     │
├─────────────────────────────────────────────────────────────────┤
│ State: "discovered"                                              │
│ - Dispatcher finds new proposal ID from blockchain              │
│ - Schedules scraping task (2 days delay)                        │
│ - Creates Prefect flow run: "scrape-{network}-{proposal_id}"   │
│ Required fields: network, proposalId, discoveredAt              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: SCRAPING (cybergov_data_scraper.py)                   │
├─────────────────────────────────────────────────────────────────┤
│ State: "scraped"                                                 │
│ - Archives previous run data if exists (vote_archive_N/)        │
│ - Fetches raw_subsquare_data.json from Subsquare API           │
│ - Validates track ID against ALLOWED_TRACK_IDS                  │
│ - Generates content.md using LLM (proposal_augmentation.py)     │
│ - Schedules inference task (30 min delay)                       │
│ Required fields: track, title, content, proposer, blockHeight   │
│ Queryable: track, status="scraped"                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: INFERENCE (cybergov_inference.py + GitHub Actions)    │
├─────────────────────────────────────────────────────────────────┤
│ State: "analyzing" → "analyzed"                                  │
│ - Triggers GitHub Actions workflow via API                      │
│ - Runs cybergov_evaluate_single_proposal_and_vote.py           │
│   ├─ Preflight checks (validate files exist)                   │
│   ├─ Run 3 MAGI agents (balthazar, melchior, caspar)          │
│   ├─ Each agent produces analysis JSON                         │
│   ├─ Consolidate votes using truth table                       │
│   └─ Generate manifest.json with file hashes                   │
│ - Polls GitHub Actions for completion                           │
│ - Schedules voting task (30 min delay)                         │
│ Required fields: githubRunId, githubCommitSha                   │
│ Queryable: status="analyzed", isUnanimous, finalDecision        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 4: VOTING (cybergov_voter.py)                            │
├─────────────────────────────────────────────────────────────────┤
│ State: "voted"                                                   │
│ - Checks track ID is allowed                                    │
│ - Reads vote.json and manifest.json                            │
│ - Creates blockchain transaction:                               │
│   ├─ Proxy.proxy(ConvictionVoting.vote)                        │
│   └─ System.remark_with_event(manifest_hash)                   │
│ - Signs with proxy account keypair                             │
│ - Submits via Substrate Sidecar                                │
│ - Schedules comment task (30 min delay)                        │
│ Required fields: txHash, manifestHash, votedAt                  │
│ Queryable: status="voted", txHash                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 5: COMMENTING (cybergov_commenter.py)                    │
├─────────────────────────────────────────────────────────────────┤
│ State: "completed"                                               │
│ - Reads vote.json for summary_rationale                        │
│ - Reads raw_subsquare_data.json for blockHeight                │
│ - Posts HTML comment to Subsquare API                          │
│ - Comment includes:                                             │
│   ├─ Vote breakdown (3 agents)                                 │
│   ├─ Links to manifest, content, GitHub run                    │
│   ├─ Feedback form links                                       │
│   └─ Transparency disclaimer                                   │
│ Required fields: commentPostedAt                                │
│ Queryable: status="completed"                                   │
└─────────────────────────────────────────────────────────────────┘

### Error States:

- "scraping_failed" - Subsquare API error, invalid track
- "analysis_failed" - GitHub Actions failed, LLM timeout
- "voting_failed" - Transaction failed, insufficient balance
- "comment_failed" - Subsquare API error

### State Transitions:

discovered → scraped → analyzing → analyzed → voted → completed
     ↓           ↓          ↓           ↓        ↓         ↓
  (failed)   (failed)   (failed)    (failed) (failed)  (failed)
```

### Required Fields by Stage:

```javascript
// Stage 1: Discovery
{
  network: "polkadot",
  proposalId: 1234,
  status: "discovered",
  discoveredAt: Timestamp,
  scheduledScrapingAt: Timestamp
}

// Stage 2: Scraped
{
  ...previous,
  status: "scraped",
  track: 34,
  title: "Treasury Proposal",
  proposer: "15oF4...",
  blockHeight: 12345678,
  scrapedAt: Timestamp,
  scheduledInferenceAt: Timestamp,
  files: {
    rawData: "proposals/polkadot/1234/raw_subsquare_data.json",
    content: "proposals/polkadot/1234/content.md"
  }
}

// Stage 3: Analyzed
{
  ...previous,
  status: "analyzed",
  githubRunId: "123456",
  githubCommitSha: "abc123",
  finalDecision: "Aye",
  isUnanimous: false,
  isConclusive: true,
  analyzedAt: Timestamp,
  scheduledVotingAt: Timestamp,
  files: {
    ...previous.files,
    balthazar: "proposals/polkadot/1234/llm_analyses/balthazar.json",
    melchior: "proposals/polkadot/1234/llm_analyses/melchior.json",
    caspar: "proposals/polkadot/1234/llm_analyses/caspar.json",
    vote: "proposals/polkadot/1234/vote.json",
    manifest: "proposals/polkadot/1234/manifest.json"
  },
  votesBreakdown: [
    {model: "balthazar", decision: "Aye"},
    {model: "melchior", decision: "Aye"},
    {model: "caspar", decision: "Nay"}
  ]
}

// Stage 4: Voted
{
  ...previous,
  status: "voted",
  txHash: "0x123...",
  manifestHash: "5e8848...",
  votedAt: Timestamp,
  scheduledCommentAt: Timestamp
}

// Stage 5: Completed
{
  ...previous,
  status: "completed",
  commentPostedAt: Timestamp,
  completedAt: Timestamp
}
```

---

## 3. Do you have multiple users or a single automated pipeline?

### Answer: **Single automated pipeline, NO user authentication**

From code analysis:

**No user management:**
- No login system
- No user roles
- No permissions
- No user-triggered actions

**Fully automated:**
- Dispatcher runs on schedule (checks for new proposals)
- All flows triggered by Prefect orchestration
- GitHub Actions runs inference (public logs)
- Blockchain transactions signed by single proxy account

**Public transparency:**
- GitHub Actions logs are public
- S3 files served via CDN (public read)
- Blockchain transactions are public
- Subsquare comments are public

**Audit trail needs:**
- Track which GitHub run produced which vote
- Track which Prefect flow run triggered which stage
- Track timing of each stage
- Track errors and retries

### Firestore Schema Implications:

```javascript
// NO users collection needed
// NO authentication needed
// NO per-user permissions

// YES audit fields needed:
{
  createdAt: Timestamp,
  updatedAt: Timestamp,
  createdBy: "cybergov-dispatcher",  // System identifier
  lastModifiedBy: "cybergov-voter",  // System identifier
  prefectFlowRunId: "abc-123",       // For debugging
  githubRunId: "456789",             // For transparency
  version: 1                          // For optimistic locking
}
```

---

## 4. Do you ever need to update only parts of a proposal?

### Answer: **YES, frequent partial updates at each stage**

From code analysis:

**Update patterns:**

1. **Discovery → Scraping** (cybergov_dispatcher.py)
   ```javascript
   // Only update:
   { status: "discovered", scheduledScrapingAt: Timestamp }
   ```

2. **Scraping → Analysis** (cybergov_data_scraper.py)
   ```javascript
   // Only update:
   { 
     status: "scraped",
     track: 34,
     title: "...",
     files: { rawData: "...", content: "..." },
     scheduledInferenceAt: Timestamp
   }
   ```

3. **Analysis → Voting** (cybergov_evaluate_single_proposal_and_vote.py)
   ```javascript
   // Only update:
   {
     status: "analyzed",
     finalDecision: "Aye",
     votesBreakdown: [...],
     files: { ...previous, balthazar: "...", vote: "...", manifest: "..." },
     manifestHash: "...",
     githubRunId: "..."
   }
   ```

4. **Voting → Commenting** (cybergov_voter.py)
   ```javascript
   // Only update:
   {
     status: "voted",
     txHash: "0x123...",
     votedAt: Timestamp
   }
   ```

5. **Commenting → Completed** (cybergov_commenter.py)
   ```javascript
   // Only update:
   {
     status: "completed",
     commentPostedAt: Timestamp
   }
   ```

**Re-voting scenario** (from cybergov_data_scraper.py lines 248-295):
- Archives previous vote data to `vote_archive_0/`, `vote_archive_1/`, etc.
- Starts fresh analysis
- This is a FULL document update, not partial

### Firestore Schema Implications:

**Use field-level updates, NOT document replacement:**

```python
# Good - field-level update
doc_ref.update({
    "status": "analyzed",
    "finalDecision": "Aye",
    "analyzedAt": firestore.SERVER_TIMESTAMP,
    "files.vote": "proposals/polkadot/1234/vote.json"
})

# Bad - full document replacement (loses data)
doc_ref.set({...})  # DON'T DO THIS
```

**Keep documents small:**
- Store large JSON files in Firebase Storage
- Store only metadata + file paths in Firestore
- Store vote breakdown array (small, 3 items)
- Store summary fields (finalDecision, isUnanimous)

**Avoid nested maps for frequently updated fields:**
```javascript
// Bad - updating nested map triggers full map rewrite
{
  files: {
    rawData: "...",
    content: "...",
    balthazar: "...",  // Adding this rewrites entire 'files' map
    ...
  }
}

// Better - use dot notation for updates
doc_ref.update({
  "files.balthazar": "proposals/polkadot/1234/llm_analyses/balthazar.json"
})
```

---

## 5. Anything time-series based?

### Answer: **YES, multiple time-series patterns**

From code analysis:

**A. Proposal lifecycle timestamps:**
```javascript
{
  discoveredAt: Timestamp,
  scrapedAt: Timestamp,
  analyzedAt: Timestamp,
  votedAt: Timestamp,
  commentPostedAt: Timestamp,
  completedAt: Timestamp
}
```

**B. Scheduled task timestamps:**
```javascript
{
  scheduledScrapingAt: Timestamp,  // 2 days after discovery
  scheduledInferenceAt: Timestamp, // 30 min after scraping
  scheduledVotingAt: Timestamp,    // 30 min after analysis
  scheduledCommentAt: Timestamp    // 30 min after voting
}
```

**C. Re-vote history** (from cybergov_data_scraper.py):
- Previous votes archived to `vote_archive_0/`, `vote_archive_1/`, etc.
- Each archive contains full snapshot of previous vote
- Need to track: when re-vote happened, why, what changed

**D. Error/retry history:**
- Track failed attempts
- Track retry timestamps
- Track error messages

**E. Performance metrics:**
- Time from discovery to completion
- Time spent in each stage
- LLM inference duration
- Transaction confirmation time

### Firestore Schema Implications:

**Use subcollections for time-series data:**

```
proposals/{network}_{proposalId}/
  - Main document (current state)
  
  /history (subcollection)
    /{timestamp_auto_id}
      - status: "analyzed"
      - changedAt: Timestamp
      - changedBy: "cybergov-inference"
      - changes: { finalDecision: "Aye" }
  
  /votes (subcollection) - for re-votes
    /{vote_number}
      - voteNumber: 0
      - finalDecision: "Aye"
      - votedAt: Timestamp
      - txHash: "0x123..."
      - manifestHash: "abc..."
      - archived: false
    /{vote_number}
      - voteNumber: 1
      - finalDecision: "Nay"
      - votedAt: Timestamp
      - archived: true
  
  /errors (subcollection)
    /{timestamp_auto_id}
      - stage: "voting"
      - error: "Transaction failed"
      - occurredAt: Timestamp
      - retryCount: 2
```

**Query patterns:**
```python
# Get proposal history
proposals.document(f"{network}_{proposal_id}").collection("history").order_by("changedAt").get()

# Get all votes for proposal
proposals.document(f"{network}_{proposal_id}").collection("votes").order_by("voteNumber").get()

# Get recent errors
proposals.document(f"{network}_{proposal_id}").collection("errors").order_by("occurredAt", direction="DESCENDING").limit(10).get()
```

---

## 6. Does the voter UI need to search proposals?

### Answer: **NO voter UI, but YES to search needs**

From code analysis:

**No voter UI exists:**
- No web interface
- No search bar
- No user-facing dashboard

**But search IS needed for:**

1. **Debugging** - Find proposals by status, error, network
2. **Monitoring** - Find stuck proposals, failed votes
3. **Analytics** - Count proposals by decision, track, network
4. **Verification** - Find proposals by txHash, manifestHash

**Current "search" is done via:**
- S3 file listing (slow, expensive)
- Prefect API queries (external dependency)
- Manual inspection of logs

### Firestore Search Strategy:

**Use Firestore queries (no full-text search needed):**

```python
# Find proposals by status
db.collection("proposals").where("status", "==", "analyzing").get()

# Find failed proposals
db.collection("proposals").where("status", "==", "voting_failed").get()

# Find proposals by network and track
db.collection("proposals").where("network", "==", "polkadot").where("track", "==", 34).get()

# Find proposals by decision
db.collection("proposals").where("finalDecision", "==", "Aye").get()

# Find proposals by date range
db.collection("proposals").where("votedAt", ">=", start_date).where("votedAt", "<=", end_date).get()
```

**For text search (title, content):**
- Store in Firebase Storage (files)
- Use Firestore for metadata only
- If needed later, add Algolia or Typesense

**For hash lookup:**
```python
# Find by manifestHash
db.collection("proposals").where("manifestHash", "==", "5e8848...").get()

# Find by txHash
db.collection("proposals").where("txHash", "==", "0x123...").get()
```

---

## 7. Expected scale?

### Answer: **Low to medium scale, but plan for growth**

From code analysis:

**Current scale (from constants.py):**

```python
# Networks: 3 active
networks = ["polkadot", "kusama", "paseo"]

# Tracks: 7 allowed
ALLOWED_TRACK_IDS = [2, 11, 30, 31, 32, 33, 34]

# Min proposal IDs (historical data):
min_proposal_id = {
    "polkadot": 1740,  # Started at proposal 1740
    "kusama": 585,     # Started at proposal 585
    "paseo": 103       # Started at proposal 103
}
```

**Estimated volume:**

**Proposals per day:**
- Polkadot: ~2-5 proposals/day (estimate)
- Kusama: ~1-3 proposals/day (estimate)
- Paseo: ~1-2 proposals/day (testnet)
- **Total: ~5-10 proposals/day across all networks**

**Proposals per year:**
- ~1,800-3,650 proposals/year

**Total historical count:**
- Polkadot: ~1,740+ proposals
- Kusama: ~585+ proposals
- Paseo: ~103+ proposals
- **Total: ~2,500+ proposals**

**LLM runs per proposal:**
- 3 agents (balthazar, melchior, caspar)
- 1 content generation LLM call
- **Total: 4 LLM calls per proposal**

**Files per proposal:**
- raw_subsquare_data.json (~5-50 KB)
- content.md (~10-100 KB)
- balthazar.json (~2-10 KB)
- melchior.json (~2-10 KB)
- caspar.json (~2-10 KB)
- vote.json (~5-20 KB)
- manifest.json (~2-5 KB)
- **Total: ~30-200 KB per proposal**

**Storage needs:**
- Current: ~2,500 proposals × 100 KB = ~250 MB
- Per year: ~2,000 proposals × 100 KB = ~200 MB/year
- 5 years: ~1 GB

**Re-votes:**
- Rare (governance changes, errors)
- Estimate: ~1-5% of proposals
- Adds: vote_archive_0/, vote_archive_1/, etc.

### Firestore Scale Implications:

**No sharding needed:**
- <10K documents per year
- Firestore handles millions of documents easily
- Single collection is fine

**No subcollection splitting needed:**
- History subcollection: ~5-10 entries per proposal
- Votes subcollection: ~1-2 entries per proposal (rare re-votes)
- Errors subcollection: ~0-5 entries per proposal

**Composite indexes needed:**
```javascript
// Index 1: Query by network + status
{
  collection: "proposals",
  fields: [
    { field: "network", order: "ASCENDING" },
    { field: "status", order: "ASCENDING" }
  ]
}

// Index 2: Query by network + votedAt
{
  collection: "proposals",
  fields: [
    { field: "network", order: "ASCENDING" },
    { field: "votedAt", order: "DESCENDING" }
  ]
}

// Index 3: Query by network + track
{
  collection: "proposals",
  fields: [
    { field: "network", order: "ASCENDING" },
    { field: "track", order: "ASCENDING" }
  ]
}

// Index 4: Query by finalDecision + votedAt
{
  collection: "proposals",
  fields: [
    { field: "finalDecision", order: "ASCENDING" },
    { field: "votedAt", order: "DESCENDING" }
  ]
}
```

**Cost estimate (Firebase free tier):**
- Storage: 1 GB free (sufficient for 5+ years)
- Reads: 50K/day free (sufficient)
- Writes: 20K/day free (sufficient)
- **Conclusion: Free tier is sufficient**

---

## Summary Table

| Question | Answer | Impact on Schema |
|----------|--------|------------------|
| **1. Query patterns** | Max ID, by status, by track, by decision, by timestamp, check existence | Need indexes on: network+status, network+track, finalDecision, timestamps |
| **2. Lifecycle** | 5 stages: discovered → scraped → analyzed → voted → completed | Need status field, stage-specific fields, transition timestamps |
| **3. Multiple users** | NO - single automated pipeline | NO users collection, YES audit fields (githubRunId, prefectFlowRunId) |
| **4. Partial updates** | YES - frequent field-level updates at each stage | Use field updates, NOT document replacement. Keep docs small. |
| **5. Time-series** | YES - lifecycle timestamps, re-votes, errors, performance | Use subcollections for history, votes, errors |
| **6. Text search** | NO UI, but need metadata search | Use Firestore queries, NO full-text search needed |
| **7. Scale** | ~5-10 proposals/day, ~2K/year, 4 LLM calls each | Single collection, no sharding, composite indexes, free tier sufficient |

---

## Next Steps

With these answers, you can now design:

1. ✅ Complete Firestore schema (collections, documents, subcollections)
2. ✅ Composite indexes configuration
3. ✅ Python Writer API (createProposal, updateStatus, etc.)
4. ✅ Integration with Firebase Storage paths
5. ✅ Prefect-ready functions for existing flows

Ready for the schema design!
