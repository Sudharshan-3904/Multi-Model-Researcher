import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.provider_utils import query_all_models

print("[server.py] Starting FastAPI app...")
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from research_handler import run_research

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                import re
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
