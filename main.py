from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel
import subprocess
import os
import re
import json
import hashlib
import logging
import uuid
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from github import Github

# Load .env from project root (same dir as main.py) so Telegram/Moltbook env are set regardless of cwd
load_dotenv(Path(__file__).resolve().parent / ".env")

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


def _post_to_moltbook(title: str, content: str, submolt: str | None = None) -> bool:
    """Post a message to the configured Moltbook submolt. Returns True on success."""
    key = (os.getenv("MOLTBOOK_API_KEY") or "").strip()
    if not key:
        return False
    submolt = (submolt or os.getenv("MOLTBOOK_SUBMOLT") or "lablab").strip()
    payload = {"submolt_name": submolt, "title": title, "content": content}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://www.moltbook.com/api/v1/posts",
        data=data,
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return True
    except Exception as e:
        logger.warning("Moltbook post failed: %s", e)
        return False


def _run_openclaw_agent(
    prompt: str,
    gemini_key: str,
    *,
    require_moltbook: bool = True,
    telegram_token: str | None = None,
    telegram_chat: str | None = None,
    moltbook_key: str | None = None,
    submolt: str | None = None,
) -> subprocess.CompletedProcess:
    """Run the OpenClaw agent in the container. Env from args or os.environ."""
    _telegram_token = (telegram_token or "").strip() or (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    _telegram_chat = (telegram_chat or "").strip() or (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if require_moltbook:
        _moltbook_key = (moltbook_key or "").strip() or (os.getenv("MOLTBOOK_API_KEY") or "").strip()
        if not _moltbook_key:
            _get_moltbook_key()  # raise
    else:
        _moltbook_key = (moltbook_key or "").strip() or (os.getenv("MOLTBOOK_API_KEY") or "").strip()
    _submolt = (submolt or "").strip() or (os.getenv("MOLTBOOK_SUBMOLT") or "lablab").strip()
    return subprocess.run(
        [
            "docker",
            "exec",
            "-e", f"GEMINI_API_KEY={(gemini_key or '').strip()}",
            "-e", f"MOLTBOOK_API_KEY={_moltbook_key}",
            "-e", f"MOLTBOOK_SUBMOLT={_submolt}",
            "-e", f"TELEGRAM_BOT_TOKEN={_telegram_token}",
            "-e", f"TELEGRAM_CHAT_ID={_telegram_chat}",
            "clawaudit_bunker",
            "npx", "openclaw", "agent", "--agent", "main", "-m", prompt,
        ],
        capture_output=True,
        text=True,
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


class ScanRequest(BaseModel):
    contract_code: str
    contract_address: str | None = None  # optional; if set, attestation is also queryable by address
    scan_type: str | None = None  # optional: "manual" | "demo" | "full" — agent posts scan-type-specific Moltbook receipt
    # Optional overrides for testing from UI; if not set, backend uses TELEGRAM_* and MOLTBOOK_* env vars
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    moltbook_api_key: str | None = None
    moltbook_submolt: str | None = None

def _get_telegram_env() -> tuple[str, str]:
    """Return (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID); raise if either is missing (needed for agent to post)."""
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat:
        raise HTTPException(
            status_code=500,
            detail="TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env so the agent can send the audit trail to Telegram. Check .env and restart the backend.",
        )
    return token, chat


@app.post("/scan")
def run_scan(req: ScanRequest):
    available_keys = [str(k).strip() for k in KEYS if k and str(k).strip()]
    if not available_keys:
        raise HTTPException(status_code=500, detail="API Keys missing: set GEMINI_API_KEY and/or GEMINI_API_KEY_2 in .env")

    # Use request overrides for testing from UI, else env
    telegram_token = (req.telegram_bot_token or "").strip() or (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    telegram_chat = (req.telegram_chat_id or "").strip() or (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    moltbook_key = (req.moltbook_api_key or "").strip() or (os.getenv("MOLTBOOK_API_KEY") or "").strip()
    submolt = (req.moltbook_submolt or "").strip() or (os.getenv("MOLTBOOK_SUBMOLT") or "lablab").strip()
    if not telegram_token or not telegram_chat:
        try:
            telegram_token, telegram_chat = _get_telegram_env()
        except HTTPException:
            raise
    if not moltbook_key:
        moltbook_key = _get_moltbook_key()
    logger.info("Scan: Moltbook and Telegram env present; submolt=%s", submolt)

    scan_type_hint = (req.scan_type or "manual").strip().lower()
    if scan_type_hint not in ("manual", "demo", "full"):
        scan_type_hint = "manual"
    moltbook_instruction = (
        f'Only after you have completed the audit and sent the Telegram message, use your \'moltbook\' tool to post to the submolt "{submolt}" exactly one short, cryptic public receipt. '
        f'Identify this as a **{scan_type_hint}** security scan in your receipt (e.g. "ClawAudit Sentinel has completed a {scan_type_hint} security scan. ..."). '
        'Do not post the actual vulnerabilities or code to Moltbook — only this cryptic receipt. Do this step only once the audit is successfully complete.'
    )
    prompt = f"""You are an elite Web3 security auditor. Analyze this Solidity code and complete the following steps in order.

Code to analyze:
{req.contract_code}

Step 1 — Console output (for the user's dashboard): Write a full vulnerability report to the console. Include: CRITICAL FINDINGS (type and location), EXPLOIT SCENARIO (how an attacker would exploit it in one sentence), and PATCHED CODE (corrected Solidity). All of this must appear in your reply so it is shown on the page.

Step 2 — Telegram (full audit trail to developer): Use your 'telegram' tool to send the **full audit trail** to the developer channel. The message must include: the complete vulnerability report — vulnerability name(s), severity, locations, exploit scenario, and remediation (patched code or clear fix steps). Send the same level of detail as the console report so the developer has the full audit trail on Telegram. Do not send only a one-line summary.

Step 3 — Moltbook (cryptic receipt only on success): {moltbook_instruction}
"""

    # Prefer first key (GEMINI_API_KEY) so you can put your paid key there; retry with next key on rate limit.
    # Sync the key into auth-profiles.json and auth.json so the agent uses it (no stale keys from TUI).
    key_index = 0
    logger.info("Scan: using Gemini key index %s of %s. Model from agent_config/openclaw.json (agents.defaults.model.primary).", key_index, len(available_keys))
    _set_agent_gemini_key(available_keys[key_index])
    result = _run_openclaw_agent(
        prompt, available_keys[key_index], require_moltbook=True,
        telegram_token=telegram_token, telegram_chat=telegram_chat,
        moltbook_key=moltbook_key, submolt=submolt,
    )
    if len(available_keys) > 1 and (
        result.returncode != 0 or _is_rate_limit(result.stdout, result.stderr)
    ):
        key_index = 1
        logger.warning("Scan: rate limit or non-zero exit detected; retrying with key index %s.", key_index)
        _set_agent_gemini_key(available_keys[key_index])
        result = _run_openclaw_agent(
            prompt, available_keys[key_index], require_moltbook=True,
            telegram_token=telegram_token, telegram_chat=telegram_chat,
            moltbook_key=moltbook_key, submolt=submolt,
        )

    if _is_rate_limit(result.stdout, result.stderr):
        logger.warning("Scan: rate limit still present after retry. Check Gemini quota or wait 1–2 min.")

    if result.returncode == 0 and not _is_rate_limit(result.stdout, result.stderr):
        proof = attest_audit(req.contract_code, result.stdout, req.contract_address)
        # Include agent stderr so user can see if Telegram/Moltbook tools failed (e.g. credentials missing in container)
        agent_stderr = (result.stderr or "").strip()
        if agent_stderr and ("Telegram" in agent_stderr or "MOLTBOOK" in agent_stderr or "ERROR" in agent_stderr):
            logger.warning("Scan succeeded but agent stderr may indicate tool issues: %s", agent_stderr[:200])
        return {
            "status": "success",
            "output": result.stdout,
            "proof": proof,
            "agent_stderr": agent_stderr[-2000:] if agent_stderr else None,
        }
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


# --- Moltbook: dev updates (hackathon submolt requirement) ---
class MoltbookPostRequest(BaseModel):
    title: str | None = None  # default "ClawAudit Dev Update"
    content: str


class RemediationPRRequest(BaseModel):
    repo_name: str  # e.g. "owner/repo"
    file_path: str  # path to the vulnerable file in the repo
    patched_code: str  # fixed code from OpenClaw agent
    vulnerability_title: str
    token: str | None = None  # optional; if omitted, uses GITHUB_TOKEN from env


@app.post("/remediation/create-pr")
def api_create_remediation_pr(req: RemediationPRRequest):
    """Create a ClawAudit auto-remediation PR from Streamlit (or any client). Uses GitHub API only."""
    result = create_clawaudit_remediation_pr(
        repo_name=req.repo_name,
        file_path=req.file_path,
        patched_code=req.patched_code,
        vulnerability_title=req.vulnerability_title,
        token=req.token,
    )
    if result is None:
        raise HTTPException(status_code=400, detail="Failed to create PR (check GITHUB_TOKEN, repo access, and file path).")
    return result


@app.post("/moltbook/post")
def moltbook_post(req: MoltbookPostRequest):
    """
    Post a development update to the configured Moltbook submolt.
    Use this for hackathon milestones (e.g. "Week 1: API live", "GitHub integration complete").
    """
    try:
        _get_moltbook_key()
    except HTTPException:
        raise
    title = (req.title or "ClawAudit Dev Update").strip() or "ClawAudit Dev Update"
    if not (req.content and req.content.strip()):
        raise HTTPException(status_code=400, detail="content is required")
    ok = _post_to_moltbook(title, req.content.strip())
    if not ok:
        raise HTTPException(status_code=502, detail="Moltbook post failed")
    return {"status": "ok", "message": "Posted to submolt"}


def _extract_patched_solidity(report: str) -> str | None:
    """Extract the first full Solidity code block from ## Patched code section or any ```solidity block."""
    if not report or not report.strip():
        return None
    # Prefer block under "## Patched code" or "## Remediation"
    for section in ("## Patched code", "## Remediation", "### Patched code"):
        idx = report.find(section)
        if idx >= 0:
            rest = report[idx:]
            m = re.search(r"```(?:solidity)?\s*\n(.*?)```", rest, re.DOTALL)
            if m:
                return m.group(1).strip()
    # Fallback: first ```solidity ... ``` or ``` ... ``` that looks like Solidity
    m = re.search(r"```solidity\s*\n(.*?)```", report, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*\n(.*?)```", report, re.DOTALL)
    if m:
        block = m.group(1).strip()
        if "pragma solidity" in block or "contract " in block:
            return block
    return None


def _create_remediation_pr(repo, pr, patched_code: str, sol_filename: str, audit_comment_url: str) -> dict | None:
    """Create a branch with the patched file and open a PR. Returns new PR info or None on failure."""
    pr_number = pr.number
    branch_name = f"clawaudit-fix-pr-{pr_number}"
    try:
        head_sha = pr.head.sha
        base_ref = pr.base.ref
        # Create branch from PR head
        try:
            repo.create_ref(f"refs/heads/{branch_name}", head_sha)
        except Exception as e:
            if "already exists" in str(e).lower() or "Reference already exists" in str(e):
                # Branch exists from previous run; skip or update? For simplicity, skip.
                logger.info("Remediation branch %s already exists, skipping PR creation", branch_name)
                return None
            raise
        # Get current file content and sha on the new branch
        try:
            file_content = repo.get_contents(sol_filename, ref=branch_name)
            file_sha = file_content.sha
        except Exception as e:
            logger.warning("Could not get file %s on branch %s: %s", sol_filename, branch_name, e)
            try:
                repo.get_git_ref(f"heads/{branch_name}").delete()
            except Exception:
                pass
            return None
        # Update file with patched code
        repo.update_file(sol_filename, "ClawAudit: apply suggested patch for vulnerabilities", patched_code, file_sha, branch=branch_name)
        # Create PR
        new_pr = repo.create_pull(
            title="ClawAudit: suggested fix for vulnerabilities",
            body=f"Automated remediation from the [audit comment]({audit_comment_url}) on the original PR. Please review the changes and merge if appropriate.",
            head=branch_name,
            base=base_ref,
        )
        logger.info("Created remediation PR #%s for %s", new_pr.number, repo.full_name)
        return {"number": new_pr.number, "url": new_pr.html_url, "branch": branch_name}
    except Exception as e:
        logger.exception("Failed to create remediation PR: %s", e)
        return None


def create_clawaudit_remediation_pr(
    repo_name: str,
    file_path: str,
    patched_code: str,
    vulnerability_title: str,
    *,
    token: str | None = None,
) -> dict | None:
    """
    Autonomously create a Pull Request with patched code using the GitHub API only (no local git).

    Uses GITHUB_TOKEN from environment unless token is passed. Returns PR info dict or None on failure.
    """
    auth_token = (token or os.getenv("GITHUB_TOKEN") or "").strip()
    if not auth_token:
        logger.error("create_clawaudit_remediation_pr: GITHUB_TOKEN not set")
        return None

    try:
        g = Github(auth_token)
        repo = g.get_repo(repo_name)

        default_branch = repo.default_branch
        default_branch_ref = repo.get_branch(default_branch)
        latest_commit_sha = default_branch_ref.commit.sha

        branch_name = f"clawaudit-patch-{uuid.uuid4().hex}"

        repo.create_ref(f"refs/heads/{branch_name}", latest_commit_sha)

        file_content = repo.get_contents(file_path, ref=default_branch)
        file_sha = file_content.sha

        repo.update_file(
            file_path,
            "ClawAudit: Auto-Remediation Patch",
            patched_code,
            file_sha,
            branch=branch_name,
        )

        new_pr = repo.create_pull(
            title=f"🚨 ClawAudit Auto-Remediation: {vulnerability_title}",
            body="This PR was autonomously generated by the ClawAudit Sentinel agent to patch a detected smart contract vulnerability.",
            head=branch_name,
            base=default_branch,
        )

        logger.info("Created ClawAudit remediation PR #%s for %s", new_pr.number, repo.full_name)
        return {"number": new_pr.number, "url": new_pr.html_url, "branch": branch_name}
    except Exception as e:
        logger.exception("create_clawaudit_remediation_pr failed: %s", e)
        return None


# --- GitHub Webhook: PR audit and post comment ---
@app.post("/webhook/github")
async def github_webhook(request: Request):
    """
    Accept GitHub Webhook payloads for Pull Requests. On PR opened/synchronize,
    audit the code diff with the OpenClaw agent and post the result as a PR comment.
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("GitHub webhook: invalid JSON body: %s", e)
        return {"status": "ignored", "reason": "invalid payload"}

    event = request.headers.get("X-GitHub-Event", "")
    if event != "pull_request":
        return {"status": "ignored", "reason": f"event {event!r} not handled"}

    action = body.get("action")
    if action not in ("opened", "synchronize"):
        return {"status": "ignored", "reason": f"action {action!r} not handled"}

    repo_full_name = (body.get("repository") or {}).get("full_name")
    pr_payload = body.get("pull_request") or {}
    pr_number = pr_payload.get("number")
    if not repo_full_name or pr_number is None:
        logger.warning("GitHub webhook: missing repository.full_name or pull_request.number")
        return {"status": "error", "reason": "missing repo or PR number"}

    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        logger.error("GitHub webhook: GITHUB_TOKEN not set")
        return {"status": "error", "reason": "GITHUB_TOKEN not configured"}

    try:
        gh = Github(token)
        repo = gh.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        files = pr.get_files()
        diff_parts = []
        for f in files:
            if getattr(f, "patch", None):
                diff_parts.append(f"### {f.filename}\n```diff\n{f.patch}\n```")
        diff_text = "\n\n".join(diff_parts) if diff_parts else "(no patch content)"
    except Exception as e:
        logger.exception("GitHub webhook: failed to fetch PR or diff: %s", e)
        return {"status": "error", "reason": str(e)}

    prompt = f"""You are an elite Web3 security auditor. Review the following code diff from a GitHub Pull Request and write a concise vulnerability report suitable as a **single GitHub PR comment** in Markdown.

Do NOT use Telegram or Moltbook. Output ONLY the comment body: use clear sections (e.g. ## Summary, ## Findings, ## Recommendations), bullet points, and code blocks where helpful. Keep it focused and actionable.

**Important:** If you find vulnerabilities and can suggest a fix, add a section **## Patched code** with exactly one Solidity code block containing the full corrected file (so a developer can apply it). Use this format:
## Patched code
```solidity
// full corrected Solidity code here
```

Code diff to audit:

{diff_text}
"""

    available_keys = [str(k).strip() for k in KEYS if k and str(k).strip()]
    if not available_keys:
        logger.error("GitHub webhook: no Gemini API keys configured")
        return {"status": "error", "reason": "no Gemini API keys"}

    _set_agent_gemini_key(available_keys[0])
    result = _run_openclaw_agent(prompt, available_keys[0], require_moltbook=False)

    comment_body = (result.stdout or "").strip() or (result.stderr or "No output from auditor.")
    if not comment_body:
        comment_body = "ClawAudit could not produce a report for this diff."

    try:
        pr.create_issue_comment(comment_body)
        logger.info("GitHub webhook: posted comment on %s PR #%s", repo_full_name, pr_number)
    except Exception as e:
        logger.exception("GitHub webhook: failed to post comment: %s", e)
        return {"status": "error", "reason": str(e)}

    # If vulnerabilities were found and the report includes patched code, create a remediation PR
    audit_pr_url = f"{repo.html_url}/pull/{pr_number}"
    remediation = None
    patched_code = _extract_patched_solidity(result.stdout or "")
    sol_files = [f.filename for f in files if f.filename.endswith(".sol")]
    if patched_code and len(sol_files) == 1:
        sol_filename = sol_files[0]
        remediation = _create_remediation_pr(repo, pr, patched_code, sol_filename, audit_pr_url)
        if remediation:
            # Add a follow-up comment linking to the remediation PR
            try:
                pr.create_issue_comment(
                    f"🔧 **ClawAudit** created a suggested fix: [PR #{remediation['number']}]({remediation['url']}). "
                    f"Review and merge if the patch looks good."
                )
            except Exception as e:
                logger.warning("Could not post remediation link comment: %s", e)
    elif patched_code and len(sol_files) != 1:
        logger.info("Skipping auto remediation PR: %s .sol files (need exactly 1)", len(sol_files))
    elif not patched_code:
        logger.info("No patched code block in report; skipping remediation PR")

    # Post scan-type-specific update to Moltbook (PR review completed)
    _post_to_moltbook(
        "ClawAudit PR Review",
        f"PR security review completed for {repo_full_name} PR #{pr_number}. Findings posted on the PR."
        + (f" Remediation PR: #{remediation['number']}." if remediation else ""),
    )
    return {"status": "ok", "repo": repo_full_name, "pr": pr_number, "remediation_pr": remediation}