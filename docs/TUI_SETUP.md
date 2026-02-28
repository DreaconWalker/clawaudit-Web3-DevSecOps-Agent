# OpenClaw TUI + FastAPI/Streamlit flow — what went wrong and how to fix it

## What went wrong (from your terminal)

| Error | Cause | Fix |
|-------|--------|-----|
| **HTTP 400 Anthropic "credit balance too low"** | Default model was set to **Anthropic** (Claude). OpenClaw tried that first. | Default model is now **Google Gemini** in `agent_config/openclaw.json`. |
| **404 "gemini-1.5-flash is not found"** | That model ID is deprecated or wrong for the API version. | Config now uses **gemini-2.0-flash** (valid and stable). |
| **429 Gemini quota exceeded** | Free tier: 5 req/min, 20 req/day. TUI kept retrying. | Wait ~1 hour or use a paid tier; your FastAPI flow already rotates two keys. |
| **"I don't have a 'moltbook' or 'surge' skill"** | Skills **moltbook** and **telegram** were **filtered out** at load time because `requires.env` (MOLTBOOK_API_KEY, TELEGRAM_*) wasn’t set in the container when the session started. | (1) `requires.env` removed so skills always load. (2) Container must get env from `.env` (see below). (3) **Start a new session** in TUI so the skill snapshot refreshes. |
| **"ERROR: Telegram credentials missing" / "MOLTBOOK_API_KEY missing inside Docker"** | When the agent runs `telegram.py` / `moltbook.py` inside the container, those scripts read env vars. The **container** didn’t have them (only the host did). | `docker-compose` now passes **GEMINI_***, **MOLTBOOK_***, **TELEGRAM_*** from `.env` into the container. **Restart the container** after pulling. |

---

## Fixes applied in this repo

1. **`agent_config/openclaw.json`**  
   - Default model set to **`google/gemini-2.0-flash`** (no more Anthropic first, no more gemini-1.5-flash 404).

2. **`docker-compose.yaml`**  
   - Container `environment` now includes:
     - `GEMINI_API_KEY`, `GEMINI_API_KEY_2`
     - `MOLTBOOK_API_KEY`, `MOLTBOOK_SUBMOLT`
     - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`  
   - All read from `.env` so the **TUI** (and any agent run inside the container) sees them.

3. **`agent_config/skills/moltbook/SKILL.md` and `telegram/SKILL.md`**  
   - **`requires.env`** removed so OpenClaw **always** loads these skills.  
   - Scripts still need the env vars at **runtime**; the container now gets them from compose.

---

## Steps to get TUI working (and link it to FastAPI/Streamlit)

Do this **in order**:

### 1. Ensure `.env` has all keys

From the project root, `.env` should contain (no trailing spaces):

```bash
GEMINI_API_KEY=...
GEMINI_API_KEY_2=...
MOLTBOOK_API_KEY=...
MOLTBOOK_SUBMOLT=lablab
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

### 2. Restart the OpenClaw container

So it picks up the new env and config (and skills):

```bash
cd /path/to/surge-hackathon
docker compose down
docker compose up -d
```

**If you get:** `The container name "/clawaudit_bunker" is already in use`  
A leftover container is holding the name. Remove it, then start again:

```bash
docker rm -f clawaudit_bunker
docker compose up -d
```

### 3. Start a **new** session in the TUI

OpenClaw caches the skill list **per session**. Old sessions still see only healthcheck, skill-creator, weather.

- Either create a **new** session (e.g. new session name), or  
- Delete or rename the old session so the next TUI run starts fresh.

Then run the TUI. The gateway requires **authentication** — when you use `--url`, you must pass `--password` (or `--token`), otherwise you get **"gateway disconnected: closed"**.

Use the same secret as in your `docker-compose` (`OPENCLAW_AUTH_SECRET`). Use **only** the flags below (no extra positional arguments):

```bash
cd /path/to/surge-hackathon
openclaw tui --url ws://127.0.0.1:18789 --password bunker_secret_123 --session main
```

Or with npx (no global install):

```bash
npx openclaw@latest tui --url ws://127.0.0.1:18789 --password bunker_secret_123 --session main
```

If you changed `OPENCLAW_AUTH_SECRET` in docker-compose, use that value instead of `bunker_secret_123`.

(If your session name is different, use that. The important part is that the session is **new** after the restart.)

### 4. Check that the agent sees moltbook and telegram

In the TUI, ask: *“List your active skills.”* You should see **moltbook** and **telegram** (and healthcheck, skill-creator, weather). If you don’t, the session is still old — create a new one.

### 5. Rate limits (429)

- **Free tier**: 5 req/min, 20 req/day for gemini-2.0-flash / gemini-2.5-flash. If you hit 429, wait (e.g. 1 hour for daily reset) or switch to a paid Gemini plan.
- Your **FastAPI** app already rotates `GEMINI_API_KEY` and `GEMINI_API_KEY_2`; the **TUI** uses whatever key the gateway/agent has (from env or auth-profiles). For TUI you can’t rotate keys the same way without changing env or config.

---

## How TUI and FastAPI/Streamlit fit together

- **FastAPI + Streamlit (your main flow)**  
  You run a scan from the UI → FastAPI runs:
  ```bash
  docker exec -e GEMINI_API_KEY=... -e MOLTBOOK_API_KEY=... -e TELEGRAM_* ... clawaudit_bunker npx openclaw agent --agent main -m "<prompt>"
  ```
  So each scan is a **one-off** agent run with env vars **injected by FastAPI**. That’s why scans can work even when TUI was broken.

- **TUI**  
  You connect to the **already-running** gateway in the container. The agent runs **inside** the container with the **container’s** environment. So the container must have `GEMINI_*`, `MOLTBOOK_*`, `TELEGRAM_*` from `docker-compose` + `.env`. After the fixes above, a **restart** and a **new session** give the TUI the same env and the same skills (moltbook, telegram) so that:
  - The agent can use the moltbook and telegram skills from the TUI.
  - Your FastAPI-triggered runs and your TUI runs both use the same OpenClaw + Gemini + Moltbook + Telegram flow; the only difference is who injects the prompt (FastAPI vs you in the TUI).

---

## Quick checklist

- [ ] `.env` has all six vars (GEMINI x2, MOLTBOOK, MOLTBOOK_SUBMOLT, TELEGRAM x2).
- [ ] `docker compose down && docker compose up -d` done after pulling the fixes.
- [ ] New TUI session (so the agent sees moltbook + telegram).
- [ ] If you see 429, wait or use a paid Gemini plan.

After that, TUI and your FastAPI/Streamlit flow both use the same ClawAudit (OpenClaw + Gemini + Moltbook + Telegram) setup.

---

## "gateway disconnected: closed" or "gateway disconnected: closed | idle"

The gateway WebSocket requires auth. You **must** pass `--password` (or `--token`) when using `--url`:

```bash
openclaw tui --url ws://127.0.0.1:18789 --password bunker_secret_123 --session main
```

Also confirm the container is running: `docker ps | grep clawaudit_bunker`. If it’s not, run `docker compose up -d`.

---

## Container in "Restarting (1)" / crash loop

If `docker ps` shows `Restarting (1)` for `clawaudit_bunker`, the container is exiting on startup. Check the logs:

```bash
docker logs clawaudit_bunker 2>&1
```

**Common causes and fixes:**

1. **Env vars empty** — Compose reads `.env` only when you run it from the **project directory**. Run from the repo root:
   ```bash
   cd /path/to/surge-hackathon
   docker compose up -d
   ```
   Ensure `.env` exists and has `GEMINI_API_KEY`, `MOLTBOOK_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (no empty values if the app requires them).

2. **Missing or unwritable volumes** — From the repo root, the compose file mounts `./agent_config` and `./agent_workspace`. If either path is missing, create it:
   ```bash
   mkdir -p agent_workspace
   ```

3. **Port 18789 in use** — Another process may be using the port. Change the host port in `docker-compose.yaml` (e.g. `"18790:18789"`) or stop the other process.

4. **Config error** — If the log mentions `openclaw.json` or auth, check `agent_config/openclaw.json` is valid JSON and that the agent’s `agent_config/agents/main/agent/auth-profiles.json` has a valid Google API key if the gateway expects it.

5. **`JSON5: invalid end of input at 43:1`** — The config file was truncated or corrupted (e.g. an incomplete write). Restore `agent_config/openclaw.json` from the repo (it must be valid JSON with all closing `}` and `]`). Then run `docker compose down` and `docker compose up -d` so the container picks up the fixed file.

6. **`models/gemini-1.5-pro is not found` (404)** — The default model was set to one that isn’t available for your API version. This repo uses `google/gemini-2.0-flash` in `agent_config/openclaw.json`. If you see 404, ensure that file has `"primary": "google/gemini-2.0-flash"` (or another [supported model](https://ai.google.dev/gemini-api/docs/models)), then restart the stack.

After fixing, run `docker compose down` then `docker compose up -d` and check `docker ps` again.

---

## Approving Telegram pairing

If you see a message like:

```text
Ask the bot owner to approve with:
openclaw pairing approve telegram W3J5GQEJ
```

**You are the bot owner** (your `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`). Approve from your **host** terminal (same machine where you run the TUI):

```bash
openclaw pairing approve telegram W3J5GQEJ
```

Use the **exact code** from the message (e.g. `W3J5GQEJ`). After that, the Telegram client should pair and the TUI will connect.

If that doesn’t work, the pairing state may live in the container. Try:

```bash
docker exec -it clawaudit_bunker npx openclaw@latest pairing approve telegram W3J5GQEJ
```
