from fastapi import FastAPI, HTTPException, status, APIRouter
from typing import List, Dict
import uuid

from . import models
from . import agents as agent_service # Renamed to avoid conflict

app = FastAPI(
    title="Agent Creator Backend",
    description="API for creating, managing, and executing agents.",
    version="0.1.0",
)

router = APIRouter(prefix="/api", tags=["Agents"])

@router.post("/agents", response_model=models.Agent, status_code=status.HTTP_201_CREATED)
async def create_new_agent(agent_create: models.AgentCreate):
    return agent_service.create_agent(agent_create)

@router.get("/agents", response_model=List[models.Agent])
async def read_agents():
    return agent_service.list_agents()

@router.get("/agents/{agent_id}", response_model=models.Agent)
async def read_agent(agent_id: uuid.UUID):
    agent = agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent

@router.put("/agents/{agent_id}", response_model=models.Agent)
async def update_existing_agent(agent_id: uuid.UUID, agent_update: models.AgentUpdate):
    agent = agent_service.update_agent(agent_id, agent_update)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent

@router.delete("/agents/{agent_id}", response_model=models.Agent) # Or status_code=204 for no content
async def delete_existing_agent(agent_id: uuid.UUID):
    agent = agent_service.delete_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    # If returning 204, just return None or Response(status_code=204)
    return agent

@router.post("/agents/{agent_id}/execute", response_model=models.Execution, status_code=status.HTTP_202_ACCEPTED)
async def execute_agent_task(agent_id: uuid.UUID, execution_create: models.ExecutionCreate):
    agent = agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    execution = agent_service.create_agent_execution(agent_id, execution_create)
    if not execution:
        # This case might be redundant if agent check is done above,
        # but good for safety if create_agent_execution had other failure modes
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create execution task")
    return execution

@router.get("/agents/{agent_id}/executions/{execution_id}", response_model=models.Execution)
async def get_execution_details(agent_id: uuid.UUID, execution_id: uuid.UUID):
    execution = agent_service.get_agent_execution(agent_id, execution_id)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return execution

@router.get("/agents/{agent_id}/executions", response_model=List[models.Execution])
async def list_executions_for_agent(agent_id: uuid.UUID):
    agent = agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent_service.list_agent_executions(agent_id)

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Agent Creator Backend. Docs at /docs"}
