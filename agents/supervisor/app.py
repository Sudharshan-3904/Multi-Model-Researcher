"""
FastAPI app entrypoint for Supervisor Agent.
"""
from fastapi import FastAPI
from agents.supervisor.supervisor_agent import SupervisorAgent
from config.settings import SUPERVISOR_CONFIG

app = FastAPI(title="Supervisor Agent API")
supervisor = SupervisorAgent(agent_id="supervisor-1", config=SUPERVISOR_CONFIG)

@app.on_event("startup")
async def startup_event():
    await supervisor.initialize()

# Import and include routes
from agents.supervisor.routes.tasks import router as tasks_router
from agents.supervisor.routes.agents import router as agents_router
from agents.supervisor.routes.health import router as health_router

app.include_router(tasks_router, prefix="/tasks")
app.include_router(agents_router, prefix="/agents")
app.include_router(health_router, prefix="/health")
