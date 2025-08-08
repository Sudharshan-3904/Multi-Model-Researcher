from fastapi import FastAPI, Request
from agents.supervisor import SupervisorAgent
from models.model_interface import ModelInterface
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
supervisor = SupervisorAgent()
model_interface = ModelInterface()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/research")
async def research(request: Request):
    data = await request.json()
    query = data.get("query")
    user = data.get("user", "anonymous")
    model = data.get("model", "Ollama")
    report = supervisor.handle_request(query, user, model=model)
    return {"report": report}

@app.get("/models")
def get_models():
    return {"models": model_interface.list_models()}
