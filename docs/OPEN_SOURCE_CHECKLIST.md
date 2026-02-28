# Open-source release checklist

Use this before making the repo public to avoid leaking secrets.

---

## ✅ Done for you

- **`.env`** — In `.gitignore`; never commit. Use `.env.example` for placeholders.
- **`agent_config/openclaw.json`** — Gateway token replaced with a placeholder; real auth comes from `OPENCLAW_AUTH_SECRET` in `.env`.
- **`agent_config/agents/main/agent/auth-profiles.json`** — Now in `.gitignore`; backend creates it from `.env` on first scan if missing. Any previously committed file had keys replaced with placeholders.
- **`agent_config/agents/main/agent/auth.json`** — In `.gitignore` (runtime auth, may contain keys).
- **Docker** — `OPENCLAW_AUTH_SECRET` uses a default in compose for dev; set in `.env` for production.

---

## Before you publish (run these)

1. **Confirm `.env` is not tracked**
   ```bash
   git status --ignored .env
   # Should show .env as ignored. If it was ever committed, run:
   # git log -p --all -- .env   # and if history shows real keys, rotate those keys and consider removing .env from history (e.g. git filter-repo or BFG).
   ```

2. **Stop tracking auth-profiles.json (if it was committed with real keys before)**  
   So the repo only has a placeholder or no file (backend creates it):
   ```bash
   git rm --cached agent_config/agents/main/agent/auth-profiles.json 2>/dev/null || true
   git rm --cached agent_config/agents/main/agent/auth.json 2>/dev/null || true
   ```

3. **Scan for leftover secrets**
   ```bash
   git grep -i "AIzaSy\|ghp_\|sk_live\|moltbook_sk_\|Bearer [A-Za-z0-9]" -- '*.json' '*.yaml' '*.yml' '*.py' '*.md' ':!.env.example' ':!docs/OPEN_SOURCE_CHECKLIST.md' || true
   ```
   If anything matches, remove or replace with placeholders and rotate the exposed keys.

4. **Commit the safety changes**
   - Placeholder `openclaw.json` and (if still tracked) placeholder `auth-profiles.json`
   - `.gitignore` updates
   - Backend changes that create auth-profiles when missing

---

## After publishing

- New clones: copy `.env.example` to `.env` and set real keys. On first scan, the backend will create `auth-profiles.json` from `GEMINI_API_KEY` in `.env`.
- Tell users to never commit `.env` or real API keys; keep secrets in `.env` only.

---

## Summary

| Item | Status |
|------|--------|
| `.env` in .gitignore | ✅ |
| No hardcoded gateway token in openclaw.json | ✅ |
| auth-profiles.json / auth.json in .gitignore | ✅ |
| Backend creates auth-profiles when missing | ✅ |
| docker-compose secret has safe default | ✅ |
| Run `git rm --cached` for auth files if they were ever committed | ⚠️ You do this once |
| Rotate any keys that were ever committed | ⚠️ If history had them |
