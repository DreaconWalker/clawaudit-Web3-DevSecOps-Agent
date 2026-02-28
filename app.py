import streamlit as st
import requests
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- UI Configuration ---
API_BASE = os.environ.get("CLAWAUDIT_API_BASE", "http://127.0.0.1:8000")
st.set_page_config(page_title="ClawAudit Sentinel", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS: cleaner layout, cards, spacing ---
st.markdown("""
<style>
    /* Header and typography */
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }
    h1 { font-weight: 700; letter-spacing: -0.02em; color: #0f172a; }
    h2, h3 { font-weight: 600; color: #1e293b; margin-top: 1.25em; }
    /* Subtle card-style sections */
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdown"]) {
        border-radius: 8px;
    }
    /* Metric/card highlight */
    [data-testid="stMetricValue"] { font-weight: 600; }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { padding: 0.6rem 1rem; font-weight: 500; border-radius: 6px; }
    .stTabs [aria-selected="true"] { background: #f1f5f9; }
    /* Buttons */
    .stButton > button { border-radius: 6px; font-weight: 500; }
    .stButton > button[kind="primary"] { background: #0f172a; }
    /* Code blocks */
    code { background: #f1f5f9; padding: 0.15em 0.4em; border-radius: 4px; font-size: 0.9em; }
    /* Expander */
    .streamlit-expanderHeader { font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar: view-only notice, enterprise hosting, project guide & deploy ---
with st.sidebar:
    st.info("**👁️ View only** — This site is a read-only demo. Scans and write actions require a local or self-hosted backend.")
    st.caption("To run scans and get attestations, the backend AI engine must be run **locally** or deployed to an **enterprise VPS or your own VPS via Docker** (OpenClaw needs local filesystem access for memory logs and secure tool execution).")
    st.markdown("---")
    st.markdown("### 📖 Project guide")
    st.caption("How this project works and what OpenClaw does:")
    st.markdown("**docs/PROJECT_GUIDE.md** — API vs UI vs agent, flows, where to change behavior.")
    st.markdown("---")
    st.markdown("### 🚀 Deploy (open-source)")
    st.caption("Where and how to run this outside localhost:")
    st.markdown("**docs/DEPLOY.md** — Railway, Render, Fly.io, VPS, Streamlit Cloud; env vars; GitHub webhook.")

# --- Header ---
st.title("🛡️ ClawAudit Sentinel")
st.markdown("**Autonomous Web3 DevSecOps** — AI-powered smart contract audits, attestation, and auto-remediation. Built on **OpenClaw** and **Gemini**.")
st.markdown("---")

# --- Create Tabs: About, Scanner, GitHub, Enterprise ---
tab_about, tab1, tab2_github, tab2 = st.tabs(["📘 About & Idea", "🔍 Live AI Scanner (Demo)", "🔗 GitHub", "💼 Enterprise API (Monetization)"])

# --- About & Idea page (originality / what this project does) ---
with tab_about:
    st.subheader("What ClawAudit Does")
    st.markdown("""
    **ClawAudit** is not “yet another AI auditor.” It’s the **first open, low-cost audit attestation layer** for Web3:
    - You run an audit (paste code → AI report + Telegram + Moltbook).
    - You get a **proof**: we hash the report and the code, store the attestation (and optionally record it on-chain).
    - **Anyone can verify**: a public API can answer *“Was this code/contract audited by ClawAudit?”* → yes/no + timestamp + proof hash.
    """)
    st.markdown("---")
    st.subheader("Why ClawAudit Is Original: The One Thing Nobody Has Built")
    st.markdown("#### The gap")
    st.markdown("""
    **Everyone runs audits for themselves.** Protocols hire firms ($50k+). Devs run Slither, Mythril, or internal tools. Reports live in PDFs, Notion, or private repos. There is **no single, open channel** where:

    - Anyone can ask: *“Was this contract audited? By whom? When?”*
    - Anyone can get a **verifiable proof** (e.g. on-chain or cryptographic) that an audit happened
    - The **cost is low** (attestation tier), not “full audit firm” pricing

    So: audits are crucial, but the **attestation layer**—the public proof that an audit exists—is missing. That’s what we’re building.
    """)
    st.markdown("---")
    st.subheader("What we’re building: open audit attestation")
    st.markdown("""
    1. **You run an audit** (paste code → AI report + Telegram + Moltbook, as today).
    2. **You get a proof**: we hash the report and the code, store the attestation, and (optionally) record it on-chain (e.g. Base).
    3. **Anyone can verify**: a public API (and later, any frontend or protocol) can call:
       - *“Was this code/contract audited by ClawAudit?”* → yes/no + timestamp + proof hash (and tx hash if on-chain).

    So:
    - **One open channel**: one place (ClawAudit) that issues and exposes attestations.
    - **Less expensive tier**: you pay for the scan (or use the hackathon demo); the **attestation** (the proof that an audit happened) is cheap and public.
    - **Crucial**: users and integrators can trust “audited by ClawAudit” without each team building their own proof system.
    """)
    st.markdown("---")
    st.subheader("How this fits the ClawAudit name")
    st.markdown("""
    - **Claw** = OpenClaw agent doing the audit.
    - **Audit** = the report and the **attestation** (the proof).
    - The differentiator = **public, verifiable audit proof** that anyone can check—the one thing that, in this area, nobody has made as a single, open, low-cost channel.
    """)
    st.markdown("---")
    st.subheader("Summary")
    st.markdown("""
    | What exists today | What we add |
    |-------------------|-------------|
    | Private reports, ad‑hoc tools, expensive firms | **One open attestation layer** |
    | “Trust us, we audited” | **Verifiable proof** (hash + optional on-chain) |
    | No shared place to check “was this audited?” | **Public API: was this code/contract audited?** |
    | High cost for “proof” | **Low-cost attestation tier** |

    **That’s the originality:** ClawAudit = AI audit + open, verifiable audit proof in one place, at a less expensive tier.
    """)

with tab1:
    st.subheader("🧪 Test Suite")
    st.write("Select a historical exploit, paste your own code, or **fetch verified source** by contract address.")

    test_contracts = {
        "Custom Code": "",
        "The DAO Hack (Reentrancy)": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
contract VulnerableBank {
    mapping(address => uint) public balances;
    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }
    function withdraw() external {
        uint amount = balances[msg.sender];
        require(amount > 0, "Insufficient balance");
        // VULNERABILITY: Sending funds before updating state
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] = 0;
    }
}"""
    }

    selected_test = st.selectbox("Load Test Contract:", options=list(test_contracts.keys()), key="scanner_preset")

    default_code = test_contracts[selected_test]
    if "scanner_code_input" not in st.session_state:
        st.session_state["scanner_code_input"] = default_code
    if st.session_state.get("scanner_preset_prev") != selected_test:
        st.session_state["scanner_preset_prev"] = selected_test
        st.session_state["scanner_code_input"] = default_code

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📝 Smart Contract Source")
        st.text_area("Solidity Code", height=400, label_visibility="collapsed", key="scanner_code_input")

        # Fetch verified source by address (Etherscan / Basescan)
        st.caption("Or fetch verified source by contract address (EVM chains):")
        fetch_col1, fetch_col2 = st.columns([2, 1])
        with fetch_col1:
            fetch_address = st.text_input("Contract address", placeholder="0x...", key="fetch_addr", label_visibility="collapsed")
        with fetch_col2:
            fetch_clicked = st.button("Fetch verified source", type="secondary", use_container_width=True)
        if fetch_clicked and fetch_address.strip():
            with st.spinner("Fetching verified source from Etherscan/Basescan..."):
                try:
                    api_key = os.environ.get("ETHERSCAN_API_KEY", "")
                    # Try Etherscan first
                    r = requests.get(
                        "https://api.etherscan.io/api",
                        params={"module": "contract", "action": "getsourcecode", "address": fetch_address.strip(), **({"apikey": api_key} if api_key else {})},
                        timeout=10,
                    )
                    data = r.json()
                    if data.get("status") == "1" and data.get("result") and len(data["result"]) > 0:
                        src = data["result"][0].get("SourceCode", "").strip()
                        if src.startswith("{{"):
                            import json
                            try:
                                parsed = json.loads(src)
                                if isinstance(parsed, dict):
                                    parts = []
                                    for k, v in sorted(parsed.items()):
                                        if isinstance(v, dict) and "content" in v:
                                            parts.append(f"// {k}\n{v['content']}")
                                        elif isinstance(v, str):
                                            parts.append(f"// {k}\n{v}")
                                    src = "\n\n".join(parts) if parts else src
                                else:
                                    src = str(parsed)
                            except Exception:
                                pass
                        if src:
                            st.session_state["scanner_code_input"] = src
                            st.success("Source loaded. You can edit above and click **Initialize Sentinel Scan**.")
                            st.rerun()
                        else:
                            st.warning("No source code returned for this address (unverified contract?). Try Basescan for Base chain.")
                    else:
                        # Try Basescan
                        r2 = requests.get(
                            "https://api.basescan.org/api",
                            params={"module": "contract", "action": "getsourcecode", "address": fetch_address.strip(), **({"apikey": os.environ.get("BASESCAN_API_KEY", "")} if os.environ.get("BASESCAN_API_KEY") else {})},
                            timeout=10,
                        )
                        d2 = r2.json()
                        if d2.get("status") == "1" and d2.get("result") and len(d2["result"]) > 0:
                            src = d2["result"][0].get("SourceCode", "").strip()
                            if src:
                                st.session_state["scanner_code_input"] = src
                                st.success("Source loaded from Basescan. Edit above and click **Initialize Sentinel Scan**.")
                                st.rerun()
                        st.warning("Could not fetch source for this address (unverified or wrong chain?). Paste Solidity code manually.")
                except Exception as e:
                    st.error(f"Fetch failed: {e}")

    with col2:
        st.markdown("### 🧠 AI Auditor Analysis")
        scan_type_ui = st.selectbox("Scan type (Moltbook receipt style)", options=["manual", "demo", "full"], index=0, key="scan_type_ui", help="Manual / demo / full — the agent posts a scan-type-specific cryptic receipt to Moltbook.")
        repository_url_optional = st.text_input(
            "Repository URL (optional)",
            placeholder="https://github.com/owner/repo",
            key="repo_url",
            help="Full git clone URL so the agent can reference this repo in Telegram and Moltbook receipts.",
        )
        contract_address_optional = st.text_input("Contract address (optional)", placeholder="0x... (for attestation by address)", key="addr")

        with st.expander("🔑 Test credentials (optional)", expanded=False):
            st.caption("Override backend env for this run. Leave empty to use server .env. Use for testing without changing server config.")
            test_telegram_token = st.text_input("Telegram Bot Token", type="password", placeholder="Bot token from @BotFather", key="test_telegram_token")
            test_telegram_chat = st.text_input("Telegram Chat ID", type="default", placeholder="e.g. -1001234567890", key="test_telegram_chat")
            test_moltbook_key = st.text_input("Moltbook API Key", type="password", placeholder="Moltbook API key", key="test_moltbook_key")
            test_moltbook_submolt = st.text_input("Moltbook Submolt", value="lablab", placeholder="lablab", key="test_moltbook_submolt")

        if st.button("🚀 Initialize Sentinel Scan", use_container_width=True, type="primary"):
            code_to_scan = (st.session_state.get("scanner_code_input") or "").strip()
            addr = (contract_address_optional or "").strip()
            # If only address is filled, try to fetch source and scan in one go
            if not code_to_scan and addr:
                with st.spinner("Fetching verified source from address..."):
                    try:
                        api_key = os.environ.get("ETHERSCAN_API_KEY", "")
                        r = requests.get("https://api.etherscan.io/api", params={"module": "contract", "action": "getsourcecode", "address": addr, **({"apikey": api_key} if api_key else {})}, timeout=10)
                        data = r.json()
                        if data.get("status") == "1" and data.get("result") and len(data["result"]) > 0:
                            src = data["result"][0].get("SourceCode", "").strip()
                            if src.startswith("{{"):
                                try:
                                    import json
                                    parsed = json.loads(src)
                                    if isinstance(parsed, dict):
                                        parts = [f"// {k}\n{v.get('content', v) if isinstance(v, dict) else v}" for k, v in sorted(parsed.items())]
                                        src = "\n\n".join(parts) if parts else src
                                except Exception:
                                    pass
                            if src:
                                code_to_scan = src
                        if not code_to_scan:
                            r2 = requests.get("https://api.basescan.org/api", params={"module": "contract", "action": "getsourcecode", "address": addr, **({"apikey": os.environ.get("BASESCAN_API_KEY", "")} if os.environ.get("BASESCAN_API_KEY") else {})}, timeout=10)
                            d2 = r2.json()
                            if d2.get("status") == "1" and d2.get("result") and len(d2["result"]) > 0:
                                code_to_scan = d2["result"][0].get("SourceCode", "").strip() or None
                    except Exception:
                        pass
            if not code_to_scan:
                st.warning("**Source code is required to scan.** Paste Solidity code above, select a test contract, use **Fetch verified source**, or paste a **contract address** (verified on Etherscan/Basescan) and click Scan.")
            else:
                with st.spinner("Agent is running symbolic execution and logic flow analysis..."):
                    try:
                        payload = {"contract_code": code_to_scan, "scan_type": scan_type_ui}
                        if addr:
                            payload["contract_address"] = addr
                        if (st.session_state.get("repo_url") or "").strip():
                            payload["repository_url"] = (st.session_state.get("repo_url") or "").strip()
                        if (st.session_state.get("test_telegram_token") or "").strip():
                            payload["telegram_bot_token"] = (st.session_state.get("test_telegram_token") or "").strip()
                        if (st.session_state.get("test_telegram_chat") or "").strip():
                            payload["telegram_chat_id"] = (st.session_state.get("test_telegram_chat") or "").strip()
                        if (st.session_state.get("test_moltbook_key") or "").strip():
                            payload["moltbook_api_key"] = (st.session_state.get("test_moltbook_key") or "").strip()
                        if (st.session_state.get("test_moltbook_submolt") or "").strip():
                            payload["moltbook_submolt"] = (st.session_state.get("test_moltbook_submolt") or "").strip()
                        res = requests.post(f"{API_BASE}/scan", json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            if data.get("status") == "error":
                                st.warning("Agent run completed with errors. Check logs below.")
                                st.code(data.get("logs", ""), language="text")
                            else:
                                st.success("✅ Audit complete. The agent was instructed to post to Telegram (full report) and to your configured Moltbook submolt (cryptic receipt). If either didn't appear, check the Agent log below.")
                                if data.get("proof"):
                                    with st.expander("🔗 Audit attestation (verifiable proof)", expanded=True):
                                        st.json(data["proof"])
                                        st.caption("Anyone can verify: GET /audit-proof?code_hash=" + data["proof"].get("code_hash", "")[:16] + "...")
                                if data.get("agent_stderr"):
                                    with st.expander("⚠️ Agent log (Telegram/Moltbook errors show here)", expanded=True):
                                        st.code(data["agent_stderr"], language="text")
                                        st.caption("If Moltbook didn't post: look for 'MOLTBOOK_API_KEY missing' or API errors. Set MOLTBOOK_API_KEY and MOLTBOOK_SUBMOLT in backend .env (or in Test credentials). Only the manual 'Post to submolt' form was removed from the GitHub tab; every scan still triggers autonomous posting to your configured submolt.")
                            st.markdown("### 📄 Report")
                            st.markdown(data.get("output", "No output generated."))
                        else:
                            st.error(f"Backend error: {res.text}")
                    except Exception as e:
                        st.error(f"Connection failed: {e}. Is the FastAPI backend running on {API_BASE} ?")
    st.markdown("---")
    st.subheader("🔍 Verify an audit (open attestation)")
    st.caption("Anyone can check if code or a contract was audited by ClawAudit — the one open channel for audit proof.")
    verify_col1, verify_col2 = st.columns(2)
    with verify_col1:
        verify_code_hash = st.text_input("Code hash (hex)", placeholder="Paste code_hash from an attestation", key="vch")
    with verify_col2:
        verify_address = st.text_input("Or contract address", placeholder="0x...", key="va")
    if st.button("Check attestation"):
        try:
            params = {}
            if verify_code_hash.strip():
                params["code_hash"] = verify_code_hash.strip()
            if verify_address.strip():
                params["contract_address"] = verify_address.strip()
            if not params:
                st.warning("Enter a code hash or contract address.")
            else:
                r = requests.get(f"{API_BASE}/audit-proof", params=params)
                if r.status_code == 200:
                    st.success("Attestation found — this code/contract was audited by ClawAudit.")
                    st.json(r.json())
                else:
                    st.info("No attestation found for this code or address.")
        except Exception as e:
            st.error(str(e))

with tab2_github:
    st.subheader("🔗 GitHub integration")
    st.write("Connect your repo so **Pull Requests** get an automatic security audit comment from ClawAudit.")
    st.markdown("---")

    # --- Create remediation PR (credentials + initiate fix) ---
    st.markdown("### 🚨 Create remediation PR (push fix to GitHub)")
    st.caption("Enter GitHub credentials and patch details to open a PR with the fixed code on your repo. No local git required. **This is separate from the webhook** — the webhook runs when a PR is opened; this form creates a new PR with your patched code.")
    st.info("**Token:** Use a Personal Access Token with **repo** scope (GitHub → Settings → Developer settings → PAT). **File path** must exist on the **default branch** (e.g. `main`) of the repo.")
    with st.expander("GitHub credentials & patch details", expanded=True):
        gh_token = st.text_input(
            "GitHub token (Personal Access Token)",
            type="password",
            placeholder="ghp_... or paste token",
            key="gh_remediation_token",
            help="Token needs `repo` scope. Leave empty to use backend GITHUB_TOKEN from .env.",
        )
        repo_name = st.text_input(
            "Repository",
            placeholder="https://github.com/owner/repo or owner/repo",
            key="gh_repo_name",
            help="Full git clone URL (e.g. https://github.com/owner/repo) or owner/repo. Use the full URL so Telegram and Moltbook receipts can reference the repo.",
        )
        file_path = st.text_input(
            "File path in repo",
            placeholder="contracts/Vulnerable.sol",
            key="gh_file_path",
            help="Path to the vulnerable file that will be replaced with the patched code.",
        )
        vulnerability_title = st.text_input(
            "Vulnerability title (for PR title)",
            placeholder="Reentrancy in withdraw()",
            key="gh_vuln_title",
        )
        patched_code = st.text_area(
            "Patched code",
            height=280,
            placeholder="// Paste the fixed Solidity (or other) code from your OpenClaw audit result.",
            key="gh_patched_code",
        )
    if st.button("🚀 Create remediation PR", type="primary", key="create_remediation_pr_btn"):
        if not repo_name.strip():
            st.warning("Enter repository (owner/repo).")
        elif not file_path.strip():
            st.warning("Enter the file path in the repo.")
        elif not vulnerability_title.strip():
            st.warning("Enter a vulnerability title for the PR.")
        elif not patched_code.strip():
            st.warning("Paste the patched code to push.")
        else:
            with st.spinner("Creating branch and opening PR via GitHub API..."):
                try:
                    payload = {
                        "repo_name": repo_name.strip(),
                        "file_path": file_path.strip(),
                        "patched_code": patched_code.strip(),
                        "vulnerability_title": vulnerability_title.strip(),
                    }
                    if gh_token.strip():
                        payload["token"] = gh_token.strip()
                    r = requests.post(f"{API_BASE.rstrip('/')}/remediation/create-pr", json=payload, timeout=30)
                    if r.status_code == 200:
                        data = r.json()
                        st.success(f"PR created: **[#{data['number']}]({data['url']})** (branch: `{data['branch']}`)")
                        st.balloons()
                    else:
                        err = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
                        st.error(f"Failed to create PR: {err}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {e}. Is the backend running on {API_BASE}?")
                except Exception as e:
                    st.error(str(e))

    st.markdown("---")
    webhook_url = f"{API_BASE.rstrip('/')}/webhook/github"
    st.markdown("### Webhook URL")
    st.code(webhook_url, language="text")
    st.caption("Use this URL in your GitHub repo: **Settings → Webhooks → Add webhook**.")
    st.warning("**Tunnel to the FastAPI port (8000), not Streamlit (8501).** If you use Pinggy or ngrok, run `pinggy http 8000` or `ngrok http 8000` so the Payload URL points at your backend. A **405 Method Not Allowed** usually means the tunnel is forwarding to the wrong port (e.g. Streamlit doesn't accept POST /webhook/github).")
    st.markdown("---")
    st.markdown("### Setup steps")
    st.markdown("""
    1. In your repo go to **Settings → Webhooks → Add webhook**.
    2. **Payload URL:** paste the URL above (your API must be reachable from the internet for GitHub to call it; use a tunnel like **Pinggy** or **ngrok** and **tunnel to port 8000** where FastAPI runs).
    3. **Content type:** `application/json`.
    4. **Which events:** choose **Let me select individual events** → enable **Pull requests**.
    5. Save. Add `GITHUB_TOKEN` to your backend `.env` (token needs `repo` scope and permission to write pull request comments).

    When a PR is **opened** or **synchronized**, ClawAudit will audit the diff and post the result as a comment on the PR. A **PR-specific update** is also posted to your Moltbook submolt (e.g. "PR security review completed for repo PR #N").
    """)
    st.info("Backend must be running and `GITHUB_TOKEN` set in `.env` for comments to be posted.")
    st.markdown("**How to test:** Create a repo → add a branch with Solidity code → open a Pull Request. The app will audit the diff and post a comment on the PR. See **docs/TESTING_GITHUB.md** in the repo for step-by-step.")
    st.markdown("---")
    st.markdown("#### Public vs private repo")
    st.caption("Both work. For **private** repos, the token must belong to an account that has access to the repo (or use a GitHub App with repo access).")

with tab2:
    st.subheader("🏢 Enterprise API & Project Overview")
    st.markdown("ClawAudit exposes a **REST API** for scans, attestation, and GitHub auto-remediation. All core flows are implemented; integrate via API or use this UI as reference.")

    st.markdown("---")
    st.markdown("### 📡 API base & endpoints")
    st.caption("Backend runs at the URL below. Full OpenAPI docs: **/docs** when the server is running.")
    st.code(API_BASE, language="text")

    st.markdown("""
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scan` | POST | Submit Solidity code → AI audit report + attestation (optional Telegram + Moltbook receipt). |
| `/audit-proof` | GET | Look up attestation by `code_hash` or `contract_address`. |
| `/audit-trail` | GET | List recent attestations (`?limit=N`). |
| `/remediation/create-pr` | POST | Create a PR with patched code (repo, file path, patched_code, vulnerability_title, optional token). |
| `/webhook/github` | POST | **GitHub webhook:** on PR open/sync → audit diff → post comment; if 1 `.sol` + patched block → auto remediation PR. |
| `/moltbook/post` | POST | Post a dev update to Moltbook submolt (body: `title`, `content`). |
""")

    st.markdown("---")
    st.markdown("### 🔗 Project barebones (where everything lives)")
    st.markdown("""
- **Backend:** `main.py` — FastAPI app, scan orchestration, attestation registry, GitHub webhook, remediation PR logic.
- **UI:** `app.py` — This Streamlit app (Scanner, GitHub, Enterprise tabs).
- **Agent config:** `agent_config/` — OpenClaw config, skills (Moltbook, Telegram), model (e.g. Gemini). Agent runs in Docker via `docker compose`.
- **Attestation store:** `data/audit_registry.json` — code_hash → proof (report_hash, timestamp, auditor).
- **Docs:** `README.md` (quick start, env, commands), `docs/TESTING_GITHUB.md` (webhook + PR test steps), `docs/OPENCLAW_MEMORY.md` (agent memory), `docs/PROJECT_GUIDE.md` (project sense + OpenClaw role).
- **Contracts:** `contracts/` — e.g. ClawAuditRegistry.sol.
    """)

    st.markdown("---")
    st.markdown("### 🔄 Flows at a glance")
    with st.expander("Scan flow (Live AI Scanner tab)", expanded=False):
        st.markdown("1. User pastes Solidity (or fetches by address). 2. **POST /scan** with `contract_code` (+ optional `contract_address`, `scan_type`). 3. Backend runs OpenClaw in Docker with a security-audit prompt. 4. Agent returns report; backend writes attestation to registry, returns report + proof. 5. Agent can post to Telegram (full report) and Moltbook (cryptic receipt).")
    with st.expander("GitHub webhook flow (autonomous)", expanded=False):
        st.markdown("1. Repo webhook points to **POST /webhook/github**. 2. On PR opened/synchronized, backend fetches PR diff via GitHub API. 3. OpenClaw audits the diff; backend posts the report as a PR comment. 4. If report contains **## Patched code** and PR touches **exactly one .sol file**, backend creates a **remediation PR** (new branch, patched file, PR to base). 5. Second comment on original PR links to the fix PR.")
    with st.expander("Manual remediation PR (GitHub tab)", expanded=False):
        st.markdown("User supplies repo, file path, vulnerability title, and **patched code** (e.g. from a prior scan). **POST /remediation/create-pr** creates branch `clawaudit-patch-{uuid}` from default branch, commits the patch, opens PR. No local git; GitHub API only.")

    st.markdown("---")
    st.markdown("### 💻 Example: call the scan API")
    st.code("""
curl -X POST """ + API_BASE.rstrip("/") + """/scan \\
  -H "Content-Type: application/json" \\
  -d '{"contract_code": "pragma solidity ^0.8.0; contract C { }", "scan_type": "manual"}'
""", language="bash")
    st.caption("Returns JSON: `status`, `output` (report), `proof` (code_hash, report_hash, timestamp), optional `agent_stderr`.")