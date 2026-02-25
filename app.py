import streamlit as st
import requests
import random

# --- UI Configuration ---
st.set_page_config(page_title="ClawAudit Enterprise", page_icon="🛡️", layout="wide")

st.title("🛡️ ClawAudit Sentinel")
st.markdown("**Autonomous Web3 DevSecOps Agent.** Powered by OpenClaw & Gemini.")
st.markdown("---")

# --- Create Tabs: One for the tech demo, one for the business pitch ---
tab1, tab2 = st.tabs(["🔍 Live AI Scanner (Demo)", "💼 Enterprise API (Monetization)"])

with tab1:
    st.subheader("🧪 Test Suite")
    st.write("Select a historical exploit to test the agent, or paste your own code.")

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

    selected_test = st.selectbox("Load Test Contract:", options=list(test_contracts.keys()))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📝 Smart Contract Source")
        default_code = test_contracts[selected_test]
        contract_code = st.text_area("Solidity Code", value=default_code, height=400, label_visibility="collapsed")

    with col2:
        st.markdown("### 🧠 AI Auditor Analysis")
        contract_address_optional = st.text_input("Contract address (optional)", placeholder="0x... (for attestation by address)", key="addr")
        if st.button("🚀 Initialize Sentinel Scan", use_container_width=True, type="primary"):
            if contract_code.strip() == "":
                st.warning("Please enter or select a smart contract to scan.")
            else:
                with st.spinner("Agent is running symbolic execution and logic flow analysis..."):
                    try:
                        payload = {"contract_code": contract_code}
                        if contract_address_optional.strip():
                            payload["contract_address"] = contract_address_optional.strip()
                        res = requests.post("http://127.0.0.1:8000/scan", json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            if data.get("status") == "error":
                                st.warning("Agent run completed with errors. Check logs below.")
                                st.code(data.get("logs", ""), language="text")
                            else:
                                st.success("✅ Audit complete. Results below. Detailed summary sent to Telegram; cryptic receipt posted to Moltbook.")
                                if data.get("proof"):
                                    with st.expander("🔗 Audit attestation (verifiable proof)", expanded=True):
                                        st.json(data["proof"])
                                        st.caption("Anyone can verify: GET /audit-proof?code_hash=" + data["proof"].get("code_hash", "")[:16] + "...")
                            st.markdown("### 📄 Report")
                            st.markdown(data.get("output", "No output generated."))
                        else:
                            st.error(f"Backend error: {res.text}")
                    except Exception as e:
                        st.error(f"Connection failed: {e}. Is the FastAPI backend running on http://127.0.0.1:8000 ?")
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
                r = requests.get("http://127.0.0.1:8000/audit-proof", params=params)
                if r.status_code == 200:
                    st.success("Attestation found — this code/contract was audited by ClawAudit.")
                    st.json(r.json())
                else:
                    st.info("No attestation found for this code or address.")
        except Exception as e:
            st.error(str(e))

with tab2:
    st.subheader("🏢 B2B API Monetization Dashboard")
    st.write("Developers can integrate ClawAudit directly into their GitHub Actions. Billed via Stripe.")
    
    col3, col4, col5 = st.columns(3)
    col3.metric(label="API Scans This Month", value="1,204", delta="+12%")
    col4.metric(label="Cost Per Scan", value="$50.00", delta="Flat Rate")
    col5.metric(label="Estimated Unbilled Revenue", value="$60,200", delta="+12%")
    
    st.markdown("---")
    st.markdown("### 🔑 Your Production API Keys")
    st.code("sk_live_clawaudit_7x9pQ2mN4vL8wK1jR5tY3", language="bash")
    
    st.markdown("### 💻 Example GitHub Actions Integration")
    st.code("""
name: ClawAudit Sentinel CI
on: [push]
jobs:
  security_scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run OpenClaw AI Audit
        run: |
          curl -X POST https://api.clawaudit.com/v1/scan \\
          -H "Authorization: Bearer ${{ secrets.CLAWAUDIT_API_KEY }}" \\
          -d '{"repo": "contracts/"}'
    """, language="yaml")