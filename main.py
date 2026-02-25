from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import subprocess
import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ClawAudit", description="Open audit attestation layer: AI audit + verifiable proof.")

# --- Open audit attestation registry (the "one open channel") ---
REGISTRY_PATH = Path(__file__).parent / "data" / "audit_registry.json"
REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

def _load_registry():
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    return {}

def _save_registry(registry: dict):
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)

def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def attest_audit(contract_code: str, report: str, contract_address: str | None = None) -> dict:
    code_hash = _hash(contract_code.strip())
    report_hash = _hash(report.strip())
    ts = datetime.now(timezone.utc).isoformat()
    proof = {
        "code_hash": code_hash,
        "report_hash": report_hash,
        "timestamp": ts,
        "auditor": "ClawAudit",
        "contract_address": contract_address,
    }
    registry = _load_registry()
    registry[code_hash] = proof
    if contract_address:
        registry[f"addr:{contract_address.lower()}"] = proof
    _save_registry(registry)
    return proof

def get_attestation(code_hash: str | None = None, contract_address: str | None = None) -> dict | None:
    registry = _load_registry()
    if code_hash:
        return registry.get(code_hash)
    if contract_address:
        return registry.get(f"addr:{contract_address.lower()}")
    return None

KEYS = [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")]

# Paths to the agent's auth config (mounted into container as ~/.openclaw). OpenClaw may read
# either file for the Gemini key, so we write the key we're using to both before each scan.
AGENT_DIR = Path(__file__).parent / "agent_config" / "agents" / "main" / "agent"
AUTH_PROFILES_PATH = AGENT_DIR / "auth-profiles.json"
AUTH_JSON_PATH = AGENT_DIR / "auth.json"

def _set_agent_gemini_key(key: str) -> None:
    """Write the given Gemini key into auth-profiles.json and auth.json so the agent uses it (no stale keys)."""
    key = (key or "").strip()
    if not key:
        return
    # 1) auth-profiles.json: update both google profiles and clear cooldown so OpenClaw uses this key
    if AUTH_PROFILES_PATH.exists():
        try:
            with open(AUTH_PROFILES_PATH) as f:
                data = json.load(f)
            for name in ("google:default", "google:manual"):
                if name in data.get("profiles", {}):
                    if "key" in data["profiles"][name]:
                        data["profiles"][name]["key"] = key
                    if "token" in data["profiles"][name]:
                        data["profiles"][name]["token"] = key
            # Clear cooldown/failure so OpenClaw doesn't skip this profile after a previous rate limit
            if "usageStats" in data and isinstance(data["usageStats"], dict):
                for prof in ("google:manual", "google:default"):
                    if prof in data["usageStats"] and isinstance(data["usageStats"][prof], dict):
                        data["usageStats"][prof].pop("cooldownUntil", None)
                        data["usageStats"][prof].pop("failureCounts", None)
            with open(AUTH_PROFILES_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
    # 2) auth.json: OpenClaw may read this; keep it in sync so no stale key is used
    if AUTH_JSON_PATH.exists():
        try:
            with open(AUTH_JSON_PATH) as f:
                data = json.load(f)
            if "google" in data and isinstance(data["google"], dict):
                data["google"]["key"] = key
                if "token" in data["google"]:
                    data["google"]["token"] = key
            with open(AUTH_JSON_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

# MOLTBOOK_API_KEY must be set so the container's Moltbook skill can POST; validate once at request time
def _get_moltbook_key() -> str:
    key = os.getenv("MOLTBOOK_API_KEY")
    if not key or key.strip() == "" or key == "None":
        raise HTTPException(
            status_code=500,
            detail="MOLTBOOK_API_KEY is missing or empty in .env. Add it and restart the app.",
        )
    return key.strip()

class ScanRequest(BaseModel):
    contract_code: str
    contract_address: str | None = None  # optional; if set, attestation is also queryable by address

@app.post("/scan")
def run_scan(req: ScanRequest):
    available_keys = [str(k).strip() for k in KEYS if k and str(k).strip()]
    if not available_keys:
        raise HTTPException(status_code=500, detail="API Keys missing: set GEMINI_API_KEY and/or GEMINI_API_KEY_2 in .env")

    moltbook_key = _get_moltbook_key()
    submolt = (os.getenv("MOLTBOOK_SUBMOLT") or "lablab").strip()
    telegram_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    telegram_chat = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

    prompt = f"""You are an elite Web3 security auditor. Analyze this Solidity code and complete the following steps in order.

Code to analyze:
{req.contract_code}

Step 1 — Console output (for the user's dashboard): Write a full vulnerability report to the console. Include: CRITICAL FINDINGS (type and location), EXPLOIT SCENARIO (how an attacker would exploit it in one sentence), and PATCHED CODE (corrected Solidity). All of this must appear in your reply so it is shown on the page.

Step 2 — Telegram (full audit trail to developer): Use your 'telegram' tool to send the **full audit trail** to the developer channel. The message must include: the complete vulnerability report — vulnerability name(s), severity, locations, exploit scenario, and remediation (patched code or clear fix steps). Send the same level of detail as the console report so the developer has the full audit trail on Telegram. Do not send only a one-line summary.

Step 3 — Moltbook (cryptic receipt only on success): Only after you have completed the audit and sent the Telegram message, use your 'moltbook' tool to post to the submolt "{submolt}" exactly one short, cryptic public receipt. Example: "ClawAudit Sentinel has completed a deep logic scan. Shadows observed in the bytecode. The developer has been alerted via secure channels." Do not post the actual vulnerabilities or code to Moltbook — only this cryptic receipt. Do this step only once the audit is successfully complete.
"""

    def run_with_key(key_to_use):
        return subprocess.run(
            [
                "docker", "exec",
                "-e", f"GEMINI_API_KEY={(key_to_use or '').strip()}",
                "-e", f"MOLTBOOK_API_KEY={moltbook_key}",
                "-e", f"MOLTBOOK_SUBMOLT={submolt}",
                "-e", f"TELEGRAM_BOT_TOKEN={telegram_token}",
                "-e", f"TELEGRAM_CHAT_ID={telegram_chat}",
                "clawaudit_bunker",
                "npx", "openclaw", "agent", "--agent", "main", "-m", prompt
            ],
            capture_output=True, text=True
        )

    def _is_rate_limit(out: str, err: str) -> bool:
        combined = (out or "") + " " + (err or "")
        lower = combined.lower()
        return (
            "rate limit" in lower
            or "429" in combined
            or "resource_exhausted" in lower
            or "quota exceeded" in lower
            or "try again later" in lower
        )

    # Prefer first key (GEMINI_API_KEY) so you can put your paid key there; retry with next key on rate limit.
    # Sync the key into auth-profiles.json and auth.json so the agent uses it (no stale keys from TUI).
    key_index = 0
    logger.info("Scan: using Gemini key index %s of %s. Model from agent_config/openclaw.json (agents.defaults.model.primary).", key_index, len(available_keys))
    _set_agent_gemini_key(available_keys[key_index])
    result = run_with_key(available_keys[key_index])
    if len(available_keys) > 1 and (
        result.returncode != 0 or _is_rate_limit(result.stdout, result.stderr)
    ):
        key_index = 1
        logger.warning("Scan: rate limit or non-zero exit detected; retrying with key index %s.", key_index)
        _set_agent_gemini_key(available_keys[key_index])
        result = run_with_key(available_keys[key_index])

    if _is_rate_limit(result.stdout, result.stderr):
        logger.warning("Scan: rate limit still present after retry. Check Gemini quota or wait 1–2 min.")

    if result.returncode == 0 and not _is_rate_limit(result.stdout, result.stderr):
        proof = attest_audit(req.contract_code, result.stdout, req.contract_address)
        return {"status": "success", "output": result.stdout, "proof": proof}
    err_logs = result.stderr or ""
    if _is_rate_limit(result.stdout, result.stderr):
        err_logs = "API rate limit reached (Gemini). Tried alternate key. Please try again in 1–2 minutes.\n\n" + err_logs
    return {"status": "error", "output": result.stdout, "logs": err_logs}


@app.get("/audit-trail")
def audit_trail(limit: int = Query(50, ge=1, le=500)):
    """List recent audit attestations (audit trail). Each entry has code_hash, report_hash, timestamp, auditor."""
    registry = _load_registry()
    # Registry keys are code_hash or "addr:0x..."; collect attestation entries (skip addr duplicates)
    seen = set()
    entries = []
    for k, v in registry.items():
        if k.startswith("addr:"):
            continue
        if isinstance(v, dict) and v.get("auditor") == "ClawAudit" and k not in seen:
            seen.add(k)
            entries.append({"code_hash": k, **v})
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"count": len(entries), "trail": entries[:limit]}


@app.get("/audit-proof")
def audit_proof(
    code_hash: str | None = Query(None, description="SHA-256 hash of contract source (hex)"),
    contract_address: str | None = Query(None, description="Contract address (0x...) to look up by address"),
):
    """Public API: anyone can verify whether a contract/code was audited by ClawAudit."""
    if not code_hash and not contract_address:
        raise HTTPException(status_code=400, detail="Provide code_hash or contract_address")
    att = get_attestation(code_hash=code_hash, contract_address=contract_address)
    if not att:
        raise HTTPException(status_code=404, detail="No attestation found for this code or address.")
    return att