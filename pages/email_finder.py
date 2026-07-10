import pandas as pd
import streamlit as st

from services.email_finder import generate_email_patterns

st.title("Email Finder")
st.caption("Pattern-generated candidates are guesses and must be verified. No emails are sent.")
first = st.text_input("First Name")
last = st.text_input("Last Name")
domain = st.text_input("Company Domain")
if st.button("Generate Patterns"):
    st.dataframe(pd.DataFrame(generate_email_patterns(first, last, domain)), use_container_width=True)
