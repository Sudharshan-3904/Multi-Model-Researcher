import streamlit as st
import requests

st.set_page_config(page_title="Multi-Agent Researcher", layout="wide")
st.title("🧠 Multi-Agent Researcher Dashboard")


# st.set_page_config(page_title="Multi-Agent Researcher", layout="wide")
# st.title("🧠 Multi-Agent Researcher Dashboard")

user = st.text_input("Enter your name or API key:")
query = st.text_area("Enter your research query:", "Find the most cited papers on quantum finance in the last 5 years")

# Fetch available models from MCP server
@st.cache_data
def get_models():
    try:
        resp = requests.get("http://localhost:8000/models")
        return resp.json().get("models", ["Ollama", "LM Studio"])
    except Exception:
        return ["Ollama", "LM Studio"]

models = get_models()
model = st.selectbox("Choose a model for analysis", models)

if st.button("Run Research"):
    with st.spinner("Agents are working via MCP server..."):
        try:
            resp = requests.post(
                "http://localhost:8000/research",
                json={"query": query, "user": user or 'anonymous', "model": model}
            )
            report = resp.json().get("report", "No report returned.")
        except Exception as e:
            report = f"Error: {e}"
    st.success("Research complete!")
    st.text_area("Result Report", report, height=200)
    st.info("All actions are logged for audit and compliance.")
