import streamlit as st
import requests

st.set_page_config(page_title="ClawAudit Sentinel", page_icon="🛡️", layout="wide")
st.title("🛡️ ClawAudit Sentinel")
st.markdown("Real-time, AI-Powered Smart Contract Auditor.")

# The upgrade: A massive text area for actual code
contract_code = st.text_area("Paste your Solidity Smart Contract Code here:", height=300, placeholder="contract MyToken { ... }")

if st.button("Run Deep AI Audit"):
    if contract_code:
        with st.spinner("Agent is actively analyzing the bytecode and logic paths..."):
            try:
                res = requests.post("http://127.0.0.1:8000/scan", json={"contract_code": contract_code})
                if res.status_code == 200:
                    st.success("Audit complete & synced to Moltbook!")
                    st.text_area("Agent Output:", value=res.json().get("output", ""), height=300)
                else:
                    st.error(f"Backend Error: {res.text}")
            except Exception as e:
                st.error("Failed to connect to backend.")
    else:
        st.warning("Please paste some contract code first.")