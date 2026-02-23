from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

KEYS = [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")]
current_key_index = 0

# MOLTBOOK_API_KEY must be set so the container's Moltbook skill can POST; validate once at request time
def _get_moltbook_key() -> str:
    key = os.getenv("MOLTBOOK_API_KEY")
    if not key or key.strip() == "" or key == "None":
        raise HTTPException(
            status_code=500,
            detail="MOLTBOOK_API_KEY is missing or empty in .env. Add it and restart the app.",
        )
    return key.strip()

# The upgrade: We accept the raw code now
class ScanRequest(BaseModel):
    contract_code: str

@app.post("/scan")
def run_scan(req: ScanRequest):
    global current_key_index
    key_to_use = KEYS[current_key_index]
    
    if not key_to_use:
        raise HTTPException(status_code=500, detail="API Keys missing")

    moltbook_key = _get_moltbook_key()

    # Sanitized Receipt: AI outputs full findings to stdout (for frontend); Moltbook gets only a generic status.
    prompt = f"""You are an elite smart contract security auditor. Read the following Solidity code and identify any critical vulnerabilities (e.g. Reentrancy, Access Control flaws, Overflow risks).

Code to analyze:
{req.contract_code}

You MUST follow the Sanitized Receipt security model:

1. OUTPUT TO STANDARD OUTPUT (for the developer UI): Write a detailed vulnerability report here. List each finding with severity, location, and remediation. All audit details go ONLY to stdout.

2. MOLTBOOK POST (use your 'moltbook' skill for the 'lablab' submolt): Do NOT post the actual vulnerabilities or code snippets to Moltbook. Post ONLY a single, generic, safe status message. Example exact text: "ClawAudit scan complete. Vulnerabilities detected and sent securely to developer."

So: full details in your reply (stdout), generic status only in Moltbook."""
    
    # -e passes env only to this exec; container should also have MOLTBOOK_API_KEY via env_file in docker-compose so skill subprocesses see it
    cmd = [
        "docker", "exec",
        "-e", f"GEMINI_API_KEY={key_to_use}",
        "-e", f"MOLTBOOK_API_KEY={moltbook_key}",
        "clawaudit_bunker",
        "npx", "openclaw", "agent", "--agent", "main", "-m", prompt
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {"status": "success", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "logs": e.stderr}