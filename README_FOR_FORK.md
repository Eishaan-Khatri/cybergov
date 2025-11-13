# Welcome to Your CyberGov Fork! 🎉

Congratulations on forking CyberGov! This document will help you understand what you have and how to run it.

## 📚 Documentation Files Created

I've created comprehensive documentation for you:

1. **CODEBASE_OVERVIEW.md** - Complete technical deep-dive
   - Architecture explanation
   - Every file and function documented
   - Security features explained
   - Technology stack details

2. **QUICK_START_GUIDE.md** - Step-by-step setup instructions
   - Prerequisites and installation
   - Environment configuration
   - Testing individual components
   - Production deployment guide

3. **SYSTEM_FLOW.txt** - Visual flow diagrams
   - Complete system workflow
   - Data flow through S3
   - Vote consolidation logic
   - Timing and delays

4. **This file** - Quick orientation

## 🎯 What is CyberGov?

CyberGov is an **autonomous AI governance system** for Polkadot/Kusama that:

- Uses 3 independent LLM agents (MAGI system from Evangelion)
- Analyzes governance proposals automatically
- Votes on-chain with transparent, verifiable execution
- Posts detailed rationales to Subsquare

**Key Innovation**: All LLM inference runs on GitHub Actions (public logs) with cryptographic attestation (manifest hash as on-chain remark).

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install packages
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create `.env` file:

```bash
PROPOSAL_ID=1234
NETWORK=polkadot
S3_BUCKET_NAME=your-bucket
S3_ACCESS_KEY_ID=your-key
S3_ACCESS_KEY_SECRET=your-secret
S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud
OPENROUTER_API_KEY=your-key
```

### 3. Test It!

```bash
# Scrape a proposal
python src/cybergov_data_scraper.py polkadot 1234

# Run LLM analysis (requires OpenRouter API key)
python src/cybergov_evaluate_single_proposal_and_vote.py
```

## 📁 Project Structure

```
cybergov/
├── src/                    # Main application
│   ├── cybergov_dispatcher.py       # Monitors new proposals
│   ├── cybergov_data_scraper.py     # Fetches data
│   ├── cybergov_inference.py        # Triggers GitHub Actions
│   ├── cybergov_evaluate_single_proposal_and_vote.py  # Core logic
│   ├── cybergov_voter.py            # Submits votes
│   ├── cybergov_commenter.py        # Posts comments
│   └── utils/                       # Helper functions
├── templates/              # MAGI personality prompts
├── tests/                  # Unit tests
├── infra/                  # Docker Compose for Prefect
└── .github/workflows/      # GitHub Actions
```

## 🔄 How It Works (Simple Version)

```
1. DISPATCHER → Finds new proposals
2. SCRAPER → Downloads proposal data
3. INFERENCE → Runs 3 LLM agents on GitHub Actions
   - Balthazar (GPT-4o): Strategic analyst
   - Melchior (Gemini): Ecosystem growth
   - Caspar (Grok): Risk & sustainability
4. VOTER → Submits consolidated vote on-chain
5. COMMENTER → Posts rationale to Subsquare
```

## 🎓 Learning Path

### Beginner (Just want to understand)
1. Read **QUICK_START_GUIDE.md** sections 1-3
2. Look at **SYSTEM_FLOW.txt** diagrams
3. Run the scraper on a test proposal

### Intermediate (Want to run it)
1. Complete **QUICK_START_GUIDE.md** fully
2. Set up S3 storage
3. Get OpenRouter API key
4. Run full pipeline locally

### Advanced (Want to deploy)
1. Read **CODEBASE_OVERVIEW.md** completely
2. Set up Prefect orchestration
3. Configure GitHub Actions
4. Set up Substrate accounts
5. Deploy to production

## 🔑 What You Need

### Required
- Python 3.11+
- S3-compatible storage (Scaleway, AWS, etc.)
- OpenRouter API key (for LLM access)

### Optional (for production)
- Docker (for Prefect)
- GitHub account (for transparent inference)
- Polkadot/Kusama accounts (for voting)

## 💡 Key Concepts

### The MAGI System
Three independent AI agents vote on each proposal:
- **Balthazar**: Focuses on competitive advantage
- **Melchior**: Focuses on ecosystem growth
- **Caspar**: Focuses on sustainability & risk

### Vote Consolidation
```
2 Aye + 1 Abstain = Aye
2 Nay + 1 Abstain = Nay
2 Aye + 1 Nay = Abstain
```

### Transparency
- All inference runs on GitHub Actions (public logs)
- Manifest hash included as on-chain remark
- Anyone can verify the vote was computed correctly

## 🧪 Testing

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v
```

## 📖 Next Steps

1. **Read the docs** - Start with QUICK_START_GUIDE.md
2. **Test locally** - Run scraper and inference
3. **Understand the code** - Read CODEBASE_OVERVIEW.md
4. **Customize** - Modify MAGI personalities
5. **Deploy** - Set up production environment

## 🆘 Need Help?

### Documentation
- **QUICK_START_GUIDE.md** - Setup and testing
- **CODEBASE_OVERVIEW.md** - Technical details
- **SYSTEM_FLOW.txt** - Visual diagrams

### Community
- GitHub Issues: https://github.com/KarimJedda/cybergov/issues
- Discussions: https://github.com/KarimJedda/cybergov/discussions
- Forum: https://forum.polkadot.network/

### Common Issues

**"S3 file not found"**
→ Run scraper first: `python src/cybergov_data_scraper.py polkadot 1234`

**"OpenRouter API error"**
→ Check your API key and balance

**"Invalid track ID"**
→ Expected - system only votes on specific tracks

## ⚠️ Important Notes

1. This is **experimental software**
2. LLMs can make mistakes
3. Start with test networks (Paseo)
4. Never commit secrets to git
5. Monitor API costs

## 🎯 Quick Reference

### Manual Execution
```bash
# 1. Scrape
python src/cybergov_data_scraper.py polkadot 1234

# 2. Analyze (local)
python src/cybergov_evaluate_single_proposal_and_vote.py

# 3. Vote (requires accounts)
python src/cybergov_voter.py polkadot 1234

# 4. Comment
python src/cybergov_commenter.py polkadot 1234
```

### File Locations
- **Agent personalities**: `templates/system_prompts/*.md`
- **Configuration**: `src/utils/constants.py`
- **Tests**: `tests/`
- **Workflows**: `.github/workflows/`

### Key URLs
- Prefect UI: http://localhost:4200
- Subscan: https://polkadot.subscan.io
- Subsquare: https://polkadot.subsquare.io

## 🚀 Ready to Start?

1. Open **QUICK_START_GUIDE.md**
2. Follow the setup instructions
3. Run your first test
4. Explore the code
5. Have fun! 🎉

---

**Questions?** Check the documentation files or open an issue on GitHub.

**Want to contribute?** Read CODEBASE_OVERVIEW.md and submit a PR!

Good luck with your CyberGov journey! 🤖
