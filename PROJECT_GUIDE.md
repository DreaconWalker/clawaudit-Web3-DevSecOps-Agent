# ClawAudit project guide: making sense of the repo and OpenClaw’s role

This doc explains how the project is structured and **what OpenClaw does** inside it.

---

## What is ClawAudit?

**ClawAudit** is an autonomous Web3 DevSecOps layer that:

1. **Audits** Solidity (and similar) code using an AI agent.
2. **Attests** audits so anyone can verify “this code was audited” (by code hash or contract address).
3. **Integrates with GitHub**: when a PR is opened or updated, it audits the diff, posts the result as a comment, and can open a **remediation PR** with a suggested fix.
4. Optionally **notifies** developers via Telegram (full report) and **Moltbook** (short receipt).

The “brain” of the audit is **OpenClaw** — an agent that runs in Docker and uses **Gemini** to analyze code and produce reports (and patched code when it finds issues).

---

## How to make sense of the project (top-level)

| Layer | What it is | Where it lives |
|-------|------------|-----------------|
| **API** | FastAPI backend: scans, attestation, GitHub webhook, remediation PRs | `main.py` |
| **UI** | Streamlit app: Live Scanner, GitHub (creds + PR), Enterprise (API overview) | `app.py` |
| **Agent** | OpenClaw in Docker: runs the actual audit from a prompt, can use Telegram/Moltbook skills | `agent_config/`, `docker-compose.yaml` |
| **Data** | Attestation registry (code_hash → proof) | `data/audit_registry.json` (created at runtime) |
| **Docs** | Setup, testing, memory, this guide | `README.md`, `TESTING_GITHUB.md`, `OPENCLAW_MEMORY.md`, `PROJECT_GUIDE.md` |

**Rough flow:** User or GitHub sends input → **main.py** receives it → **main.py** builds a prompt and runs **OpenClaw** in Docker → OpenClaw (Gemini) returns a report (and sometimes a “## Patched code” block) → **main.py** stores attestation, posts comments/PRs, returns JSON.

---

## What OpenClaw does in this project

**OpenClaw** is the AI agent that performs the security analysis. In this repo it is **not** a standalone app you run in a TUI; it is **invoked by the FastAPI backend** as a subprocess.

### How we call OpenClaw

- **main.py** runs:
  ```bash
  docker exec -e GEMINI_API_KEY=... -e MOLTBOOK_API_KEY=... ... clawaudit_bunker npx openclaw agent --agent main -m "<prompt>"
  ```
- So every **scan** (from the UI or from the GitHub webhook) is: “run the OpenClaw agent once with this prompt; capture stdout/stderr.”
- The **prompt** tells the agent to:
  - Act as a Web3 security auditor.
  - Analyze the given Solidity (or diff).
  - Output a **report** (findings, severity, exploit scenario).
  - Optionally include a **## Patched code** block with corrected Solidity.
  - For manual/demo/full scans: also use **Telegram** (full report) and **Moltbook** (cryptic receipt) skills.

### Where OpenClaw’s config lives

- **Agent and model:** `agent_config/openclaw.json` (e.g. `google/gemini-2.5-flash`).
- **Skills:** `agent_config/skills/` (e.g. `telegram`, `moltbook`) — enabled in config so the agent can post to Telegram and Moltbook when the prompt asks for it.
- **Workspace:** `agent_config/workspace/` is mounted as the agent’s workspace (e.g. for memory; see `OPENCLAW_MEMORY.md`).

So in one sentence: **OpenClaw is the audit engine; this project is the orchestration layer (API, UI, attestation, GitHub, remediation PRs) around it.**

---

## Flows in one place

1. **Live scan (UI or POST /scan)**  
   User (or client) sends Solidity → backend runs OpenClaw with that code in the prompt → agent returns report (+ optional Patched code) → backend saves attestation, returns report and proof. Agent may also post to Telegram and Moltbook per prompt.

2. **GitHub webhook (autonomous)**  
   PR opened/synced → GitHub hits `POST /webhook/github` → backend gets PR diff via GitHub API → runs OpenClaw on the diff → posts report as PR comment → if report has “## Patched code” and PR has exactly one `.sol` file, backend creates a **remediation PR** (new branch, patch that file, open PR) and posts a second comment with the link.

3. **Manual “Create remediation PR” (UI)**  
   User enters repo, file path, vulnerability title, and **pastes** the patched code → `POST /remediation/create-pr` → backend creates branch and PR via GitHub API only (no scan in this flow).

4. **Attestation**  
   After a scan, proofs are stored in `data/audit_registry.json`. Anyone can call `GET /audit-proof?code_hash=...` or `?contract_address=...` to verify an audit.

---

## Quick “where do I look?”

- **Change API or webhook logic:** `main.py`
- **Change UI (tabs, forms, copy):** `app.py`
- **Change model or agent behavior:** `agent_config/openclaw.json` and prompts in `main.py`
- **Change Telegram/Moltbook behavior:** `agent_config/skills/telegram`, `agent_config/skills/moltbook`, and the scan/webhook prompts in `main.py`
- **Understand agent memory:** `OPENCLAW_MEMORY.md` and `agent_config/workspace/MEMORY.md`
- **Test GitHub webhook + remediation PR:** `TESTING_GITHUB.md`

---

## Summary

- **ClawAudit** = API + UI + attestation + GitHub integration + remediation PRs.
- **OpenClaw** = the AI agent (in Docker) that actually audits code and returns reports (and patched code); it is invoked by the backend and configured under `agent_config/`.
- To “make sense” of the project: follow a request from **app.py** or **GitHub** → **main.py** → **OpenClaw** → back to **main.py** (attestation, comments, PRs), then to the user or GitHub.
