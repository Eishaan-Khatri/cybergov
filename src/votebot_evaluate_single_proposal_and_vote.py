import sys
import json
import datetime
import os
import hashlib
from pathlib import Path
from collections import Counter

# Firestore
import firebase_admin
from firebase_admin import credentials as fb_credentials
from firebase_admin import firestore as admin_firestore

# Internal utils
from utils.helpers import setup_logging, get_config_from_env, hash_file
from utils.run_magi_eval import run_single_inference, setup_compiled_agent

logger = setup_logging()


# ------------------------------------------------------------------------------
# FIREBASE INITIALIZATION
# ------------------------------------------------------------------------------

def initialize_firebase_app_if_needed(service_account_dict=None):
    """Idempotent Firebase initialization."""
    if firebase_admin._apps:
        return

    if service_account_dict:
        cred = fb_credentials.Certificate(service_account_dict)
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()


def get_firestore_client():
    return admin_firestore.client()


# ------------------------------------------------------------------------------
# LOAD MAGI PERSONALITIES
# ------------------------------------------------------------------------------

def load_magi_personalities() -> dict[str, str]:
    personalities = {}
    prompts_dir = Path(__file__).parent.parent / "templates" / "system_prompts"
    names = ["balthazar", "melchior", "caspar"]

    for name in names:
        fpath = prompts_dir / f"{name}_system_prompt.md"
        try:
            if fpath.exists():
                personalities[name] = fpath.read_text(encoding="utf-8").strip()
                logger.info(f"Loaded {name} prompt from {fpath}")
            else:
                logger.warning(f"System prompt NOT found: {fpath}")
        except Exception as e:
            logger.error(f"Failed loading system prompt {name}: {e}")

    return personalities


# ------------------------------------------------------------------------------
# SUMMARY RATIONALE
# ------------------------------------------------------------------------------

def generate_summary_rationale(votes_breakdown, proposal_id, network, analysis_files):
    logger.info("--> Generating simple concatenated rationale...")

    github_run_id = os.getenv("GITHUB_RUN_ID", "N/A")

    aye_votes = sum(v["decision"] == "Aye" for v in votes_breakdown)
    nay_votes = sum(v["decision"] == "Nay" for v in votes_breakdown)
    abstain_votes = sum(v["decision"] == "Abstain" for v in votes_breakdown)

    balthazar_rationale = melchior_rationale = caspar_rationale = None
    balthazar_decision = melchior_decision = caspar_decision = None

    for af in analysis_files:
        data = json.loads(Path(af).read_text())
        if af.name == "balthazar.json":
            balthazar_rationale = data["rationale"]
            balthazar_decision = data["decision"]
        if af.name == "melchior.json":
            melchior_rationale = data["rationale"]
            melchior_decision = data["decision"]
        if af.name == "caspar.json":
            caspar_rationale = data["rationale"]
            caspar_decision = data["decision"]

    return f"""
<p>A panel of autonomous agents reviewed this proposal, resulting in a vote of
<strong>{aye_votes} AYE</strong>, <strong>{nay_votes} NAY</strong>, and
<strong>{abstain_votes} ABSTAIN</strong>.</p>

<h3>Balthazar voted <u>{balthazar_decision}</u></h3>
<blockquote>{balthazar_rationale}</blockquote>

<h3>Melchior voted <u>{melchior_decision}</u></h3>
<blockquote>{melchior_rationale}</blockquote>

<h3>Caspar voted <u>{caspar_decision}</u></h3>
<blockquote>{caspar_rationale}</blockquote>

<h3>System Transparency</h3>
<p>All analysis files and manifest are stored in Firestore under this proposal document.</p>
"""


# ------------------------------------------------------------------------------
# PREFLIGHT (FIRESTORE VERSION)
# ------------------------------------------------------------------------------

def perform_preflight_checks(proposal_doc_ref, local_workspace):
    logger.info("01 - Performing pre-flight checks (Firestore)...")
    manifest_inputs = []

    snap = proposal_doc_ref.get()
    if not snap.exists:
        logger.error("Firestore proposal doc does NOT exist.")
        sys.exit(1)

    doc = snap.to_dict()
    files = doc.get("files", {})

    # 1) RAW DATA
    raw_data = files.get("rawData") or doc.get("rawData")
    if not raw_data:
        logger.error("rawData not found in Firestore.")
        sys.exit(1)

    raw_path = local_workspace / "raw_subsquare.json"
    raw_path.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")

    manifest_inputs.append({
        "logical_name": "rawData",
        "firestore_path": f"proposals/{proposal_doc_ref.id}/files/rawData",
        "hash": hash_file(raw_path)
    })
    logger.info("✔ rawData validated.")

    # 2) CONTENT
    content = files.get("content")
    if not content:
        # fallback: extract from raw_data
        content = raw_data.get("content") or raw_data.get("body")
        if not content:
            logger.error("content markdown not found.")
            sys.exit(1)

    content_path = local_workspace / "content.md"
    content_path.write_text(content, encoding="utf-8")

    manifest_inputs.append({
        "logical_name": "content",
        "firestore_path": f"proposals/{proposal_doc_ref.id}/files/content",
        "hash": hash_file(content_path)
    })
    logger.info("✔ content.md ready.")

    # 3) SYSTEM PROMPTS
    prompt_dir = Path("templates/system_prompts")
    for name in ["balthazar", "caspar", "melchior"]:
        f = prompt_dir / f"{name}_system_prompt.md"
        if not f.exists():
            logger.error(f"Prompt missing: {f}")
            sys.exit(1)
    logger.info("✔ All system prompts exist.")

    return manifest_inputs, content_path, ["balthazar", "caspar", "melchior"]


# ------------------------------------------------------------------------------
# RUN MAGI
# ------------------------------------------------------------------------------

def run_magi_evaluations(magi_models_list, local_workspace):
    logger.info("02 - Running MAGI evaluations...")
    analysis_dir = local_workspace / "llm_analyses"
    analysis_dir.mkdir(exist_ok=True)

    personalities = load_magi_personalities()

    # Choose models
    magi_llms = {
        "balthazar": "openai/gpt-4o",
        "melchior": "openrouter/google/gemini-2.5-pro-preview",
        "caspar": "openrouter/x-ai/grok-code-fast-1",
    }

    proposal_text = (local_workspace / "content.md").read_text()

    outputs = []
    for key in magi_models_list:
        model_id = magi_llms[key]
        personality = personalities[key]

        logger.info(f"--- Magi: {key.upper()} using {model_id} ---")
        compiled = setup_compiled_agent(model_id=model_id)

        prediction = run_single_inference(compiled, personality, proposal_text)

        out_path = analysis_dir / f"{key}.json"
        data = {
            "model_name": model_id,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "decision": prediction.vote.strip(),
            "confidence": None,
            "rationale": prediction.rationale.strip(),
            "raw_api_response": {}
        }
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        outputs.append(out_path)

        logger.info(f"✔ Saved {out_path.name}")

    return outputs


# ------------------------------------------------------------------------------
# CONSOLIDATE VOTE
# ------------------------------------------------------------------------------

def consolidate_vote(analysis_files, local_workspace, proposal_id, network):
    logger.info("03 - Consolidating votes...")

    votes = []
    decisions = []

    for af in analysis_files:
        data = json.loads(Path(af).read_text())
        decision_raw = data["decision"].strip().upper()

        if decision_raw == "AYE":
            decision = "Aye"
        elif decision_raw == "NAY":
            decision = "Nay"
        else:
            decision = "Abstain"

        votes.append({
            "model": af.stem,
            "decision": decision,
            "confidence": data["confidence"]
        })
        decisions.append(decision)

    # Voting logic
    if not decisions:
        final = "Abstain"
        unanimous = False
        conclusive = False
    else:
        unanimous = len(set(decisions)) == 1
        if unanimous:
            final = decisions[0]
            conclusive = True
        else:
            count = Counter(decisions)
            if count["Aye"] == 2:
                final = "Aye"
            elif count["Nay"] == 2:
                final = "Nay"
            else:
                final = "Abstain"
            conclusive = False

    vote_data = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "is_conclusive": conclusive,
        "final_decision": final,
        "is_unanimous": unanimous,
        "summary_rationale": generate_summary_rationale(
            votes, proposal_id, network, analysis_files
        ),
        "votes_breakdown": votes
    }

    out_path = local_workspace / "vote.json"
    out_path.write_text(json.dumps(vote_data, indent=2), encoding="utf-8")
    logger.info(f"✔ vote.json generated.")
    return out_path


# ------------------------------------------------------------------------------
# FIRESTORE UPLOAD + MANIFEST
# ------------------------------------------------------------------------------

def upload_outputs_and_generate_manifest(proposal_doc_ref, local_workspace, analysis_files, vote_file, manifest_inputs):
    logger.info("04 - Uploading outputs to Firestore...")

    manifest_outputs = []
    all_files = analysis_files + [vote_file]

    for lf in all_files:
        lf = Path(lf)
        content = lf.read_text(encoding="utf-8")
        file_hash = hash_file(lf)

        logical = lf.stem

        proposal_doc_ref.update({
            f"files.outputs.{logical}.content": content,
            f"files.outputs.{logical}.hash": file_hash,
            f"files.outputs.{logical}.timestamp_utc":
                datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

        manifest_outputs.append({
            "logical_name": logical,
            "firestore_path": f"proposals/{proposal_doc_ref.id}/files/outputs/{logical}",
            "hash": file_hash
        })

        logger.info(f"✔ Uploaded {logical} to Firestore.")

    manifest = {
        "provenance": {
            "job_name": "LLM Inference and Voting",
            "github_repository": os.getenv("GITHUB_REPOSITORY", "N/A"),
            "github_run_id": os.getenv("GITHUB_RUN_ID", "N/A"),
            "github_commit_sha": os.getenv("GITHUB_SHA", "N/A"),
            "timestamp_utc":
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        "inputs": manifest_inputs,
        "outputs": manifest_outputs
    }

    manifest_path = local_workspace / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # save manifest to Firestore
    proposal_doc_ref.update({
        "files.manifest": manifest,
        "files.manifest_timestamp":
            datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

    logger.info("✔ Manifest written to Firestore.")
    return manifest


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------

def main():
    logger.info("CyberGov V0 ... starting Firestore evaluation.")

    last_step = "initializing"

    try:
        config = get_config_from_env()

        # Init Firebase
        sa_path = config.get("FIREBASE_SA_PATH")
        sa_dict = json.loads(Path(sa_path).read_text()) if sa_path and Path(sa_path).exists() else None
        initialize_firebase_app_if_needed(sa_dict)

        db = get_firestore_client()

        proposal_id = config["PROPOSAL_ID"]
        network = config["NETWORK"]
        doc_id = f"{network}-{proposal_id}"

        proposal_doc_ref = db.collection("proposals").document(doc_id)
        local_workspace = Path("workspace")
        local_workspace.mkdir(exist_ok=True)

        last_step = "preflight"
        manifest_inputs, content_path, magi_models = perform_preflight_checks(proposal_doc_ref, local_workspace)

        last_step = "magi_evaluation"
        analysis_files = run_magi_evaluations(magi_models, local_workspace)

        last_step = "vote_consolidation"
        vote_file = consolidate_vote(analysis_files, local_workspace, proposal_id, network)

        last_step = "manifest_and_upload"
        upload_outputs_and_generate_manifest(proposal_doc_ref, local_workspace, analysis_files, vote_file, manifest_inputs)

        logger.info("🎉 CyberGov Firestore evaluation complete!")

    except Exception as e:
        logger.error("💥 Error during evaluation.")
        logger.error(f"Last successful step: {last_step}")
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
