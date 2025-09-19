print("[app.py] Starting Streamlit app...")
from pickle import GLOBAL
import streamlit as st
import requests
import os
from dotenv import set_key, load_dotenv

print("[app.py] Setting Streamlit page config")
st.set_page_config(page_title="Multi-Agent Researcher", layout="wide")

print("[app.py] Showing sidebar navigation")

tool_page = st.sidebar.radio("Tools", ["Dashboard", "Summarizer", "Analyzer", "Formatter", "Add Provider"])
st.sidebar.button("Refresh Models/Providers", on_click=lambda: onload())

# Use session_state for providers and models
if 'ALL_PROVIDERS' not in st.session_state:
    st.session_state.ALL_PROVIDERS = []
if 'ALL_MODELS' not in st.session_state:
    st.session_state.ALL_MODELS = {}

def get_env_path():
    path = os.path.join(os.path.dirname(__file__), ".env")
    print(f"[app.py] .env path: {path}")
    return path

def get_providers_from_env():
    env_path = get_env_path()
    print(f"[app.py] Reading providers from env: {env_path}")
    if not os.path.exists(env_path):
        print("[app.py] .env file does not exist")
        return {}
    providers = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and "=" in line:
                k, v = line.strip().split("=", 1)
                if k.endswith("_API_KEY"):
                    providers[k.replace("_API_KEY", "")] = v
    print(f"[app.py] Providers found: {providers}")
    return providers

def add_provider_to_env(provider, api_key):
    env_path = get_env_path()
    key = f"{provider.upper()}_API_KEY"
    print(f"[app.py] Adding provider {provider} with key {key} to env")
    # Overwrite or add
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(key + "="):
                    lines.append(f"{key}={api_key}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{key}={api_key}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"[app.py] Provider {provider} added/updated in .env")

def get_models_and_providers():
    print(f"[app.py] Getting models and providers from backend")
    providers, models = [], {}
    try:
        resp = requests.get("http://localhost:8000/models")
        data = resp.json()
        print(f"[app.py] /models response: {data}")
        if "model_providers" in data:
            providers = data["model_providers"]
        if "models" in data:
            models = data["models"].copy()
    except Exception as e:
        print(f"[app.py] Error getting models and providers: {e}")
    
    return providers, models


def onload():
    print("[app.py] onload called")
    providers, models = get_models_and_providers()
    st.session_state.ALL_PROVIDERS = providers
    st.session_state.ALL_MODELS = models

if tool_page == "Dashboard":
    print("[app.py] Dashboard page selected")
    st.title("🧠 Multi-Agent Researcher Dashboard")
    user = st.text_input("Enter your name:")
    query = st.text_area("Enter your research query:", "Quantum physics")

    # Use session_state for providers/models
    providers = st.session_state.ALL_PROVIDERS
    print(f"[app.py] Providers for selectbox: {providers}")
    if not providers:
        st.warning("No providers available. Please add a provider or check backend.")
    else:
        provider = st.selectbox("Choose a model provider", providers)
        models = st.session_state.ALL_MODELS[provider] if provider in st.session_state.ALL_MODELS else []
        print(f"[app.py] Models for selectbox: {models}")
        if not models:
            st.warning("No models available for this provider.")
        else:
            model = st.selectbox("Choose a model for analysis", models)

            if st.button("Run Research"):
                print(f"[app.py] Run Research clicked with provider={provider}, model={model}, user={user}, query={query}")
                print(f"[app.py] Sending research request with: query={query}, user={user}, model_provider={provider}, model={model}")
                with st.spinner("Agents are working via MCP server..."):
                    try:
                        payload = {
                            "query": query,
                            "user": user or 'anonymous',
                            "model_provider": provider,
                            "model": model
                        }
                        print(f"[app.py] Payload: {payload}")
                        resp = requests.post(
                            "http://localhost:8000/research",
                            json=payload
                        )
                        print(f"[app.py] Response status: {resp.status_code}")
                        report = resp.json().get("report", "No report returned.")
                        print(f"[app.py] Research response: {report}")
                    except Exception as e:
                        report = f"Error: {e}"
                        print(f"[app.py] Error in research: {e}")
                st.success("Research complete!")
                # st.text_area("Result Report", report, height=500)
                st.markdown(report)
                st.info("All actions are logged for audit and compliance.")

elif tool_page == "Summarizer":
    st.title("Summarizer Tool")
    st.write("Summarize a list of articles (title, abstract, url, citations). Paste as JSON list.")
    articles_json = st.text_area("Articles JSON", '[{"title": "Sample", "abstract": "...", "url": "...", "citations": 100}]', height=200)
    if st.button("Summarize Articles"):
        try:
            articles = eval(articles_json)
            resp = requests.post("http://localhost:8000/summarize", json={"articles": articles})
            summaries = resp.json().get("summaries", [])
            st.write("### Summaries:")
            for s in summaries:
                st.markdown(s)
        except Exception as e:
            st.error(f"Error: {e}")

elif tool_page == "Analyzer":
    st.title("Analyzer Tool")
    st.write("Analyze a list of summaries. Paste as JSON list of strings.")
    summaries_json = st.text_area("Summaries JSON", '["Summary 1", "Summary 2"]', height=200)
    if st.button("Analyze Summaries"):
        try:
            summaries = eval(summaries_json)
            resp = requests.post("http://localhost:8000/analyze", json={"summaries": summaries})
            report = resp.json().get("report", "")
            st.write("### Analysis Report:")
            st.markdown(report)
        except Exception as e:
            st.error(f"Error: {e}")

elif tool_page == "Formatter":
    st.title("Formatter Tool")
    st.write("Format an analysis into a markdown report.")
    analysis = st.text_area("Analysis Text", "Paste analysis here", height=200)
    chat_title = st.text_input("Chat Title", "Untitled")
    topic = st.text_input("Topic", "Quantum Physics")
    provider = st.text_input("Provider", "Ollama")
    model = st.text_input("Model", "llama2")
    if st.button("Format Report"):
        try:
            payload = {"analysis": analysis, "chat_title": chat_title, "topic": topic, "provider": provider, "model": model}
            resp = requests.post("http://localhost:8000/format", json=payload)
            formatted = resp.json().get("formatted", "")
            st.write("### Formatted Markdown Report:")
            st.markdown(formatted)
        except Exception as e:
            st.error(f"Error: {e}")

elif tool_page == "Add Provider":
    print("[app.py] Add Provider page selected")
    st.title("Add New Model Provider")
    st.write("Register a new model provider and its API key. This will be stored in the local incex.")
    provider = st.text_input("Provider Name (e.g., OpenAI, Anthropic, Ollama)")
    api_key = st.text_input("API Key", type="password")
    if st.button("Add Provider"):
        print(f"[app.py] Add Provider clicked with provider={provider}, api_key={api_key}")
        if provider and api_key:
            add_provider_to_env(provider, api_key)
            st.success(f"Provider '{provider}' added to index!")
        else:
            st.error("Please enter both provider name and API key.")


# Always call onload once per session
if 'initialized' not in st.session_state or not st.session_state.initialized:
    print("[app.py] Initializing session state")
    onload()
    st.session_state.initialized = True
