from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
from .models import Agent, AgentCreate, AgentUpdate, AgentStatus, Execution, ExecutionCreate, ExecutionStatus, AgentType

# In-memory storage
db_agents: Dict[uuid.UUID, Agent] = {}
# Store executions per agent_id, then per execution_id for easier lookup
db_executions: Dict[uuid.UUID, Dict[uuid.UUID, Execution]] = {}

def create_agent(agent_create: AgentCreate) -> Agent:
    agent = Agent(**agent_create.model_dump(), agent_id=uuid.uuid4(), status=AgentStatus.CREATED, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db_agents[agent.agent_id] = agent
    db_executions[agent.agent_id] = {} # Initialize execution dict for this agent
    return agent

def get_agent(agent_id: uuid.UUID) -> Optional[Agent]:
    return db_agents.get(agent_id)

def list_agents() -> List[Agent]:
    return list(db_agents.values())

def update_agent(agent_id: uuid.UUID, agent_update: AgentUpdate) -> Optional[Agent]:
    agent = db_agents.get(agent_id)
    if agent:
        update_data = agent_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(agent, key, value)
        agent.updated_at = datetime.utcnow()
        agent.status = AgentStatus.UPDATED # Or reflect based on actual update
        db_agents[agent_id] = agent
        return agent
    return None

def delete_agent(agent_id: uuid.UUID) -> Optional[Agent]:
    if agent_id in db_agents:
        # Also remove associated executions
        if agent_id in db_executions:
            del db_executions[agent_id]
        return db_agents.pop(agent_id)
    return None

def create_agent_execution(agent_id: uuid.UUID, execution_create: ExecutionCreate) -> Optional[Execution]:
    agent = get_agent(agent_id)
    if not agent:
        return None

    execution = Execution(
        **execution_create.model_dump(),
        execution_id=uuid.uuid4(),
        agent_id=agent_id,
        status=ExecutionStatus.PENDING, # Default status
        submitted_at=datetime.utcnow()
    )
    db_executions[agent_id][execution.execution_id] = execution

    # Simulate execution start for now
    # In a real scenario, this would trigger an async task
    print(f"Agent {agent.name} (ID: {agent_id}) received execution request {execution.execution_id}.")
    print(f"Parameters: {execution.parameters}")

    # Placeholder: Simulate some processing and update status
    # This should be handled by a background task manager in a real app
    # For now, let's assume it starts running quickly
    execution.started_at = datetime.utcnow()
    execution.status = ExecutionStatus.RUNNING # Simulate it's now running
    # To simulate completion/failure, another mechanism would update this.

    return execution

def get_agent_execution(agent_id: uuid.UUID, execution_id: uuid.UUID) -> Optional[Execution]:
    if agent_id in db_executions and execution_id in db_executions[agent_id]:
        return db_executions[agent_id][execution_id]
    return None

def list_agent_executions(agent_id: uuid.UUID) -> List[Execution]:
     if agent_id in db_executions:
         return list(db_executions[agent_id].values())
     return []
