# Contributing to ClawAudit

Thanks for your interest in contributing.

## Development setup

1. **Clone and install**
   ```bash
   git clone https://github.com/YOUR_ORG/surge-hackathon.git
   cd surge-hackathon
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment**  
   Copy `.env.example` to `.env` and set `GEMINI_API_KEY`, `MOLTBOOK_API_KEY`, and Telegram vars. For GitHub webhook, set `GITHUB_TOKEN`.

3. **Run services**
   - Start the agent: `docker compose up -d`
   - Start API: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
   - Start UI: `streamlit run app.py`

## Code and PRs

- Do not modify or break existing API endpoints used by the Streamlit UI (`/scan`, `/audit-trail`, `/audit-proof`). New features (e.g. webhooks) should be additive.
- Use the same Docker/OpenClaw flow for any new agent-based features (reuse `_run_openclaw_agent` and env vars where appropriate).
- Keep secrets in `.env` only; never commit `.env` or real API keys.

## Docs

- Update `README.md` if you add endpoints or change run instructions.
- Update `.env.example` if you add new env vars.

## License

By contributing, you agree that your contributions will be licensed under the project’s MIT License.
