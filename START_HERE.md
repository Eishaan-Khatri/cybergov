# 🚀 START HERE - CyberGov Documentation

Welcome to your forked CyberGov repository! This is your starting point.

---

## 🎯 What You Have

You've forked **CyberGov** - an autonomous AI governance system that uses three independent LLM agents to analyze and vote on Polkadot/Kusama governance proposals.

**Key Innovation**: Transparent, verifiable AI voting with public execution logs and cryptographic attestation.

---

## 📚 Complete Documentation Created

I've analyzed the entire codebase and created comprehensive documentation:

### Core Documentation (Read in Order)

1. **README_FOR_FORK.md** ⭐ START HERE
   - Quick 5-minute orientation
   - What is CyberGov?
   - Quick start guide
   - Where to go next

2. **QUICK_START_GUIDE.md**
   - Step-by-step setup (30 min)
   - Testing procedures
   - First run walkthrough
   - Debugging tips

3. **SYSTEM_FLOW.txt**
   - Visual workflow diagrams
   - Data flow through S3
   - Vote consolidation logic
   - Command reference

### Reference Documentation

4. **CONFIGURATION_GUIDE.md**
   - Complete configuration reference
   - Environment variables
   - Prefect blocks
   - S3 setup
   - Substrate accounts

5. **TROUBLESHOOTING_GUIDE.md**
   - Common errors and solutions
   - Debugging tips
   - Performance optimization
   - Getting help

6. **CODEBASE_OVERVIEW.md**
   - Complete technical deep-dive
   - Architecture explanation
   - Every file documented
   - Security features
   - Technology stack

7. **DOCUMENTATION_INDEX.md**
   - Master index of all docs
   - Learning paths
   - Quick reference
   - Topic finder

---

## 🎓 Choose Your Path

### Path 1: "Just Exploring" (20 minutes)

```
1. Read README_FOR_FORK.md
2. Skim SYSTEM_FLOW.txt
3. Look at templates/system_prompts/*.md
```

**Outcome**: Understand what CyberGov does

---

### Path 2: "Want to Test Locally" (2 hours)

```
1. Read README_FOR_FORK.md
2. Follow QUICK_START_GUIDE.md (sections 1-3)
3. Set up environment
4. Run scraper: python src/cybergov_data_scraper.py polkadot 1234
5. Run inference: python src/cybergov_evaluate_single_proposal_and_vote.py
6. Check output in workspace/
```

**Outcome**: Successfully run the system locally

---

### Path 3: "Deploy to Production" (1 day)

```
1. Complete Path 2
2. Read CONFIGURATION_GUIDE.md
3. Set up Prefect (docker-compose up -d)
4. Configure GitHub Actions
5. Set up Substrate accounts
6. Deploy workflows
7. Monitor first automated run
```

**Outcome**: Fully automated system

---

### Path 4: "Customize & Contribute" (2-3 days)

```
1. Complete Path 3
2. Read CODEBASE_OVERVIEW.md completely
3. Review source code
4. Run tests: pytest tests/
5. Make changes
6. Submit PR
```

**Outcome**: Deep understanding, ready to contribute

---

## ⚡ Quick Start (5 Minutes)

Want to see it work right now?

```bash
# 1. Install dependencies
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Set environment variables (create .env file)
PROPOSAL_ID=1234
NETWORK=polkadot
S3_BUCKET_NAME=your-bucket
S3_ACCESS_KEY_ID=your-key
S3_ACCESS_KEY_SECRET=your-secret
S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud
OPENROUTER_API_KEY=your-key

# 3. Test scraper
python src/cybergov_data_scraper.py polkadot 1234

# 4. Check output
# Files created in S3: raw_subsquare_data.json, content.md
```

---

## 🔑 What You Need

### Required (for local testing)
- ✅ Python 3.11+
- ✅ S3-compatible storage (Scaleway, AWS)
- ✅ OpenRouter API key

### Optional (for production)
- Docker (for Prefect)
- GitHub account (for transparent inference)
- Polkadot/Kusama accounts (for voting)

---

## 📖 Documentation Map

```
START_HERE.md (you are here)
    ↓
README_FOR_FORK.md (5 min read)
    ↓
QUICK_START_GUIDE.md (30 min read)
    ↓
SYSTEM_FLOW.txt (10 min read)
    ↓
CONFIGURATION_GUIDE.md (45 min read)
    ↓
CODEBASE_OVERVIEW.md (2 hour read)
    ↓
TROUBLESHOOTING_GUIDE.md (reference)
    ↓
DOCUMENTATION_INDEX.md (master index)
```

---

## 🎯 Key Concepts (Quick Version)

### The MAGI System

Three independent AI agents vote on each proposal:

- **Balthazar** (GPT-4o): Strategic analyst
- **Melchior** (Gemini): Ecosystem growth
- **Caspar** (Grok): Risk & sustainability

### Vote Consolidation

```
2 Aye + 1 Abstain = Aye
2 Nay + 1 Abstain = Nay
2 Aye + 1 Nay = Abstain
3 Aye = Aye (unanimous)
```

### Transparency

- All inference runs on GitHub Actions (public logs)
- Manifest hash included as on-chain remark
- Anyone can verify the vote

---

## 🔄 How It Works (Simple)

```
1. DISPATCHER → Monitors blockchain for new proposals
2. SCRAPER → Downloads proposal data from Subsquare
3. INFERENCE → Runs 3 LLM agents on GitHub Actions
4. VOTER → Submits consolidated vote on-chain
5. COMMENTER → Posts rationale to Subsquare
```

---

## 📁 Project Structure

```
cybergov/
├── src/                    # Main application code
│   ├── cybergov_dispatcher.py
│   ├── cybergov_data_scraper.py
│   ├── cybergov_inference.py
│   ├── cybergov_evaluate_single_proposal_and_vote.py
│   ├── cybergov_voter.py
│   ├── cybergov_commenter.py
│   └── utils/
├── templates/              # MAGI personality prompts
│   └── system_prompts/
├── tests/                  # Unit tests
├── infra/                  # Docker Compose for Prefect
├── .github/workflows/      # GitHub Actions
└── docs/                   # This documentation
```

---

## 🚦 Next Steps

### Right Now (5 minutes)

1. ✅ You're reading START_HERE.md
2. → Open **README_FOR_FORK.md**
3. → Decide which path to follow

### Today (1-2 hours)

1. → Read **QUICK_START_GUIDE.md**
2. → Set up environment
3. → Run first test

### This Week

1. → Complete local testing
2. → Read **CODEBASE_OVERVIEW.md**
3. → Understand architecture
4. → Plan deployment or customization

---

## 🆘 Need Help?

### Documentation

- **Can't find something?** → DOCUMENTATION_INDEX.md
- **Something not working?** → TROUBLESHOOTING_GUIDE.md
- **Need to configure?** → CONFIGURATION_GUIDE.md

### Community

- **GitHub Issues**: https://github.com/KarimJedda/cybergov/issues
- **Discussions**: https://github.com/KarimJedda/cybergov/discussions
- **Forum**: https://forum.polkadot.network/

---

## ⚠️ Important Notes

1. This is **experimental software**
2. LLMs can make mistakes
3. Start with test networks (Paseo)
4. Never commit secrets to git
5. Monitor API costs

---

## ✅ Pre-Flight Checklist

Before you start:

- [ ] I understand what CyberGov does
- [ ] I have Python 3.11+ installed
- [ ] I have access to S3 storage (or can set it up)
- [ ] I have an OpenRouter API key (or can get one)
- [ ] I've read README_FOR_FORK.md
- [ ] I know which learning path to follow
- [ ] I have TROUBLESHOOTING_GUIDE.md bookmarked

---

## 🎉 You're Ready!

Everything you need is documented. The codebase has been fully analyzed and explained.

**Your next step**: Open **README_FOR_FORK.md** and start your journey!

---

## 📊 Documentation Summary

| Document | Purpose | Time | When to Read |
|----------|---------|------|--------------|
| START_HERE.md | Orientation | 5 min | Right now |
| README_FOR_FORK.md | Quick start | 5 min | First |
| QUICK_START_GUIDE.md | Setup guide | 30 min | Second |
| SYSTEM_FLOW.txt | Visual diagrams | 10 min | Third |
| CONFIGURATION_GUIDE.md | Config reference | 45 min | Before production |
| TROUBLESHOOTING_GUIDE.md | Error solutions | As needed | When stuck |
| CODEBASE_OVERVIEW.md | Technical deep-dive | 2 hours | Before customizing |
| DOCUMENTATION_INDEX.md | Master index | 5 min | Reference |

**Total reading time**: ~4 hours for complete understanding

---

## 🚀 Ready to Begin?

```bash
# Open the next document
cat README_FOR_FORK.md

# Or jump straight to setup
cat QUICK_START_GUIDE.md
```

**Good luck with your CyberGov journey! 🤖**

---

*Questions? Check DOCUMENTATION_INDEX.md for the master index of all topics.*
