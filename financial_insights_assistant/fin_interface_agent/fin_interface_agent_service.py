import os
import uuid
import httpx # For making requests to mcp-trader
import json
from typing import Dict, Any, Optional, List

from a2a.types import (
    AgentCard,
    Tool,
    ToolInputSchema,
    ToolOutputSchema,
    Property,
)
from google.adk import Agent as ADKAgent
from google.adk.tools import tool
from google.adk.agents.context import ReadonlyContext # Not used here but good for consistency
from google.adk.tools.tool_context import ToolContext # Not used here but good for consistency

AGENT_NAME = "FinancialDataInterfaceAgent"
AGENT_DESCRIPTION = "Provides an A2A interface to financial market data and analysis via an mcp-trader server."
AGENT_VERSION = "0.1.0"
AGENT_ID = uuid.uuid4().hex

# Environment variable for the mcp-trader server URL
MCP_TRADER_URL = os.getenv("MCP_TRADER_URL", "http://mcp_trader_server_container:8000") # Default for Docker Compose

FIN_INTERFACE_AGENT_CARD = AgentCard(
    id=AGENT_ID,
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version=AGENT_VERSION,
    publisher="FinancialInsightsAssistant",
    tools=[
        Tool(
            id="get_stock_technical_analysis",
            name="GetStockTechnicalAnalysis",
            description="Performs technical analysis on a given stock symbol using mcp-trader's 'analyze-stock' tool.",
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "symbol": Property(type="string", description="The stock symbol (e.g., 'NVDA').")
                },
                required=["symbol"],
            ),
            # Output schema should ideally match what mcp-trader's 'analyze-stock' returns.
            # This is a generic placeholder; actual structure depends on mcp-trader.
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "status": Property(type="string", description="Status of the operation."),
                    "analysis_data": Property(type="object", description="The technical analysis data from mcp-trader.", additional_properties_type=True),
                    "error": Property(type="string", description="Error message if failed.")
                }
            ),
        ),
        Tool(
            id="get_stock_volume_profile",
            name="GetStockVolumeProfile",
            description="Analyzes volume distribution by price for a stock using mcp-trader's 'volume-profile' tool.",
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "symbol": Property(type="string", description="The stock symbol (e.g., 'MSFT')."),
                    "lookback_days": Property(type="integer", description="Number of days to look back (default: 60).", default=60)
                },
                required=["symbol"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "status": Property(type="string", description="Status of the operation."),
                    "volume_profile_data": Property(type="object", description="The volume profile data from mcp-trader.", additional_properties_type=True),
                    "error": Property(type="string", description="Error message if failed.")
                }
            ),
        ),
        Tool(
            id="get_stock_relative_strength",
            name="GetStockRelativeStrength",
            description="Calculates a stock's relative strength compared to a benchmark using mcp-trader's 'relative-strength' tool.",
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "symbol": Property(type="string", description="The stock symbol (e.g., 'AAPL')."),
                    "benchmark": Property(type="string", description="Benchmark symbol (default: 'SPY').", default="SPY")
                },
                required=["symbol"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "status": Property(type="string", description="Status of the operation."),
                    "relative_strength_data": Property(type="object", description="The relative strength data from mcp-trader.", additional_properties_type=True),
                    "error": Property(type="string", description="Error message if failed.")
                }
            ),
        )
        # Add more tools here corresponding to other mcp-trader tools if desired.
    ]
)

class FinancialDataInterfaceAgent(ADKAgent):
    def __init__(self):
        super().__init__(name=AGENT_NAME, instruction="You are a financial data interface agent.")
        self.description = AGENT_DESCRIPTION
        self.add_tool(self.get_stock_technical_analysis)
        self.add_tool(self.get_stock_volume_profile)
        self.add_tool(self.get_stock_relative_strength)
        self.http_client = httpx.AsyncClient(base_url=MCP_TRADER_URL, timeout=60.0) # Increased timeout for potentially long analyses
        print(f"[{AGENT_NAME}] Initialized. Will connect to mcp-trader at: {MCP_TRADER_URL}")

    async def _call_mcp_trader_tool(self, mcp_tool_name: str, mcp_arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Helper function to call a tool on the mcp-trader server."""
        request_payload = {
            "name": mcp_tool_name, # Tool name expected by mcp-trader
            "arguments": mcp_arguments
        }
        try:
            print(f"[{AGENT_NAME}] Calling mcp-trader tool '{mcp_tool_name}' with args: {mcp_arguments}")
            # mcp-trader docs say its HTTP endpoint is /call-tool
            response = await self.http_client.post("/call-tool", json=request_payload)
            response.raise_for_status()
            mcp_response = response.json() # mcp-trader returns an array of content items
            print(f"[{AGENT_NAME}] Response from mcp-trader: {mcp_response}")

            # mcp-trader returns a list of "content items". We need to parse this.
            # For simplicity, we'll assume the relevant data is in the first item, often in 'text' or 'data'.
            # A more robust parser would iterate through items and handle different types (text, images).
            if isinstance(mcp_response, list) and mcp_response:
                # Let's try to find a part that is likely the main data.
                # This is heuristic. Ideally, mcp-trader tools would have a more predictable structured output.
                extracted_data = {}
                text_parts = []
                for item in mcp_response:
                    if isinstance(item, dict):
                        if "text" in item: # Often, analysis results are in text parts
                             text_parts.append(item["text"])
                        if "data" in item: # If there's a specific 'data' field
                            if isinstance(item["data"], dict):
                                extracted_data.update(item["data"])
                            else:
                                extracted_data["raw_data"] = item["data"]

                if not extracted_data and text_parts: # If no 'data' field, combine text parts
                    # Attempt to parse combined text if it looks like JSON, otherwise return as string
                    full_text = "\n".join(text_parts)
                    try:
                        extracted_data = json.loads(full_text)
                    except json.JSONDecodeError:
                         # If it's not JSON, it might be a formatted string report.
                         # The  tool in mcp-trader returns a formatted string.
                        extracted_data = {"report": full_text}


                if not extracted_data and not text_parts: # If nothing useful found
                    return {"status": "success_empty_response_from_mcp", "raw_mcp_response": mcp_response}

                return {"status": "success", "data": extracted_data}
            elif isinstance(mcp_response, dict): # If it's a dict, maybe it's already structured
                return {"status": "success", "data": mcp_response}
            else:
                return {"status": "error", "error": "Unexpected response format from mcp-trader", "raw_mcp_response": mcp_response}

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error calling mcp-trader: {e.response.status_code} - {e.response.text}"
            print(f"ERROR: {error_msg}")
            return {"status": "error", "error": error_msg}
        except Exception as e:
            error_msg = f"Error calling mcp-trader: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {"status": "error", "error": error_msg}

    @tool()
    async def get_stock_technical_analysis(self, symbol: str, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        response = await self._call_mcp_trader_tool(mcp_tool_name="analyze-stock", mcp_arguments={"symbol": symbol})
        if response.get("status") == "success":
            return {"status": "success", "analysis_data": response.get("data")}
        return response # Pass through error or other statuses

    @tool()
    async def get_stock_volume_profile(self, symbol: str, lookback_days: int = 60, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        args = {"symbol": symbol}
        if lookback_days != 60: # Only include if not default, mcp-trader uses default if not provided
            args["lookback_days"] = lookback_days
        response = await self._call_mcp_trader_tool(mcp_tool_name="volume-profile", mcp_arguments=args)
        if response.get("status") == "success":
            return {"status": "success", "volume_profile_data": response.get("data")}
        return response

    @tool()
    async def get_stock_relative_strength(self, symbol: str, benchmark: str = "SPY", tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        args = {"symbol": symbol}
        if benchmark != "SPY": # Only include if not default
            args["benchmark"] = benchmark
        response = await self._call_mcp_trader_tool(mcp_tool_name="relative-strength", mcp_arguments=args)
        if response.get("status") == "success":
            return {"status": "success", "relative_strength_data": response.get("data")}
        return response

fin_interface_adk_agent = FinancialDataInterfaceAgent()
