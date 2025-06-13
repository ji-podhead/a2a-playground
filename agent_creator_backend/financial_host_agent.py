import os
import uuid
import httpx
import json
from typing import Dict, Any, Optional

from a2a.types import Message, Part # For constructing A2A messages
from google.adk import Agent as ADKAgent
from google.adk.tools import tool
from google.adk.tools.tool_context import ToolContext

AGENT_NAME = "FinancialHostAgent"
AGENT_DESCRIPTION = "Orchestrates financial analysis tasks and interacts with the user."

# Gemini model for the host agent's intelligence
HOST_AGENT_MODEL = os.getenv("HOST_AGENT_MODEL", "gemini-1.5-flash-latest")


class FinancialHostLogicAgent(ADKAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name=AGENT_NAME,
            model=HOST_AGENT_MODEL, # This could also come from config
            instruction=self._get_host_instruction()
        )
        self.description = AGENT_DESCRIPTION

        # Default URLs
        self.analysis_loop_agent_url = "http://mock_analysis_loop_agent:8005"
        self.pg_interface_agent_url = "http://mock_pg_interface_agent:8001"
        self.fin_interface_agent_url = "http://mock_fin_interface_agent:8002"
        self.shopping_agent_url = "http://mock_shopping_agent:8007"
        self.host_agent_model = HOST_AGENT_MODEL # Default

        if config:
            self.analysis_loop_agent_url = config.get("ANALYSIS_LOOP_AGENT_URL", self.analysis_loop_agent_url)
            self.pg_interface_agent_url = config.get("PG_INTERFACE_AGENT_URL", self.pg_interface_agent_url)
            self.fin_interface_agent_url = config.get("FIN_INTERFACE_AGENT_URL", self.fin_interface_agent_url)
            self.shopping_agent_url = config.get("SHOPPING_AGENT_URL", self.shopping_agent_url)
            self.host_agent_model = config.get("HOST_AGENT_MODEL", self.host_agent_model)
            # Update the ADKAgent's model if overridden
            self.model = self.host_agent_model


        self.add_tool(self.start_stock_analysis)
        self.add_tool(self.stop_stock_analysis)
        self.add_tool(self.get_analysis_loop_status)
        self.add_tool(self.get_latest_prediction)
        self.add_tool(self.query_database)
        self.add_tool(self.fetch_financial_data)
        self.add_tool(self.view_shop_catalog)
        self.add_tool(self.add_item_to_cart)
        self.add_tool(self.view_shopping_cart)
        self.add_tool(self.checkout_cart)
        self.add_tool(self.get_shopping_balance)

        self._a2a_client = httpx.AsyncClient(timeout=60.0)
        print(f"[{AGENT_NAME}] Initialized. Model: {self.model}")
        print(f"[{AGENT_NAME}] Downstream Agents: Analysis->{self.analysis_loop_agent_url}, PG->{self.pg_interface_agent_url}, Fin->{self.fin_interface_agent_url}, Shop->{self.shopping_agent_url}")

    async def release(self):
        print(f"[{self.name}] Releasing financial host agent resources (if any).")
        # If there were specific resources to clean up per-instance before pooling,
        # they would go here. For now, it's mainly for demonstration.
        # The self._a2a_client is an async client, its lifecycle is tricky with sync pooling.
        # For now, we won't close it here as it's shared or would need async pool.
        # await self.close_clients() # This would be ideal with an async pool
        print(f"[{self.name}] Instance ready to be pooled.")

    def _get_host_instruction(self) -> str:
        # Instructions for the LLM
        return """
        You are a sophisticated Financial Insights Assistant. Your role is to help users by managing stock analysis tasks and retrieving financial data or predictions.

        Available actions:
        1.  **Start Stock Analysis**:
            *   If the user asks to "analyze [STOCK_SYMBOL]", "start predictions for [STOCK_SYMBOL]", or similar.
            *   You MUST get the stock symbol from the user.
            *   Then, call the  tool with the .
            *   Inform the user that the analysis loop has been started.

        2.  **Stop Stock Analysis**:
            *   If the user asks to "stop analysis", "stop predictions", or similar.
            *   Call the  tool.
            *   Inform the user that the stop command has been issued.

        3.  **Check Analysis Status**:
            *   If the user asks "what's being analyzed?", "is the analysis running?", or similar.
            *   Call the  tool.
            *   Relay the status (running or not, and which symbol) to the user.

        4.  **Get Latest Prediction**:
            *   If the user asks for "latest prediction for [STOCK_SYMBOL]", "what's the forecast for [STOCK_SYMBOL]?".
            *   You MUST get the stock symbol.
            *   Call the  tool with the .
            *   Present the fetched prediction (or "no prediction found") to the user.

        5.  **Query Database (Advanced)**:
            *   If the user asks a specific question that requires querying stored market data or predictions directly using SQL (e.g., "show me the last 3 predictions for AAPL", "get all stored market data for TSLA today").
            *   You MUST formulate a valid SQL query for the  or  tables.
                *    columns: id, symbol, timestamp, data_source, raw_data (JSONB)
                *    columns: id, symbol, prediction_timestamp, prediction_type, predicted_value, notes, raw_input_summary (JSONB)
            *   Call the  tool with the .
            *   Present the results clearly. If  is complex, summarize it or inform the user.

        6.  **Fetch Financial Data (Advanced)**:
            *   If the user asks for specific financial data that maps to a tool in the Financial Data Interface Agent (e.g., "get technical analysis for GOOGL", "show volume profile for MSFT").
            *   Determine the correct  (e.g., "GetStockTechnicalAnalysis", "GetStockVolumeProfile") and  (as a JSON string).
            *   Call the  tool.
            *   Present the results.

        General Rules:
        *   Be polite and informative.
        *   If a stock symbol is needed and not provided, ALWAYS ask the user for it.
        *   Do not make up information. Rely on the tools.
        *   If a tool call fails, inform the user about the error.

        7.  **View Shopping Catalog**:
            *   If the user asks to "see items for sale", "show me the catalog", "what can I buy?".
            *   Call the `view_shop_catalog` tool.
            *   Present the catalog to the user.

        8.  **Add Item to Cart**:
            *   If the user asks to "add [ITEM_NAME] to cart", "buy [QUANTITY] of [ITEM_NAME]", or similar.
            *   You MUST obtain the `item_name` they want to add. This should be one of the items listed in the shop catalog. If unsure, you can ask the user to view the catalog first.
            *   You MUST obtain the `quantity`. If not specified by the user, assume a quantity of 1.
            *   Call the `add_item_to_cart` tool with the `item_name` and `quantity` parameters.
            *   Inform the user about the result (e.g., item added, or error if item not found or invalid quantity).

        9.  **View Shopping Cart**:
            *   If the user asks "what's in my cart?", "show my shopping cart", "current order".
            *   Call the `view_shopping_cart` tool.
            *   Display cart contents and total cost.

        10. **Checkout Cart**:
            *   If the user asks to "checkout", "buy my items", "complete purchase".
            *   Call the `checkout_cart` tool.
            *   Report success (new balance, items bought) or failure (e.g., insufficient funds).

        11. **Get Shopping Balance**:
            *   If the user asks "what's my shopping balance?", "how much virtual money do I have?".
            *   Call the `get_shopping_balance` tool.
            *   Inform the user of their virtual balance.
        """

    async def _call_downstream_a2a_tool(self, agent_base_url: str, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        message_id = uuid.uuid4().hex
        task_id = uuid.uuid4().hex
        a2a_message = Message(
            message_id=message_id, role="agent",
            parts=[Part(tool_code={"name": tool_name, "args": tool_args})],
            task_id=task_id
        )
        try:
            print(f"[{AGENT_NAME}] Calling A2A: {agent_base_url}/messages, tool: {tool_name}, args: {tool_args}")
            response = await self._a2a_client.post(f"{agent_base_url}/messages", json=a2a_message.model_dump(exclude_none=True))
            response.raise_for_status()
            response_data = response.json()
            if response_data and response_data.get("parts"):
                for part_data in response_data["parts"]:
                    if "tool_data" in part_data:
                        return {"status": "success", "data": part_data["tool_data"]}
                    if "error" in part_data: # A2A ErrorResponse object
                        err_msg = part_data["error"].get("message", "Unknown error from downstream agent")
                        print(f"ERROR from downstream agent: {err_msg}")
                        return {"status": "error", "error": err_msg}
            return {"status": "error", "error": "Malformed or empty response from downstream agent", "raw_response": response_data}
        except httpx.HTTPStatusError as e:
            err_text = e.response.text
            print(f"ERROR: HTTP error {e.response.status_code} calling {agent_base_url}: {err_text}")
            return {"status": "error", "error": f"HTTP error {e.response.status_code}: {err_text}"}
        except Exception as e:
            print(f"ERROR: Exception calling {agent_base_url}: {str(e)}")
            return {"status": "error", "error": f"Exception: {str(e)}"}

    @tool()
    async def start_stock_analysis(self, stock_symbol: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Starts the analysis loop for the given stock symbol via the AnalysisLoopAgent."""
        return await self._call_downstream_a2a_tool(self.analysis_loop_agent_url, "StartAnalysisLoop", {"stock_symbol": stock_symbol})

    @tool()
    async def stop_stock_analysis(self, tool_context: ToolContext) -> Dict[str, Any]:
        """Stops the analysis loop via the AnalysisLoopAgent."""
        return await self._call_downstream_a2a_tool(self.analysis_loop_agent_url, "StopAnalysisLoop", {})

    @tool()
    async def get_analysis_loop_status(self, tool_context: ToolContext) -> Dict[str, Any]:
        """Gets the status of the analysis loop from the AnalysisLoopAgent."""
        return await self._call_downstream_a2a_tool(self.analysis_loop_agent_url, "GetAnalysisStatus", {})

    @tool()
    async def get_latest_prediction(self, stock_symbol: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Fetches the latest prediction for a stock symbol from the database via PgInterfaceAgent."""
        sql = f"SELECT prediction_timestamp, prediction_type, predicted_value, notes FROM stock_predictions WHERE symbol = '{stock_symbol.upper()}' ORDER BY prediction_timestamp DESC LIMIT 1"
        response = await self._call_downstream_a2a_tool(self.pg_interface_agent_url, "ExecuteSQLQuery", {"sql_query": sql})
        if response.get("status") == "success" and response.get("data", {}).get("results"):
            return {"status": "success", "prediction": response["data"]["results"][0]}
        elif response.get("status") == "success": # Success but no results
             return {"status": "success", "prediction": "No prediction found for this symbol."}
        return response # Error or other status

    @tool()
    async def query_database(self, sql_query: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Executes a given SQL query via the PgInterfaceAgent."""
        return await self._call_downstream_a2a_tool(self.pg_interface_agent_url, "ExecuteSQLQuery", {"sql_query": sql_query})

    @tool()
    async def fetch_financial_data(self, fin_tool_name: str, tool_arguments: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Fetches financial data by calling a specified tool on the FinInterfaceAgent."""
        try:
            args_dict = json.loads(tool_arguments)
        except json.JSONDecodeError:
            return {"status": "error", "error": "Invalid JSON format for tool_arguments."}
        return await self._call_downstream_a2a_tool(self.fin_interface_agent_url, fin_tool_name, args_dict)

    @tool()
    async def view_shop_catalog(self, tool_context: ToolContext) -> Dict[str, Any]:
        """Displays the available virtual items from the shopping catalog."""
        return await self._call_downstream_a2a_tool(self.shopping_agent_url, "view_catalog", {})

    @tool()
    async def add_item_to_cart(self, item_name: str, quantity: int, tool_context: ToolContext) -> Dict[str, Any]:
        """Adds a specified quantity of an item to the virtual shopping cart."""
        user_id = "default_fin_user"
        return await self._call_downstream_a2a_tool(self.shopping_agent_url, "add_to_cart", {"user_id": user_id, "item_name": item_name, "quantity": quantity})

    @tool()
    async def view_shopping_cart(self, tool_context: ToolContext) -> Dict[str, Any]:
        """Shows the current items in the shopping cart and the total cost."""
        user_id = "default_fin_user"
        return await self._call_downstream_a2a_tool(self.shopping_agent_url, "view_cart", {"user_id": user_id})

    @tool()
    async def checkout_cart(self, tool_context: ToolContext) -> Dict[str, Any]:
        """Simulates purchasing all items currently in the shopping cart."""
        user_id = "default_fin_user"
        return await self._call_downstream_a2a_tool(self.shopping_agent_url, "checkout", {"user_id": user_id})

    @tool()
    async def get_shopping_balance(self, tool_context: ToolContext) -> Dict[str, Any]:
        """Fetches the virtual shopping fund balance for the current user."""
        user_id = "default_fin_user"
        return await self._call_downstream_a2a_tool(self.shopping_agent_url, "get_virtual_balance", {"user_id": user_id})

    async def close_clients(self):
        if self._a2a_client and not self._a2a_client.is_closed:
            await self._a2a_client.aclose()
