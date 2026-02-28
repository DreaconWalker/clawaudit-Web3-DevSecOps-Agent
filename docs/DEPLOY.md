# Deploying ClawAudit (open-source project)

This guide covers **where** and **how** to deploy ClawAudit so it runs outside localhost (e.g. for open-source demos, hackathons, or production).

---

## What you need to run

- **Backend:** FastAPI (`main.py`) — needs Docker (for the OpenClaw agent), env vars (Gemini, optional Telegram/Moltbook/GitHub).
- **UI:** Streamlit (`app.py`) — talks to the backend via `CLAWAUDIT_API_BASE`.
- **Agent:** OpenClaw in a container (`docker compose`); backend runs `docker exec ... clawaudit_bunker ...` to perform scans.

So you need a host that can run **Docker** and **Python** (or containerize the API + UI).

---

## Where to deploy

### 1. **Railway** (good for quick public demos)

- **Why:** Simple deploy from GitHub, supports Docker and env vars, public URL for API and (if you add a Streamlit service) UI.
- **Steps:**
  1. Connect your GitHub repo to [Railway](https://railway.app).
  2. Add a **service** that runs the backend: use a **Dockerfile** (see below) that starts the OpenClaw container and then `uvicorn main:app --host 0.0.0.0 --port 8000`, or use two services (one for Docker Compose / agent, one for uvicorn).
  3. Set env vars in Railway: `GEMINI_API_KEY`, optionally `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `MOLTBOOK_API_KEY`, `GITHUB_TOKEN`.
  4. Expose the API (e.g. port 8000) and copy the public URL (e.g. `https://your-app.up.railway.app`).
  5. For the Streamlit UI you can add a second service (Dockerfile that runs `streamlit run app.py`) and set `CLAWAUDIT_API_BASE` to the backend URL.
- **Caveat:** Railway’s free tier has limits; Docker-in-Docker or running both API and agent on the same machine may need a single Dockerfile that starts the agent container then the API (see “Single Dockerfile” below).

### 2. **Render**

- **Why:** Free tier, Docker support, GitHub integration.
- **Steps:** Create a **Web Service**, connect repo, use a Dockerfile that builds and runs the backend (and optionally the UI). Set env vars in the Render dashboard. For the agent, you typically need a Dockerfile that either (a) runs `docker compose up` and then uvicorn (if Render supports Docker Compose), or (b) runs the OpenClaw image and the API in one Dockerfile (multi-stage or sidecar). Render’s free tier can sleep; use a paid tier for always-on.

### 3. **Fly.io**

- **Why:** Runs full VMs, so you can install Docker and run `docker compose` + uvicorn + streamlit as on a VPS.
- **Steps:** Install [flyctl](https://fly.io/docs/hands-on/install-flyctl/), create an app, use a `Dockerfile` or `fly.toml` that runs your stack. You can run the agent container and the API in the same machine; expose the API port and set `CLAWAUDIT_API_BASE` for the UI.

### 4. **VPS (DigitalOcean, Hetzner, AWS EC2, etc.)**

- **Why:** Full control; same setup as local (Docker Compose + two terminals).
- **Steps:**
  1. Create a droplet/instance (e.g. Ubuntu).
  2. Install Docker and Docker Compose, clone the repo, copy `.env.example` to `.env` and set secrets.
  3. Run `docker compose up -d` (OpenClaw agent).
  4. Run `uvicorn main:app --host 0.0.0.0 --port 8000` (in a screen/tmux or as a systemd service).
  5. Run `streamlit run app.py --server.port 8501` (optional; or point Streamlit Cloud to your API URL).
  6. Put a reverse proxy (nginx/Caddy) in front and add HTTPS (e.g. Let’s Encrypt). Use the public URL as `CLAWAUDIT_API_BASE` and as the GitHub webhook payload URL.

### 5. **Streamlit Community Cloud** (UI only)

- **Why:** Host only the Streamlit app; backend runs elsewhere.
- **Steps:**
  1. Push the repo to GitHub.
  2. Go to [share.streamlit.io](https://share.streamlit.io), connect the repo, select `app.py` as the main file.
  3. Add **Secrets** (or env vars): `CLAWAUDIT_API_BASE` = your deployed API URL (e.g. `https://your-backend.railway.app`).
  4. Deploy. The UI will call your backend; the backend must be deployed somewhere that runs Docker + FastAPI (Railway, Render, Fly, VPS).

---

## Minimal Dockerfile (backend only)

If your host runs Docker Compose separately, you can run only the FastAPI app:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py ./
COPY agent_config ./agent_config
# data/ is created at runtime. Assumes OpenClaw container is already running on same host (e.g. docker compose up -d).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

This assumes the OpenClaw container is reachable (e.g. same host; backend uses `docker exec` to that container). For cloud PaaS, the “same host” requirement often means you run both the agent and the API in one Dockerfile (e.g. start the agent in the background, then start uvicorn).

---

## Env vars to set in production

| Variable | Required for | Notes |
|----------|----------------|------|
| `GEMINI_API_KEY` | Scan | Google AI (Gemini) key. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Scan (full report to Telegram) | From @BotFather and a group/channel. |
| `MOLTBOOK_API_KEY`, `MOLTBOOK_SUBMOLT` | Scan (Moltbook receipt) | From Moltbook; submolt name (e.g. `lablab`). |
| `GITHUB_TOKEN` | GitHub webhook + remediation PRs | PAT with `repo` scope. |
| `CLAWAUDIT_API_BASE` | Streamlit UI only | Backend URL (e.g. `https://your-api.example.com`). |

---

## GitHub webhook when deployed

1. In your repo: **Settings → Webhooks → Add webhook**.
2. **Payload URL:** `https://YOUR_DEPLOYED_API_URL/webhook/github` (must be HTTPS and reachable from the internet).
3. **Content type:** `application/json`.
4. **Events:** Pull requests.
5. Set `GITHUB_TOKEN` in your deployment env so the backend can comment and create PRs.

---

## Quick checklist for open-source deploy

- [ ] Repo is public (or deployment has access).
- [ ] `.env` is not committed; use platform env vars (Railway/Render/Fly/VPS).
- [ ] Backend runs with Docker (OpenClaw container + uvicorn).
- [ ] `CLAWAUDIT_API_BASE` points to the deployed API URL if you host the UI separately.
- [ ] GitHub webhook URL uses your deployed API base + `/webhook/github`.
- [ ] Optional: add a short **Deploy** badge or link in the README (e.g. “Deploy on Railway”) using the platform’s one-click deploy if available.

For more on the project structure and OpenClaw’s role, see **PROJECT_GUIDE.md**.
