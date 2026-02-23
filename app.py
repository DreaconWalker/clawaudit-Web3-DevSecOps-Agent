import streamlit as st
import requests

st.set_page_config(page_title="ClawAudit Sentinel", page_icon="🛡️")
st.title("🛡️ ClawAudit Sentinel")
st.markdown("Automated OpenClaw Smart Contract Auditor")

address = st.text_input("Enter SURGE Contract Address", placeholder="0x...")

if st.button("Run Audit"):
    if address:
        with st.spinner("Agent is auditing and posting to Moltbook..."):
            try:
                # Calls our FastAPI backend
                res = requests.post("http://127.0.0.1:8000/scan", json={"contract_address": address})
                if res.status_code == 200:
                    st.success("Audit complete!")
                    st.text_area("Agent Output:", value=res.json().get("output", ""), height=300)
                else:
                    st.error(f"Backend Error: {res.text}")
            except Exception as e:
                st.error("Failed to connect to backend.")