# OpenClaw agent memory (local)

## Does `memory.md` / `MEMORY.md` exist?

**Yes, it can exist** — but OpenClaw does **not** create it by default. Memory is stored as plain Markdown in the agent’s **workspace**. In this project:

- **Workspace (in container):** `~/.openclaw/workspace` → on the host that is **`agent_config/workspace`** (mounted from `docker-compose`).
- **Long-term memory file:** `MEMORY.md` (optional) in that workspace → **`agent_config/workspace/MEMORY.md`**.
- **Daily logs:** `memory/YYYY-MM-DD.md` in the same workspace → **`agent_config/workspace/memory/2026-02-24.md`** etc.

So the agent’s “local memory” **does exist** as a concept: it’s these Markdown files. If `MEMORY.md` or `memory/*.md` are not present yet, it’s because nothing has been written to them (see below).

## Why you might not see `MEMORY.md`

1. **One-off scans** — When you run a scan from the FastAPI/Streamlit UI or the GitHub webhook, we start the agent with a single prompt (`npx openclaw agent -m "..."`). The agent completes the audit and exits. It often doesn’t run a “memory flush” or get asked to “remember this,” so it may never write to `MEMORY.md` or `memory/`.
2. **Memory is optional** — OpenClaw only writes to `MEMORY.md` when:
   - You (or the prompt) ask the agent to remember something, or
   - The session hits compaction and the automatic memory flush runs (reminder to write durable notes).
3. **Workspace must be writable** — The container needs write access to `agent_config/workspace` (or wherever the workspace is). Our mount `./agent_config:/home/node/.openclaw` makes `agent_config/workspace` writable inside the container.

## Where to look on your machine

| What            | Path on host (this repo)        |
|-----------------|----------------------------------|
| Long-term memory| `agent_config/workspace/MEMORY.md` |
| Daily logs      | `agent_config/workspace/memory/YYYY-MM-DD.md` |
| Workspace root  | `agent_config/workspace/`        |

If `MEMORY.md` is missing, create it (or let the agent create it on first write). You can add a line or two of Markdown; the agent will read it and can append when it stores new facts.

## How to get the agent to use memory

- **TUI / interactive:** In a normal OpenClaw TUI session you can say things like “remember that we use Moltbook for cryptic receipts” or “remember my preferred severity levels.” The agent can then write to `MEMORY.md` or `memory/YYYY-MM-DD.md` via its memory tools.
- **Scans:** Our scan prompts don’t currently ask the agent to read or update memory. If you want scan-related facts to persist (e.g. “prefer reentrancy checks”), you could add a line to the prompt like: “If you have a durable preference from this run, write it to MEMORY.md,” and ensure the workspace is writable.
- **Automatic flush:** If the session gets long enough and compaction is enabled, OpenClaw will prompt the agent to write durable notes before compacting; that can create or update `MEMORY.md` and `memory/YYYY-MM-DD.md`.

## Summary

- **Local memory exists** as Markdown under the agent workspace (`agent_config/workspace/`).
- **`MEMORY.md`** is the long-term file; **`memory/YYYY-MM-DD.md`** are daily logs.
- They may be **absent** until the agent (or you) writes to them. You can create **`agent_config/workspace/MEMORY.md`** yourself so the file exists and the agent can read/update it.
