import os
import uuid
import httpx
import json
import asyncio
import datetime
import traceback # Added for error logging
from typing import Dict, Any, Optional

from a2a.types import (
    AgentCard,
    Tool,
    ToolInputSchema,
    ToolOutputSchema,
    Property,
    Message,
    Part
)
from google.adk import Agent as ADKAgent
from google.adk.tools import tool
from google.adk.tools.tool_context import ToolContext

AGENT_NAME = "LoopingAnalysisAgent"
AGENT_DESCRIPTION = "Performs continuous analysis of a specified stock, fetching data, storing it, and generating predictions."
AGENT_VERSION = "0.1.0"
AGENT_ID = uuid.uuid4().hex

# URLs for dependent A2A services (from environment variables)
FIN_INTERFACE_AGENT_URL = os.getenv("FIN_INTERFACE_AGENT_URL", "http://fin_interface_agent_service:8002")
PG_INTERFACE_AGENT_URL = os.getenv("PG_INTERFACE_AGENT_URL", "http://pg_interface_agent_service:8001")
LOOP_SLEEP_INTERVAL_SECONDS = int(os.getenv("ANALYSIS_LOOP_SLEEP_INTERVAL_SECONDS", "60")) # Default to 1 minute

ANALYSIS_AGENT_CARD = AgentCard(
    id=AGENT_ID,
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version=AGENT_VERSION,
    publisher="FinancialInsightsAssistant",
    tools=[
        Tool(
            id="start_analysis_loop",
            name="StartAnalysisLoop",
            description="Starts the continuous analysis loop for a given stock symbol.",
            input_schema=ToolInputSchema(
                type="object",
                properties={"stock_symbol": Property(type="string", description="The stock symbol to analyze (e.g., 'NVDA').")},
                required=["stock_symbol"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={"status": Property(type="string", description="Status of the start command.")}
            ),
        ),
        Tool(
            id="stop_analysis_loop",
            name="StopAnalysisLoop",
            description="Stops the currently running analysis loop.",
            output_schema=ToolOutputSchema(
                type="object",
                properties={"status": Property(type="string", description="Status of the stop command.")}
            ),
        ),
        Tool(
            id="get_analysis_status",
            name="GetAnalysisStatus",
            description="Gets the current status of the analysis loop.",
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "is_running": Property(type="boolean", description="True if the loop is currently active."),
                    "analyzing_symbol": Property(type="string", description="The stock symbol currently being analyzed, if any.")
                }
            ),
        )
    ]
)

class LoopingAnalysisAgent(ADKAgent):
    def __init__(self):
        super().__init__(name=AGENT_NAME, instruction="You manage a financial analysis loop.")
        self.description = AGENT_DESCRIPTION
        self.add_tool(self.start_analysis_loop)
        self.add_tool(self.stop_analysis_loop)
        self.add_tool(self.get_analysis_status)

        self._is_running = False
        self._current_stock_symbol: Optional[str] = None
        self._analysis_task: Optional[asyncio.Task] = None
        self._a2a_client = httpx.AsyncClient(timeout=45.0) # For calls to other agents
        print(f"[{AGENT_NAME}] Initialized. FIN_URL: {FIN_INTERFACE_AGENT_URL}, PG_URL: {PG_INTERFACE_AGENT_URL}")

    async def _call_a2a_agent_tool(self, agent_base_url: str, tool_name: str, tool_args: Dict) -> Dict[str, Any]:
        """Helper to make A2A call to another agent's tool via /messages endpoint."""
        message_id = uuid.uuid4().hex
        task_id = uuid.uuid4().hex # Each tool call can be a new task for the downstream agent

        a2a_message = Message(
            message_id=message_id,
            role="agent", # This agent is acting as a user to the downstream agent
            parts=[Part(tool_code={"name": tool_name, "args": tool_args})],
            task_id=task_id
        )

        try:
            print(f"[{AGENT_NAME}] Calling A2A: {agent_base_url}/messages, tool: {tool_name}, args: {tool_args}")
            response = await self._a2a_client.post(f"{agent_base_url}/messages", json=a2a_message.model_dump(exclude_none=True))
            response.raise_for_status()
            response_data = response.json() # Expecting A2A Message back

            # Extract tool_data or error from the response message
            if response_data and response_data.get("parts"):
                for part_data in response_data["parts"]:
                    if "tool_data" in part_data:
                        return {"status": "success", "data": part_data["tool_data"]}
                    if "error" in part_data:
                        return {"status": "error", "error": part_data["error"].get("message", "Unknown error from downstream agent")}
            return {"status": "error", "error": "Malformed response from downstream agent", "raw_response": response_data}
        except httpx.HTTPStatusError as e:
            return {"status": "error", "error": f"HTTP error {e.response.status_code} calling {agent_base_url}: {e.response.text}"}
        except Exception as e:
            return {"status": "error", "error": f"Exception calling {agent_base_url}: {str(e)}"}


    async def _analysis_loop_task(self, stock_symbol: str):
        print(f"[{AGENT_NAME}] Analysis loop started for symbol: {stock_symbol}")
        self._is_running = True
        self._current_stock_symbol = stock_symbol

        while self._is_running:
            try:
                print(f"[{AGENT_NAME} Loop] Iteration for {stock_symbol} at {datetime.datetime.now()}")

                # 1. Get stock analysis from Financial Data Interface Agent
                fin_agent_resp = await self._call_a2a_agent_tool(
                    agent_base_url=FIN_INTERFACE_AGENT_URL,
                    tool_name="GetStockTechnicalAnalysis", # Corresponds to tool ID in FinInterfaceAgent
                    tool_args={"symbol": stock_symbol}
                )

                market_data_to_store = None
                if fin_agent_resp.get("status") == "success" and fin_agent_resp.get("data"):
                    market_data_to_store = fin_agent_resp["data"].get("analysis_data", fin_agent_resp["data"])
                    print(f"[{AGENT_NAME} Loop] Fetched market data for {stock_symbol}: {json.dumps(market_data_to_store)[:200]}...")

                    # 2. Store market data via PostgreSQL Interface Agent
                    pg_store_market_resp = await self._call_a2a_agent_tool(
                        agent_base_url=PG_INTERFACE_AGENT_URL,
                        tool_name="InsertRecord", # Tool ID in PgInterfaceAgent
                        tool_args={
                            "table_name": "stock_market_data",
                            "data": {
                                "symbol": stock_symbol,
                                "timestamp": datetime.datetime.now().isoformat(), # Store fetch time
                                "data_source": "mcp-trader/GetStockTechnicalAnalysis", # Or the specific mcp-trader tool
                                "raw_data": market_data_to_store # Store the JSONB data
                            }
                        }
                    )
                    if pg_store_market_resp.get("status") == "success":
                        print(f"[{AGENT_NAME} Loop] Stored market data for {stock_symbol}.")
                    else:
                        print(f"ERROR [{AGENT_NAME} Loop] Failed to store market data for {stock_symbol}: {pg_store_market_resp.get('error')}")
                else:
                    print(f"ERROR [{AGENT_NAME} Loop] Failed to fetch market data for {stock_symbol}: {fin_agent_resp.get('error')}")
                    # Optionally continue or implement backoff

                # 3. Perform simple/mock prediction
                prediction_value = "mock_neutral"
                prediction_notes = f"Simple mock prediction for {stock_symbol}."
                if market_data_to_store: # Make a slightly more "informed" mock if data exists
                    # Example: if mcp-trader's 'analyze-stock' returns a report string
                    if isinstance(market_data_to_store, dict) and "report" in market_data_to_store:
                        if "bullish" in market_data_to_store["report"].lower(): prediction_value = "mock_bullish_trend"
                        elif "bearish" in market_data_to_store["report"].lower(): prediction_value = "mock_bearish_trend"
                    prediction_notes = f"Mock prediction based on fetched analysis for {stock_symbol} at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."


                # 4. Print prediction to console
                print(f"PREDICTION [{AGENT_NAME} Loop] Symbol: {stock_symbol}, Prediction: {prediction_value}, Notes: {prediction_notes}")

                # 5. Store prediction via PostgreSQL Interface Agent
                pg_store_pred_resp = await self._call_a2a_agent_tool(
                    agent_base_url=PG_INTERFACE_AGENT_URL,
                    tool_name="InsertRecord",
                    tool_args={
                        "table_name": "stock_predictions",
                        "data": {
                            "symbol": stock_symbol,
                            "prediction_timestamp": datetime.datetime.now().isoformat(),
                            "prediction_type": "simple_mock",
                            "predicted_value": prediction_value,
                            "notes": prediction_notes,
                            "raw_input_summary": {"source_data_timestamp": datetime.datetime.now().isoformat()} if market_data_to_store else None
                        }
                    }
                )
                if pg_store_pred_resp.get("status") == "success":
                    print(f"[{AGENT_NAME} Loop] Stored prediction for {stock_symbol}.")
                else:
                    print(f"ERROR [{AGENT_NAME} Loop] Failed to store prediction for {stock_symbol}: {pg_store_pred_resp.get('error')}")

            except Exception as e:
                print(f"ERROR [{AGENT_NAME} Loop] Unhandled exception in loop for {stock_symbol}: {e}")
                traceback.print_exc() # For detailed debugging

            if self._is_running: # Check again before sleeping
                await asyncio.sleep(LOOP_SLEEP_INTERVAL_SECONDS)
            else:
                break # Exit if stop was requested during processing

        print(f"[{AGENT_NAME}] Analysis loop gracefully stopped for symbol: {stock_symbol}")
        self._current_stock_symbol = None # Reset symbol when loop stops

    @tool()
    async def start_analysis_loop(self, stock_symbol: str, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        if self._is_running:
            if self._current_stock_symbol == stock_symbol:
                return {"status": f"Analysis loop already running for {stock_symbol}."}
            else:
                return {"status": f"Error: Analysis loop is busy with {self._current_stock_symbol}. Stop it first."}

        # Sanitize stock_symbol? (e.g., uppercase, length check) - for now, assume valid.
        print(f"[{AGENT_NAME}] Received start_analysis_loop command for: {stock_symbol}")
        self._analysis_task = asyncio.create_task(self._analysis_loop_task(stock_symbol))
        return {"status": f"Analysis loop initiated for {stock_symbol}."}

    @tool()
    async def stop_analysis_loop(self, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        print(f"[{AGENT_NAME}] Received stop_analysis_loop command.")
        if not self._is_running or not self._analysis_task:
            return {"status": "Analysis loop is not currently running."}

        self._is_running = False # Signal the loop to stop
        # Optionally, await the task with a timeout to ensure it finishes
        try:
            if self._analysis_task: # Check if task exists
                 # Do not await here directly as it can block the tool response.
                 # The loop itself will print when it stops.
                 # Consider adding a check in get_analysis_status if task is done.
                 print(f"[{AGENT_NAME}] Stop signal sent to loop for {self._current_stock_symbol}. Loop will terminate after current iteration.")
        except asyncio.CancelledError:
            print(f"[{AGENT_NAME}] Analysis task was cancelled externally.")
        except Exception as e:
            print(f"[{AGENT_NAME}] Error during task cleanup (it might have already finished): {e}")

        # self._analysis_task = None # Task object is cleared when it finishes or here
        # self._current_stock_symbol = None # Cleared by the loop itself
        return {"status": "Stop signal sent to analysis loop. It will terminate after its current iteration."}

    @tool()
    async def get_analysis_status(self, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        is_task_active = False
        if self._analysis_task and not self._analysis_task.done():
            is_task_active = True

        # Update _is_running if task has finished but flag not reset (e.g. due to an error in loop)
        if self._is_running and not is_task_active :
            self._is_running = False # Correct the state
            self._current_stock_symbol = None # Clear symbol if task is done

        return {
            "is_running": self._is_running and is_task_active, # Both flag and task active
            "analyzing_symbol": self._current_stock_symbol if (self._is_running and is_task_active) else None
        }

    # Graceful shutdown for the httpx client if the agent instance is destroyed
    async def __aenter__(self): # For context management if needed
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb): # For context management
        await self.close_clients()

    async def close_clients(self):
        if self._a2a_client and not self._a2a_client.is_closed:
            print(f"[{AGENT_NAME}] Closing A2A HTTP client...")
            await self._a2a_client.aclose()
            print(f"[{AGENT_NAME}] A2A HTTP client closed.")

# Instantiate the agent globally for ADK runner
analysis_loop_adk_agent = LoopingAnalysisAgent()

# Ensure client is closed on application shutdown (FastAPI specific)
async def on_shutdown():
    print(f"[{AGENT_NAME}] Application shutdown event received.")
    await analysis_loop_adk_agent.close_clients()
