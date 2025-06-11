import os
import uuid
import httpx # For making requests to postgres-mcp
import json
from typing import Dict, Any, Optional, List

from a2a.types import (
    AgentCard,
    Tool,
    ToolInputSchema,
    ToolOutputSchema,
    Property,
    Message, # For A2A message structure if directly handling
    Part,    # For A2A message structure
    ErrorResponse
)
from google.adk import Agent as ADKAgent
from google.adk.tools import tool
from google.adk.agents.context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext

AGENT_NAME = "PostgreSQLInterfaceAgent"
AGENT_DESCRIPTION = "Provides an A2A interface to interact with a PostgreSQL database via a postgres-mcp server."
AGENT_VERSION = "0.1.0"
AGENT_ID = uuid.uuid4().hex

# Environment variable for the postgres-mcp server URL
POSTGRES_MCP_URL = os.getenv("POSTGRES_MCP_URL", "http://postgres_mcp_server_container:8000") # Default for Docker Compose

PG_INTERFACE_AGENT_CARD = AgentCard(
    id=AGENT_ID,
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version=AGENT_VERSION,
    publisher="FinancialInsightsAssistant",
    tools=[
        Tool(
            id="execute_sql_query",
            name="ExecuteSQLQuery",
            description="Executes a given SQL query (primarily for SELECT statements) and returns the results.",
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "sql_query": Property(type="string", description="The SQL query to execute."),
                    "params": Property(type="object", description="Optional dictionary of parameters for the query.", additional_properties_type="string")
                },
                required=["sql_query"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "status": Property(type="string", description="Status of the operation (e.g., 'success', 'error')."),
                    "results": Property(type="array", description="Query results if successful, usually a list of dictionaries.", items={"type":"object"}),
                    "error": Property(type="string", description="Error message if the operation failed."),
                    "row_count": Property(type="integer", description="Number of rows affected or returned.")
                }
            ),
        ),
        Tool(
            id="execute_sql_update",
            name="ExecuteSQLUpdate",
            description="Executes a given SQL DML statement (INSERT, UPDATE, DELETE) and returns status.",
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "sql_query": Property(type="string", description="The SQL DML statement to execute."),
                    "params": Property(type="object", description="Optional dictionary of parameters for the query.", additional_properties_type="string")
                },
                required=["sql_query"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "status": Property(type="string", description="Status of the operation (e.g., 'success', 'error')."),
                    "row_count": Property(type="integer", description="Number of rows affected."),
                    "error": Property(type="string", description="Error message if the operation failed.")
                }
            ),
        ),
        Tool(
            id="insert_record",
            name="InsertRecord",
            description="Inserts a single record (dictionary) into a specified table.",
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "table_name": Property(type="string", description="The name of the table to insert into."),
                    "data": Property(type="object", description="A dictionary where keys are column names and values are the data to insert."),
                },
                required=["table_name", "data"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "status": Property(type="string", description="Status of the operation (e.g., 'success', 'error')."),
                    "record_id": Property(type="string", description="ID of the inserted record, if applicable/returned."),
                    "error": Property(type="string", description="Error message if the operation failed.")
                }
            ),
        )
    ]
)

class PostgreSQLInterfaceAgent(ADKAgent):
    def __init__(self):
        super().__init__(name=AGENT_NAME, instruction="You are a PostgreSQL interface agent.")
        self.description = AGENT_DESCRIPTION
        self.add_tool(self.execute_sql_query)
        self.add_tool(self.execute_sql_update)
        self.add_tool(self.insert_record)
        self.http_client = httpx.AsyncClient(base_url=POSTGRES_MCP_URL, timeout=30.0)
        print(f"[{AGENT_NAME}] Initialized. Will connect to postgres-mcp at: {POSTGRES_MCP_URL}")

    async def _call_postgres_mcp(self, mcp_tool_name: str, mcp_arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Helper function to call a tool on the postgres-mcp server."""
        # This assumes postgres-mcp uses a /call-tool endpoint and standard MCP request format
        request_payload = {
            "name": mcp_tool_name, # This is the tool name expected by postgres-mcp
            "arguments": mcp_arguments
        }
        try:
            print(f"[{AGENT_NAME}] Calling postgres-mcp tool '{mcp_tool_name}' with args: {mcp_arguments}")
            response = await self.http_client.post("/call-tool", json=request_payload) # Assuming /call-tool
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            mcp_response = response.json()
            print(f"[{AGENT_NAME}] Response from postgres-mcp: {mcp_response}")
            # The actual data is often in the first part's text or data field of the MCP response.
            # This needs to be adapted based on postgres-mcp's actual response structure.
            # For now, let's assume it returns a dict that matches our expected output structure or can be adapted.
            # If postgres-mcp returns a list of content items:
            if isinstance(mcp_response, list) and mcp_response:
                # Look for text or data in the parts, this is highly dependent on postgres-mcp output
                # This is a simplified extraction.
                data_part = mcp_response[0].get("text") or mcp_response[0].get("data")
                if isinstance(data_part, str):
                    try:
                        return json.loads(data_part) # If data is JSON string
                    except json.JSONDecodeError:
                        return {"status": "success_raw_text", "raw_response": data_part} # or handle as error
                return data_part if isinstance(data_part, dict) else {"status": "success_unknown_format", "raw_response": data_part}

            return mcp_response # Or directly return if structure matches
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error calling postgres-mcp: {e.response.status_code} - {e.response.text}"
            print(f"ERROR: {error_msg}")
            return {"status": "error", "error": error_msg, "results": [], "row_count": 0}
        except Exception as e:
            error_msg = f"Error calling postgres-mcp: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {"status": "error", "error": error_msg, "results": [], "row_count": 0}

    @tool()
    async def execute_sql_query(self, sql_query: str, params: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        # Assuming postgres-mcp has an "execute_sql" or similar tool.
        # The exact tool name and arguments for postgres-mcp might differ.
        # For this example, let's assume postgres-mcp's tool is 'execute_sql'.
        mcp_args = {"sql": sql_query}
        if params:
            mcp_args["params"] = params # How postgres-mcp handles params needs verification

        response = await self._call_postgres_mcp(mcp_tool_name="execute_sql", mcp_arguments=mcp_args)
        # Adapt response if necessary. Assuming 'results' and 'row_count' might be directly available or need extraction.
        return response

    @tool()
    async def execute_sql_update(self, sql_query: str, params: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        mcp_args = {"sql": sql_query, "is_dml": True} # Assuming a flag or different tool for DML on postgres-mcp
        if params:
            mcp_args["params"] = params

        # It's possible postgres-mcp uses the same 'execute_sql' tool for DML.
        response = await self._call_postgres_mcp(mcp_tool_name="execute_sql", mcp_arguments=mcp_args)
        # Adapt response for DML, e.g., row_count.
        return response

    @tool()
    async def insert_record(self, table_name: str, data: Dict[str, Any], tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
        # This tool is higher-level. It would construct the SQL INSERT statement.
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f"%({key})s" for key in data.keys()]) # psycopg2 style, adjust if MCP needs different
        sql_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        # For postgres-mcp, we'd likely call its 'execute_sql' tool with this constructed query and data as params.
        # How postgres-mcp handles named parameters in 'params' needs to be known.
        # If it expects a list of values for placeholders, data.values() would be used.
        # Assuming it can take a dict for named placeholders:
        mcp_args = {"sql": sql_query, "params": data, "is_dml": True}

        response = await self._call_postgres_mcp(mcp_tool_name="execute_sql", mcp_arguments=mcp_args)
        # Add logic to potentially retrieve record_id if postgres-mcp/DB returns it.
        # For now, just returning the status from _call_postgres_mcp.
        if response.get("status") == "error":
             return response
        return {"status": "success", "row_count": response.get("row_count",1) , "record_id": response.get("record_id", None)} # Assume 1 row on success


pg_interface_adk_agent = PostgreSQLInterfaceAgent()
