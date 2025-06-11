from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
import uvicorn
import os
import uuid # ensure uuid is imported

# Adjust import path based on execution context (e.g., running uvicorn from project root)
from flight_agent.flight_agent_service import FLIGHT_AGENT_CARD, handle_a2a_message, flight_adk_agent
from a2a.types import Message, Part, ErrorResponse # Ensure Message is imported for type hinting

# Initialize FastAPI app
app = FastAPI(
    title=FLIGHT_AGENT_CARD.name,
    version=FLIGHT_AGENT_CARD.version,
    description=FLIGHT_AGENT_CARD.description,
)

@app.get("/agent.json", response_model=AgentCard) # AgentCard needs to be imported from a2a.types
async def get_agent_card(): # Add AgentCard to imports in flight_agent_service.py for this to be valid
    from a2a.types import AgentCard # Local import if not top-level in service
    return FLIGHT_AGENT_CARD

@app.post("/messages", response_model=Message) # A2A response is a Message
async def process_message(message: Message = Body(...)): # A2A request is a Message
    """
    Handles incoming A2A messages.
    It expects a message containing a tool_code part for the SearchFlights tool.
    """
    print(f"[/messages endpoint] Received message: {message.message_id}")
    try:
        response_message = await handle_a2a_message(message)
        return response_message
    except Exception as e:
        print(f"Error in /messages endpoint: {e}")
        # Return a valid A2A error message structure
        error_part = Part(error=ErrorResponse(code="InternalServerError", message=str(e)))
        return Message(
            message_id=uuid.uuid4().hex,
            role="agent",
            parts=[error_part],
            task_id=message.task_id, # Try to echo task_id if available
            context_id=message.context_id # Try to echo context_id if available
        )

# ADK Runner endpoint (optional, if you want to expose ADK directly too)
# from google.adk.runners.fastapi_runner import create_fastapi_runner
# adk_runner_router = create_fastapi_runner(flight_adk_agent)
# app.include_router(adk_runner_router, prefix="/adk")


if __name__ == "__main__":
    port = int(os.getenv("FLIGHT_AGENT_PORT", "8001")) # Default to 8001 if not set
    print(f"Starting Flight Specialist Agent on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
