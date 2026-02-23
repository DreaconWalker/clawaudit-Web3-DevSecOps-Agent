from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, constr
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

KEYS = [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")]
current_key_index = 0

# Strict Pydantic validation: Only accepts standard 42-character Web3 addresses
class ScanRequest(BaseModel):
    contract_address: constr(pattern=r'^0x[a-fA-F0-9]{40}$') # type: ignore

@app.post("/scan")
def run_scan(req: ScanRequest):
    global current_key_index
    key_to_use = KEYS[current_key_index]
    
    if not key_to_use:
        raise HTTPException(status_code=500, detail="API Keys missing")

    prompt = f"Scan SURGE contract {req.contract_address} for vulnerabilities. If you find any, use your moltbook skill to post an alert."
    
    # Secure subprocess execution (no shell=True)
    cmd = [
        "docker", "exec",
        "-e", f"GEMINI_API_KEY={key_to_use}",
        "clawaudit_bunker",
        "npx", "openclaw", "agent", "--agent", "main", "-m", prompt
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {"status": "success", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        # Auto-rotator logic could go here if the error was a rate limit
        return {"status": "error", "logs": e.stderr}