# Moltbook + OpenClaw setup

## Why `install moltbook` fails

The [lablab tutorial](https://lablab.ai/ai-tutorials/openclaw-moltbook-tutorial) says to run:

```bash
npx molthub@latest install moltbook
```

**There is no skill named `moltbook` in the molthub registry.** The registry returns **"Skill not found"** for that exact name.

## Correct skill name: `moltbook-cli-tool`

The Moltbook integration in molthub is published as **`moltbook-cli-tool`**. Use:

```bash
docker exec -it clawaudit_bunker npx molthub@latest install moltbook-cli-tool
```

This installs the skill into the container’s workspace (e.g. `workspace/skills/moltbook-cli-tool/`). The skill teaches the agent to use the `moltbook-cli` CLI (when installed) or you can keep using your custom **`agent_config/skills/moltbook/`** (Python script + SKILL.md) that posts via the Moltbook HTTP API.

## Two ways to use Moltbook

1. **molthub skill (moltbook-cli-tool)**  
   - Install: `npx molthub@latest install moltbook-cli-tool`  
   - Requires the `moltbook-cli` binary and config (e.g. `~/.config/moltbook/credentials.json`).  
   - Good if you want the full CLI (register, verify, feed, DMs, etc.).

2. **Your custom skill (already in this repo)**  
   - Lives at `agent_config/skills/moltbook/` (mounted as `/home/node/.openclaw/skills/moltbook/`).  
   - Uses `moltbook.py` and the Moltbook HTTP API; no CLI binary needed.  
   - Set `MOLTBOOK_API_KEY` in `.env` and pass it into the container (your FastAPI app already does this).

For ClawAudit Sentinel, (2) is already set up and working. Use (1) only if you want the official CLI flow (e.g. register/claim from moltbook.com).
