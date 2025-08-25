print("[mcp_server.py] Starting FastAPI app...")
from fastapi import FastAPI, Request
from agents.supervisor import SupervisorAgent
from models.model_interface import ModelInterface
from fastapi.middleware.cors import CORSMiddleware
from models.provider_utils import query_all_models

app = FastAPI()
print("[mcp_server.py] Initializing SupervisorAgent and ModelInterface")
supervisor = SupervisorAgent()
model_interface = ModelInterface()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("[mcp_server.py] Querying all providers and models at startup")
ALL_MODELS = dict()

def get_provider_and_models():# -> dict[str, Any]:
    ALL_MODELS = query_all_models()
    print("[mcp_server.py] get_provider_and_models called")
    return {
        "model_providers": list(ALL_MODELS.keys()),
        "models": ALL_MODELS
    }

@app.post("/research")
async def research(request: Request):
    print("[mcp_server.py] /research endpoint called")
    data = await request.json()
    print(f"[mcp_server.py] /research received data: {data}")
    query = data.get("query")
    user = data.get("user", "anonymous")
    model_provider = data.get("model_provider", "Ollama")
    model = data.get("model", "")
    report = supervisor.handle_request(query, user, model_provider=model_provider, model=model)
    print(f"[mcp_server.py] /research returning report: {report[:100]}")
    return {"report": report}

@app.get("/models")
def get_models():
    print("[mcp_server.py] /models endpoint called")
    return get_provider_and_models()
