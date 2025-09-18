
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import Body
from research_handler import summarize_articles, analyze_summaries, format_report, run_research


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Summarizer endpoint
@app.post("/summarize")
async def summarize_endpoint(request: Request):
    data = await request.json()
    articles = data.get("articles", [])
    try:
        # summarize_articles is a sync function that internally uses asyncio
        summaries = summarize_articles(articles)
        return {"summaries": summaries}
    except Exception as e:
        return {"error": str(e)}

# Analyzer endpoint
@app.post("/analyze")
async def analyze_endpoint(request: Request):
    data = await request.json()
    summaries = data.get("summaries", [])
    try:
        report = analyze_summaries(summaries)
        return {"report": report}
    except Exception as e:
        return {"error": str(e)}

# Formatter endpoint
@app.post("/format")
async def format_endpoint(request: Request):
    data = await request.json()
    analysis = data.get("analysis", "")
    chat_title = data.get("chat_title", "Untitled")
    topic = data.get("topic", "")
    provider = data.get("provider", "")
    model = data.get("model", "")
    try:
        formatted = format_report(analysis, chat_title, topic, provider, model)
        return {"formatted": formatted}
    except Exception as e:
        return {"error": str(e)}

from models.provider_utils import query_all_models

print("[server.py] Starting FastAPI app...")

ALL_MODELS = dict()

def get_provider_and_models():# -> dict[str, Any]:
    ALL_MODELS = query_all_models()
    print("[mcp_server.py] get_provider_and_models called")
    return {
        "model_providers": list(ALL_MODELS.keys()),
        "models": ALL_MODELS
    }

@app.get("/models")
def get_models():
    print("[mcp_server.py] /models endpoint called")
    return get_provider_and_models()

@app.post("/research")
async def research(request: Request):
    print("[server.py] /research endpoint called")
    data = await request.json()
    print(f"[server.py] /research received data: {data}")
    query = data.get("query")
    user = data.get("user", "anonymous")
    model_provider = data.get("model_provider", "Ollama")
    model = data.get("model", "llama2")
    chat_title = data.get("chat_title", "Untitled")
    # Call run_research directly


    try:
        report = run_research(query=query, user=user, model_provider=model_provider, model=model, chat_title=chat_title)
        print(f"[server.py] /research raw output: {str(report)[:100]}")
        # Filter out agent meta-messages and ensure only well-structured document is returned
        if isinstance(report, str):
            # Remove agent meta-messages if present
            if report.strip().startswith("Agent response:"):
                # If agent output contains unsupported tool calls, fallback to a message
                if "browser tool" in report or "websearch" in report:
                    fallback = "[ERROR] The requested tool (browser/websearch) is not available. Please use only supported tools: collect, summarize_articles, analyze_summaries, format_report, store_report."
                    print(f"[server.py] /research unsupported tool fallback: {fallback}")
                    return {"report": fallback}
                doc_match = re.search(r"(#+ .+|\n# .+|\n\*\*Topic:|\n---|\n[A-Za-z].+)" , report, re.DOTALL)
                if doc_match:
                    filtered = report[doc_match.start():].strip()
                    print(f"[server.py] /research filtered output: {filtered[:100]}")
                    return {"report": filtered}
                else:
                    filtered = report.replace("Agent response:", "").strip()
                    print(f"[server.py] /research fallback filtered output: {filtered[:100]}")
                    return {"report": filtered}
            else:
                return {"report": report.strip()}
        else:
            return {"report": str(report)}
    except Exception as e:
        print(f"[server.py] /research error: {e}")
        return {"report": "Error: No valid report generated. Details: " + str(e)}
