# ClawAudit — Local setup steps

Use this file to follow the setup; it is committed so the whole team can use it.

---

## 1. Clone and install

```bash
git clone https://github.com/YOUR_ORG/surge-hackathon.git
cd surge-hackathon
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

---

## 2. Environment (`.env`)

Copy `.env.example` to `.env` and set at least:

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Primary Gemini key for the audit agent |
| `GEMINI_API_KEY_2` | Optional; used if first key hits rate limit |
| `MOLTBOOK_API_KEY` | For posting receipts to Moltbook |
| `MOLTBOOK_SUBMOLT` | Submolt name (e.g. `lablab`) |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Chat ID for full audit trail |

Optional: `GITHUB_TOKEN` (webhook PR comments), `ETHERSCAN_API_KEY` / `BASESCAN_API_KEY` (fetch verified source in UI).

---

## 3. OpenClaw container

```bash
docker compose up -d
```

If you see *"container name clawaudit_bunker already in use"*:

```bash
docker rm -f clawaudit_bunker
docker compose up -d
```

---

## 4. Run API and UI

**Terminal 1 — FastAPI**

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Streamlit**

```bash
streamlit run app.py
```

- API: http://localhost:8000 (docs: http://localhost:8000/docs)
- UI: http://localhost:8501

---

## 5. Optional: TUI (OpenClaw terminal UI)

If you use the TUI, start a **new session** after changing env/config so the agent sees moltbook and telegram:

```bash
openclaw tui --url ws://127.0.0.1:18789 --password YOUR_OPENCLAW_AUTH_SECRET --session main
```

Use the same value as `OPENCLAW_AUTH_SECRET` in docker-compose (default dev: `bunker_secret_123`).

---

## Quick checklist

- [ ] `.env` has GEMINI (x1 or x2), MOLTBOOK, MOLTBOOK_SUBMOLT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
- [ ] `docker compose up -d` (container running)
- [ ] Backend: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- [ ] UI: `streamlit run app.py`

For more detail: **README.md**, **docs/TUI_SETUP.md**, **docs/MOLTBOOK_SETUP.md**, **docs/DEPLOY.md**.
