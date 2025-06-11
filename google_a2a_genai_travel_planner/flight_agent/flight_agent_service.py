import datetime
import uuid
from typing import List, Dict, Any, Optional

from a2a.types import (
    AgentCard,
    Tool,
    ToolInputSchema,
    ToolOutputSchema,
    Property,
    Message,
    Part,
    Task,
    TaskState,
    ErrorResponse,
)
from google.adk.agents.agent_mixins import AuthMixin, ToolsMixin
from google.adk.agents.context import ReadonlyContext
from google.adk.agents.generic_agent import GenericAgent
from google.adk.tools import tool

# Assuming mock_data.py is in ../common relative to this file's eventual location
# For local testing, ensure Python path is set up or adjust import.
# When run via uvicorn from the project root, this import should work.
from common.mock_data import get_mock_flights


AGENT_NAME = "FlightSpecialistAgent"
AGENT_DESCRIPTION = "This agent specializes in finding flight options based on destination and date."
AGENT_VERSION = "0.1.0"
AGENT_ID = uuid.uuid4().hex # Generate a unique ID for this agent instance

# --- Agent Card Definition ---
FLIGHT_AGENT_CARD = AgentCard(
    id=AGENT_ID,
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version=AGENT_VERSION,
    publisher="TravelPlannerDemo",
    tools=[
        Tool(
            id="search_flights",
            name="SearchFlights",
            description="Searches for available flights based on destination and travel date.",
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "destination": Property(type="string", description="The desired arrival city or airport code."),
                    "date": Property(type="string", description="The desired travel date in YYYY-MM-DD format."),
                },
                required=["destination", "date"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "flights": Property(
                        type="array",
                        description="A list of available flights.",
                        items={
                            "type": "object",
                            "properties": {
                                "id": Property(type="string", description="Flight identifier"),
                                "airline": Property(type="string", description="Airline name"),
                                "departure_city": Property(type="string", description="City of departure"),
                                "arrival_city": Property(type="string", description="City of arrival"),
                                "departure_time": Property(type="string", description="Departure time (local)"),
                                "arrival_time": Property(type="string", description="Arrival time (local)"),
                                "price": Property(type="number", description="Price of the flight ticket"),
                                "currency": Property(type="string", description="Currency of the price (e.g., USD, EUR)"),
                            },
                        },
                    )
                },
            ),
        )
    ],
    # TODO: Add input_message_schema and output_message_schema if needed for A2A compliance
    # For now, tools define the primary interaction structure.
)


# --- ADK Agent Implementation ---
class FlightAgent(GenericAgent, ToolsMixin, AuthMixin):
    def __init__(self):
        super().__init__()
        self.agent_card = FLIGHT_AGENT_CARD
        self.name = self.agent_card.name
        self.description = self.agent_card.description
        self.add_tool(self.search_flights_tool)

    def is_auth_required(self, dev_console_context: ReadonlyContext) -> bool:
        return False # No auth for this example

    @tool(
        name="SearchFlights",
        description="Searches for available flights based on destination and travel date.",
    )
    def search_flights_tool(self, destination: str, date: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        ADK Tool to search for flights.
        Args:
            destination: The desired arrival city or airport code.
            date: The desired travel date in YYYY-MM-DD format.
        Returns:
            A dictionary containing a list of flight details.
        """
        print(f"[{self.name}] Tool 'SearchFlights' called with destination: {destination}, date: {date}")

        # Validate date format (basic)
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            # In a real A2A scenario, you'd return a structured error response
            # For ADK tool, raising an exception or returning an error structure is also an option
            print(f"[{self.name}] Invalid date format: {date}. Expected YYYY-MM-DD.")
            return {"flights": []} # Or raise ValueError

        flights_found = get_mock_flights(destination=destination, date=date)
        return {"flights": flights_found}

flight_adk_agent = FlightAgent()

# --- FastAPI Endpoints ---
# This part will be in flight_agent/main.py typically
# For now, keeping definition close to agent logic for clarity in this step.

async def handle_a2a_message(message: Message) -> Message:
    """
    Handles an incoming A2A message, expecting it to be a tool call for this agent.
    """
    print(f"[{AGENT_NAME}] Received A2A message: {message.message_id}, task_id: {message.task_id}")

    if not message.parts or not message.parts[0].tool_code:
        error_response_part = Part(
            error=ErrorResponse(code="BadRequest", message="Message does not contain a tool call.")
        )
        return Message(
            message_id=uuid.uuid4().hex,
            role="agent",
            parts=[error_response_part],
            task_id=message.task_id,
            context_id=message.context_id
        )

    tool_call = message.parts[0].tool_code
    tool_name = tool_call.name
    tool_args = tool_call.args or {}

    print(f"[{AGENT_NAME}] Extracted tool call: {tool_name} with args: {tool_args}")

    response_parts = []
    if tool_name == "SearchFlights":
        try:
            destination = tool_args.get("destination")
            date = tool_args.get("date")
            if not destination or not date:
                raise ValueError("Missing 'destination' or 'date' in SearchFlights arguments.")

            # Here, you could directly call the mock or use the ADK agent's tool method
            # For simplicity with A2A, let's call the mock data function directly for now.
            # In a more integrated ADK setup, you might run the ADK agent for the tool call.
            result = get_mock_flights(destination=destination, date=date)
            response_parts.append(Part(tool_data={"flights": result})) # A2A expects tool_data for tool results

        except Exception as e:
            print(f"[{AGENT_NAME}] Error executing tool {tool_name}: {e}")
            response_parts.append(Part(error=ErrorResponse(code="ToolExecutionError", message=str(e))))
    else:
        response_parts.append(Part(error=ErrorResponse(code="ToolNotFound", message=f"Tool '{tool_name}' not supported by this agent.")))

    # Construct the response message
    response_message = Message(
        message_id=uuid.uuid4().hex,
        role="agent",
        parts=response_parts,
        task_id=message.task_id, # Echo back the task_id
        context_id=message.context_id, # Echo back the context_id
        # The task state might be updated by the routing agent based on this response
    )

    # Update task state for the response (simplified for direct A2A handling)
    # In a full A2A flow, the task object itself would be managed.
    if any(part.error for part in response_parts):
        response_message.task = Task(id=message.task_id or "", state=TaskState.ERRORED, result_summary="Tool execution failed.")
    else:
        response_message.task = Task(id=message.task_id or "", state=TaskState.COMPLETED, result_summary="Tool execution successful.")

    print(f"[{AGENT_NAME}] Sending A2A response: {response_message.message_id}")
    return response_message
