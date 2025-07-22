from fastapi import APIRouter, HTTPException
from shared.schemas.task_schemas import Task
from agents.supervisor.supervisor_agent import SupervisorAgent

router = APIRouter()
supervisor = SupervisorAgent(agent_id="supervisor-1", config={})

@router.post("/")
async def create_task(task: Task):
    agent_id = await supervisor.assign_task(task)
    if not agent_id:
        raise HTTPException(status_code=503, detail="No available agents")
    return {"assigned_agent": agent_id, "task_id": task.id}

@router.get("/")
async def list_tasks():
    return {"tasks": list(supervisor.tasks.values())}
