# Where to see audit logs and confirm the model

## Audit trail and logs

| What | Where |
|------|--------|
| **API response (each scan)** | The `/scan` response has `output` (full report text) and on error `logs` (agent stderr). In Streamlit this is shown in the "Report" section and in the error box. |
| **Audit trail (past attestations)** | **GET** `http://127.0.0.1:8000/audit-trail` — returns recent attestations (code_hash, report_hash, timestamp, auditor). Optional query: `?limit=20`. |
| **Attestation registry (raw)** | File: `data/audit_registry.json` in the project root (created after first successful scan). |
| **FastAPI server logs** | The **terminal where you run `uvicorn main:app ...`** — we log which Gemini key index is used and when a rate limit is detected/retried. |
| **Agent/OpenClaw logs** | **Docker:** `docker logs clawaudit_bunker` — shows what runs inside the container (model loading, agent stdout/stderr). Use `docker logs -f clawaudit_bunker` to follow. |

## Config errors (openclaw.json)

- **`JSON5: invalid end of input at 43:1`** — The config file inside the container is truncated or invalid. Ensure `agent_config/openclaw.json` in the repo is complete valid JSON (all braces closed). Restart the stack so the mount is re-read.
- **`models/gemini-1.5-pro is not found` (404)** — The agent fell back to an unsupported model (e.g. after a config parse failure). This repo sets `agents.defaults.model.primary` to `google/gemini-2.0-flash`. Fix the config and restart so the agent uses a [supported model](https://ai.google.dev/gemini-api/docs/models).

## “API rate limit reached”

- **Cause:** Gemini free tier (e.g. 5 req/min, 20 req/day per model). Both keys may share the same project quota.
- **What we do:** We rotate between `GEMINI_API_KEY` and `GEMINI_API_KEY_2` and retry once on rate limit. You’ll see in the **uvicorn terminal**: `Scan: using Gemini key index 0 ...` and, if we retry, `Scan: rate limit or non-zero exit detected; retrying with key index 1`.
- **What you can do:** Wait 1–2 minutes and scan again; or use a paid Gemini plan / separate Google Cloud projects for each key.

## Confirming which model is loaded

- **Config (default model):** `agent_config/openclaw.json` → `agents.defaults.model.primary` (e.g. `google/gemini-2.0-flash`). The agent uses this unless overridden elsewhere.
- **At runtime:** Run `docker logs clawaudit_bunker 2>&1` and look for lines mentioning “model” or “gemini” when a scan runs. OpenClaw may log the resolved model there.
- **Key in use:** The **uvicorn terminal** logs which key index (0 or 1) is used for each scan; the actual key is written to `agent_config/agents/main/agent/auth-profiles.json` before each run so the container uses the same key.

## Quick checks

```bash
# Recent attestations (audit trail)
curl -s "http://127.0.0.1:8000/audit-trail?limit=5"

# Container logs (model and agent output)
docker logs clawaudit_bunker 2>&1 | tail -100

# Default model in config
grep -o '"primary":"[^"]*"' agent_config/openclaw.json
```
