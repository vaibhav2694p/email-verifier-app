import streamlit as st

st.title("API Settings")
st.code("uvicorn api.main:app --reload")
st.caption("Set API_KEY to require X-API-Key authentication.")
