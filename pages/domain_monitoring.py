import streamlit as st

from domain_health import check_domain_health
from verifier.config import VerifierConfig

st.title("Domain Monitoring")
domain = st.text_input("Domain")
if st.button("Check Domain Health") and domain:
    config = VerifierConfig.from_env()
    config.enable_domain_monitoring = True
    st.json(check_domain_health(domain, config))
