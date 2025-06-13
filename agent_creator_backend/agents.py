from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
from .models import Agent, AgentCreate, AgentUpdate, AgentStatus, Execution, ExecutionCreate, ExecutionStatus, AgentType

# NOTE: This module uses synchronous functions for agent execution (create_agent_execution).
# Integrating asynchronous agents (like ADK agents using httpx.AsyncClient or async tool calls)
# synchronously can lead to blocking or errors. Ideally, execution endpoints and internal
# calls to async agents should be `async def` and properly awaited.
# The current implementation for FinancialHostLogicAgent uses a simplified, synchronous placeholder.

from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
from .models import Agent, AgentCreate, AgentUpdate, AgentStatus, Execution, ExecutionCreate, ExecutionStatus, AgentType

# Import new classes
from .object_pool import ObjectPool
from .a2a_mock import A2AMock
from .adk_mock import ADKMock
from .financial_host_agent import FinancialHostLogicAgent

# In-memory storage
db_agents: Dict[uuid.UUID, Agent] = {}
db_executions: Dict[uuid.UUID, Dict[uuid.UUID, Execution]] = {}

# --- Object Pool Initialization ---
A2A_AGENT_POOL_SIZE = 5  # Example size
ADK_AGENT_POOL_SIZE = 5  # Example size
FINANCIAL_HOST_AGENT_POOL_SIZE = 2

def create_a2a_agent_instance(config: Dict[str, Any]) -> A2AMock:
    return A2AMock(config=config)

def create_adk_agent_instance(config: Dict[str, Any]) -> ADKMock:
    return ADKMock(config=config)

def create_financial_host_agent_instance(config: Dict[str, Any]) -> FinancialHostLogicAgent:
    return FinancialHostLogicAgent(config=config)

# Global pools for A2A and ADK agents
# These pools are created with default configurations.
# Specific configurations will be passed when acquiring/creating instances if needed.
a2a_agent_pool = ObjectPool(creator=create_a2a_agent_instance, initial_size=A2A_AGENT_POOL_SIZE, config={"type": "a2a_default"})
adk_agent_pool = ObjectPool(creator=create_adk_agent_instance, initial_size=ADK_AGENT_POOL_SIZE, config={"type": "adk_default"})
financial_host_agent_pool = ObjectPool(
    creator=create_financial_host_agent_instance,
    initial_size=FINANCIAL_HOST_AGENT_POOL_SIZE,
    config={ # Default config for the pool, can be overridden by agent's own config
        "ANALYSIS_LOOP_AGENT_URL": "http://localhost:8005/mock",
        "PG_INTERFACE_AGENT_URL": "http://localhost:8001/mock",
        "FIN_INTERFACE_AGENT_URL": "http://localhost:8002/mock",
        "SHOPPING_AGENT_URL": "http://localhost:8007/mock",
        "HOST_AGENT_MODEL": "gemini-1.5-flash-latest"
    }
)
# --- End Object Pool Initialization ---

def create_agent(agent_create: AgentCreate) -> Agent:
    agent = Agent(**agent_create.model_dump(), agent_id=uuid.uuid4(), status=AgentStatus.CREATED, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db_agents[agent.agent_id] = agent
    db_executions[agent.agent_id] = {}
    print(f"Agent '{agent.name}' of type '{agent.agent_type.value}' created with ID {agent.agent_id} and config {agent.config}")
    return agent

def get_agent(agent_id: uuid.UUID) -> Optional[Agent]:
    return db_agents.get(agent_id)

def list_agents() -> List[Agent]:
    return list(db_agents.values())

def update_agent(agent_id: uuid.UUID, agent_update: AgentUpdate) -> Optional[Agent]:
    agent = db_agents.get(agent_id)
    if agent:
        update_data = agent_update.model_dump(exclude_unset=True)
        # If config is being updated, we might need to handle pools differently,
        # e.g., by clearing and recreating pools associated with this agent's specific config,
        # or by managing different pools for different configs.
        # For now, this basic update doesn't reconfigure live pools, only the agent's stored config.
        if 'config' in update_data:
            print(f"Updating config for agent {agent_id}. Note: This does not automatically update live object pools based on this agent's config yet.")
        for key, value in update_data.items():
            setattr(agent, key, value)
        agent.updated_at = datetime.utcnow()
        agent.status = AgentStatus.UPDATED
        db_agents[agent_id] = agent
        return agent
    return None

def delete_agent(agent_id: uuid.UUID) -> Optional[Agent]:
    # Before deleting an agent, consider if its dedicated pool (if any) needs cleanup.
    # Current global pools are not per-agent, but per-agent-type.
    # If pools were per-agent_id, this would be the place to destroy them.
    if agent_id in db_agents:
        agent_info = db_agents[agent_id]
        print(f"Deleting agent {agent_info.name} (ID: {agent_id}). Associated executions will also be removed.")
        if agent_id in db_executions:
            del db_executions[agent_id]
        return db_agents.pop(agent_id)
    return None

def create_agent_execution(agent_id: uuid.UUID, execution_create: ExecutionCreate) -> Optional[Execution]:
    agent_model = get_agent(agent_id) # Renamed from 'agent' to 'agent_model' to avoid var name clash
    if not agent_model:
        return None

    execution = Execution(
        **execution_create.model_dump(),
        execution_id=uuid.uuid4(),
        agent_id=agent_id,
        status=ExecutionStatus.PENDING,
        submitted_at=datetime.utcnow()
    )
    db_executions[agent_id][execution.execution_id] = execution

    print(f"Agent '{agent_model.name}' (ID: {agent_id}, Type: {agent_model.agent_type}) received execution request {execution.execution_id}.")
    print(f"Execution Parameters: {execution.parameters}")
    print(f"Agent Configuration: {agent_model.config}")


    # Simulate execution start for now
    execution.started_at = datetime.utcnow()
    execution.status = ExecutionStatus.RUNNING

    actual_agent_instance = None # To hold the acquired agent

    try:
        if agent_model.agent_type == AgentType.A2A:
            # Acquire from A2A pool. Pass agent's specific config for this execution.
            print(f"Acquiring A2A agent from pool for agent_id {agent_id} with config {agent_model.config}")
            actual_agent_instance = a2a_agent_pool.acquire(config_override=agent_model.config)
            result = actual_agent_instance.execute(execution.parameters)
            execution.result = result
            execution.status = ExecutionStatus.COMPLETED
            print(f"A2A execution for {execution.execution_id} completed. Result: {result}")

        elif agent_model.agent_type == AgentType.ADK:
            # Acquire from ADK pool. Pass agent's specific config.
            print(f"Acquiring ADK agent from pool for agent_id {agent_id} with config {agent_model.config}")
            actual_agent_instance = adk_agent_pool.acquire(config_override=agent_model.config)
            result = actual_agent_instance.execute(execution.parameters)
            execution.result = result
            execution.status = ExecutionStatus.COMPLETED
            print(f"ADK execution for {execution.execution_id} completed. Result: {result}")

        elif agent_model.agent_type == AgentType.FINANCIAL_HOST:
            print(f"Acquiring Financial Host agent from pool for agent_id {agent_id} with config {agent_model.config}")
            # Pass the agent's specific config, which might override pool defaults
            actual_agent_instance = financial_host_agent_pool.acquire(config_override=agent_model.config)

            input_text = execution.parameters.get("input_text")
            if not input_text:
                raise ValueError("Missing 'input_text' in parameters for Financial Host agent execution.")

            # THIS IS A TEMPORARY SYNCHRONOUS PLACEHOLDER.
            # In a real scenario, `create_agent_execution` would need to be async
            # or use `asyncio.run` to execute the ADK agent's async methods.
            print(f"Executing Financial Host agent with input: '{input_text}'. This part is a placeholder for async execution.")
            # Simulate what might happen: ADK agent processes the input.
            # The actual call would be something like:
            # adk_response_stream = await actual_agent_instance.invoke_async(input_text)
            # final_response_text = ""
            # async for item in adk_response_stream:
            #   if item.text_content:
            #       final_response_text += item.text_content
            # result = {"output_text": final_response_text}

            # For now, a mock response as the async integration is complex here:
            result = {
                "status": "simulated_success",
                "message": f"Financial Host Agent processed (simulated): {input_text}",
                "notes": "This execution is a synchronous placeholder for an async ADK agent."
            }
            execution.result = result
            execution.status = ExecutionStatus.COMPLETED
            print(f"Financial Host execution for {execution.execution_id} (simulated) completed. Result: {result}")

        elif agent_model.agent_type == AgentType.MCP or agent_model.agent_type == AgentType.CUSTOM:
            # Placeholder for MCP and CUSTOM agents - current direct simulation
            print(f"Simulating execution for {agent_model.agent_type.value} agent '{agent_model.name}'.")
            # Simulate some processing
            simulated_result = {
                "message": f"{agent_model.agent_type.value} agent '{agent_model.name}' processed parameters.",
                "received_params": execution.parameters,
                "agent_config": agent_model.config
            }
            execution.result = simulated_result
            execution.status = ExecutionStatus.COMPLETED
            print(f"Simulated execution for {execution.execution_id} completed. Result: {simulated_result}")
        else:
            error_message = f"Unsupported agent type: {agent_model.agent_type}"
            print(error_message)
            execution.status = ExecutionStatus.FAILED
            execution.error = error_message

    except Exception as e:
        error_message = f"Execution failed for agent {agent_model.name}: {str(e)}"
        print(error_message)
        execution.status = ExecutionStatus.FAILED
        execution.error = error_message
    finally:
        if actual_agent_instance:
            # Release the agent back to its pool
            if agent_model.agent_type == AgentType.A2A:
                a2a_agent_pool.release(actual_agent_instance)
                print(f"Released A2A agent instance. Pool size: {a2a_agent_pool.get_pool_size()}")
            elif agent_model.agent_type == AgentType.ADK:
                adk_agent_pool.release(actual_agent_instance)
                print(f"Released ADK agent instance. Pool size: {adk_agent_pool.get_pool_size()}")
            elif agent_model.agent_type == AgentType.FINANCIAL_HOST and actual_agent_instance:
                financial_host_agent_pool.release(actual_agent_instance)
                print(f"Released Financial Host agent instance. Pool size: {financial_host_agent_pool.get_pool_size()}")

        execution.completed_at = datetime.utcnow()

    return execution

def get_agent_execution(agent_id: uuid.UUID, execution_id: uuid.UUID) -> Optional[Execution]:
    if agent_id in db_executions and execution_id in db_executions[agent_id]:
        return db_executions[agent_id][execution_id]
    return None

def list_agent_executions(agent_id: uuid.UUID) -> List[Execution]:
     if agent_id in db_executions:
         return list(db_executions[agent_id].values())
     return []
