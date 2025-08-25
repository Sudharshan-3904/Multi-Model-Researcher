print("[app.py] Starting Streamlit app...")
import streamlit as st
import requests
import os
from dotenv import set_key, load_dotenv

print("[app.py] Setting Streamlit page config")
st.set_page_config(page_title="Multi-Agent Researcher", layout="wide")

print("[app.py] Showing sidebar navigation")
page = st.sidebar.selectbox("Navigation", ["Dashboard", "Add Provider"])

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

def get_model_providers():
    print("[app.py] Getting model providers from backend")
    try:
        resp = requests.get("http://localhost:8000/models")
        data = resp.json()
        print(f"[app.py] /models response: {data}")
        if "model_providers" in data:
            return data["model_providers"]
        elif "models" in data:
            # fallback for old API
            return list(data["models"].keys())
    except Exception as e:
        print(f"[app.py] Error getting model providers: {e}")
    env_providers = list(get_providers_from_env().keys())
    # Always include LM Studio as an option
    if 'LM Studio' not in env_providers:
        env_providers.append('LM Studio')
    print(f"[app.py] Returning providers: {env_providers}")
    return env_providers if env_providers else ["Ollama", "LM Studio"]

def get_models_for_provider(provider):
    print(f"[app.py] Getting models for provider: {provider}")
    try:
        resp = requests.get("http://localhost:8000/models")
        data = resp.json()
        print(f"[app.py] /models response: {data}")
        if "models" in data:
            # provider key may be upper or lower, try both
            for key in (provider, provider.upper(), provider.lower()):
                if key in data["models"]:
                    print(f"[app.py] Found models for {key}: {data['models'][key]}")
                    return data["models"][key]
    except Exception as e:
        print(f"[app.py] Error getting models for provider {provider}: {e}")
    print(f"[app.py] Returning default model for provider: {provider}")
    return [provider]

if page == "Dashboard":
    print("[app.py] Dashboard page selected")
    st.title("🧠 Multi-Agent Researcher Dashboard")
    user = st.text_input("Enter your name:")
    query = st.text_area("Enter your research query:", "Find the most cited papers on quantum finance in the last 5 years")

    providers = get_model_providers()
    print(f"[app.py] Providers for selectbox: {providers}")
    provider = st.selectbox("Choose a model provider", providers)
    models = get_models_for_provider(provider)
    print(f"[app.py] Models for selectbox: {models}")
    model = st.selectbox("Choose a model for analysis", models)

    if st.button("Run Research"):
        print(f"[app.py] Run Research clicked with provider={provider}, model={model}, user={user}, query={query}")
        with st.spinner("Agents are working via MCP server..."):
            try:
                resp = requests.post(
                    "http://localhost:8000/research",
                    json={"query": query, "user": user or 'anonymous', "model_provider": provider, "model_provider": model}
                )
                report = resp.json().get("report", "No report returned.")
                print(f"[app.py] Research response: {report}")
            except Exception as e:
                report = f"Error: {e}"
                print(f"[app.py] Error in research: {e}")
        st.success("Research complete!")
        st.text_area("Result Report", report, height=200)
        st.info("All actions are logged for audit and compliance.")

elif page == "Add Provider":
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
