from fastapi import FastAPI, Body
import uvicorn
import os
import uuid

from pg_interface_agent.pg_interface_agent_service import PG_INTERFACE_AGENT_CARD, pg_interface_adk_agent
from a2a.types import AgentCard, Message, Part, ErrorResponse # A2A types for request/response

from google.adk.runners.fastapi_runner import create_fastapi_runner # For ADK agent serving

# Initialize FastAPI app
app = FastAPI(
    title=PG_INTERFACE_AGENT_CARD.name,
    version=PG_INTERFACE_AGENT_CARD.version,
    description=PG_INTERFACE_AGENT_CARD.description,
)

@app.get("/agent.json", response_model=AgentCard)
async def get_agent_card():
    """Serves the agent's card."""
    return PG_INTERFACE_AGENT_CARD

# Use ADK's FastAPI runner to handle /messages and other ADK interactions
# This simplifies routing A2A messages to the ADK agent's tools
adk_runner_router = create_fastapi_runner(pg_interface_adk_agent)
app.include_router(adk_runner_router, prefix="") # Mount at root for /messages

# Fallback /messages if not using ADK runner directly or for custom handling
# @app.post("/messages", response_model=Message)
# async def process_message(message: Message = Body(...)):
#     # This endpoint would be manually implemented if not using create_fastapi_runner
#     # It would involve:
#     # 1. Parsing the message.parts for tool_code.
#     # 2. Finding the corresponding tool in pg_interface_adk_agent.
#     # 3. Executing the tool with tool_code.args.
#     # 4. Formatting the tool's output into an A2A Message with tool_data or error.
#     print(f"[/messages endpoint for PG Interface] Received message: {message.message_id}")
#     # ... manual tool dispatch and A2A response construction ...
#     # For now, relying on ADK runner.
#     error_part = Part(error=ErrorResponse(code="NotImplemented", message="/messages endpoint direct handling not implemented, use ADK runner."))
#     return Message(message_id=uuid.uuid4().hex, role="agent", parts=[error_part])


if __name__ == "__main__":
    # Port for this agent, e.g., 8001. Should be configurable for Docker.
    port = int(os.getenv("PG_INTERFACE_AGENT_PORT", "8001"))
    host = os.getenv("PG_INTERFACE_AGENT_HOST", "0.0.0.0")
    print(f"Starting PostgreSQL Interface Agent on {host}:{port}...")
    uvicorn.run(app, host=host, port=port)
