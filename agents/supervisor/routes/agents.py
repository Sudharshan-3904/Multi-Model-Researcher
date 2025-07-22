from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/")
async def list_agents():
    # Dummy agent list for now
    return {"agents": ["data_collector-1", "analyzer-1"]}

@router.post("/register")
async def register_agent(agent_id: str):
    # Dummy registration logic
    return {"status": "registered", "agent_id": agent_id}
