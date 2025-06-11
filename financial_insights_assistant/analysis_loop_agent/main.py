from fastapi import FastAPI
import uvicorn
import os

from analysis_loop_agent.analysis_loop_agent_service import ANALYSIS_AGENT_CARD, analysis_loop_adk_agent, on_shutdown as agent_on_shutdown
from a2a.types import AgentCard
from google.adk.runners.fastapi_runner import create_fastapi_runner

app = FastAPI(
    title=ANALYSIS_AGENT_CARD.name,
    version=ANALYSIS_AGENT_CARD.version,
    description=ANALYSIS_AGENT_CARD.description,
    on_shutdown=[agent_on_shutdown] # Register the agent's cleanup function
)

@app.get("/agent.json", response_model=AgentCard)
async def get_agent_card():
    return ANALYSIS_AGENT_CARD

adk_runner_router = create_fastapi_runner(analysis_loop_adk_agent)
app.include_router(adk_runner_router, prefix="")

if __name__ == "__main__":
    port = int(os.getenv("ANALYSIS_LOOP_AGENT_PORT", "8005")) # Using a different port, e.g. 8005
    host = os.getenv("ANALYSIS_LOOP_AGENT_HOST", "0.0.0.0")
    print(f"Starting Looping Analysis Agent on {host}:{port}...")
    uvicorn.run(app, host=host, port=port)
