from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
import uvicorn
import os
import uuid # ensure uuid is imported

from hotel_agent.hotel_agent_service import HOTEL_AGENT_CARD, handle_a2a_message, hotel_adk_agent
from a2a.types import Message, Part, ErrorResponse # Ensure all necessary types are imported

app = FastAPI(
    title=HOTEL_AGENT_CARD.name,
    version=HOTEL_AGENT_CARD.version,
    description=HOTEL_AGENT_CARD.description,
)

@app.get("/agent.json", response_model=AgentCard) # AgentCard needs to be imported from a2a.types
async def get_agent_card(): # Add AgentCard to imports in hotel_agent_service.py for this to be valid
    from a2a.types import AgentCard # Local import if not top-level in service
    return HOTEL_AGENT_CARD

@app.post("/messages", response_model=Message)
async def process_message(message: Message = Body(...)):
    print(f"[/messages endpoint] Received message: {message.message_id}")
    try:
        response_message = await handle_a2a_message(message)
        return response_message
    except Exception as e:
        print(f"Error in /messages endpoint: {e}")
        error_part = Part(error=ErrorResponse(code="InternalServerError", message=str(e)))
        return Message(
            message_id=uuid.uuid4().hex,
            role="agent",
            parts=[error_part],
            task_id=message.task_id,
            context_id=message.context_id
        )

# from google.adk.runners.fastapi_runner import create_fastapi_runner
# adk_runner_router = create_fastapi_runner(hotel_adk_agent)
# app.include_router(adk_runner_router, prefix="/adk")

if __name__ == "__main__":
    port = int(os.getenv("HOTEL_AGENT_PORT", "8002")) # Default to 8002
    print(f"Starting Hotel Specialist Agent on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
