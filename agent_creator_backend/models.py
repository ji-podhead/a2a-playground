from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid
from datetime import datetime

class AgentType(str, Enum):
    MCP = "mcp"
    A2A = "a2a"
    ADK = "adk"
    FINANCIAL_HOST = "financial_host" # Added
    CUSTOM = "custom_agent_type" # Example, can be expanded

class AgentStatus(str, Enum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    UPDATED = "updated"

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentBase(BaseModel):
    name: str = Field(..., example="My New Agent")
    agent_type: AgentType = Field(..., example=AgentType.MCP)
    config: Dict[str, Any] = Field({}, example={"param1": "value1"})

class AgentCreate(AgentBase):
    pass

class Agent(AgentBase):
    agent_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: AgentStatus = Field(default=AgentStatus.CREATED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True # Changed from orm_mode for Pydantic v2

class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, example="Updated Agent Name")
    config: Optional[Dict[str, Any]] = Field(None, example={"param1": "new_value"})


class ExecutionBase(BaseModel):
    parameters: Dict[str, Any] = Field({}, example={"input_data": "sample"})

class ExecutionCreate(ExecutionBase):
    pass

class Execution(ExecutionBase):
    execution_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    agent_id: uuid.UUID
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True # Changed from orm_mode for Pydantic v2
