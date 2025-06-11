from fastapi import FastAPI
import uvicorn
import os

from fin_interface_agent.fin_interface_agent_service import FIN_INTERFACE_AGENT_CARD, fin_interface_adk_agent
from a2a.types import AgentCard
from google.adk.runners.fastapi_runner import create_fastapi_runner

app = FastAPI(
    title=FIN_INTERFACE_AGENT_CARD.name,
    version=FIN_INTERFACE_AGENT_CARD.version,
    description=FIN_INTERFACE_AGENT_CARD.description,
)

@app.get("/agent.json", response_model=AgentCard)
async def get_agent_card():
    return FIN_INTERFACE_AGENT_CARD

adk_runner_router = create_fastapi_runner(fin_interface_adk_agent)
app.include_router(adk_runner_router, prefix="") # Mount at root for /messages

if __name__ == "__main__":
    port = int(os.getenv("FIN_INTERFACE_AGENT_PORT", "8002"))
    host = os.getenv("FIN_INTERFACE_AGENT_HOST", "0.0.0.0")
    print(f"Starting Financial Data Interface Agent on {host}:{port}...")
    uvicorn.run(app, host=host, port=port)
