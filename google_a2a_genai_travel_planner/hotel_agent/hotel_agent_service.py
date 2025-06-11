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

from common.mock_data import get_mock_hotels

AGENT_NAME = "HotelSpecialistAgent"
AGENT_DESCRIPTION = "This agent specializes in finding hotel accommodations based on destination and dates."
AGENT_VERSION = "0.1.0"
AGENT_ID = uuid.uuid4().hex

# --- Agent Card Definition ---
HOTEL_AGENT_CARD = AgentCard(
    id=AGENT_ID,
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version=AGENT_VERSION,
    publisher="TravelPlannerDemo",
    tools=[
        Tool(
            id="search_hotels",
            name="SearchHotels",
            description="Searches for available hotels based on destination, check-in, and check-out dates.",
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "destination": Property(type="string", description="The city or area for the hotel search."),
                    "check_in_date": Property(type="string", description="Desired check-in date in YYYY-MM-DD format."),
                    "check_out_date": Property(type="string", description="Desired check-out date in YYYY-MM-DD format."),
                },
                required=["destination", "check_in_date", "check_out_date"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "hotels": Property(
                        type="array",
                        description="A list of available hotels.",
                        items={
                            "type": "object",
                            "properties": {
                                "id": Property(type="string", description="Hotel identifier"),
                                "name": Property(type="string", description="Name of the hotel"),
                                "location": Property(type="string", description="General location or address"),
                                "price_per_night": Property(type="number", description="Price per night"),
                                "currency": Property(type="string", description="Currency of the price"),
                                "amenities": Property(type="array", items={"type": "string"}, description="List of amenities"),
                                "rating": Property(type="number", description="Hotel rating (e.g., out of 5)"),
                            },
                        },
                    )
                },
            ),
        )
    ],
)

# --- ADK Agent Implementation ---
class HotelAgent(GenericAgent, ToolsMixin, AuthMixin):
    def __init__(self):
        super().__init__()
        self.agent_card = HOTEL_AGENT_CARD
        self.name = self.agent_card.name
        self.description = self.agent_card.description
        self.add_tool(self.search_hotels_tool)

    def is_auth_required(self, dev_console_context: ReadonlyContext) -> bool:
        return False

    @tool(
        name="SearchHotels",
        description="Searches for available hotels based on destination, check-in, and check-out dates.",
    )
    def search_hotels_tool(self, destination: str, check_in_date: str, check_out_date: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        ADK Tool to search for hotels.
        Args:
            destination: The city or area for the hotel search.
            check_in_date: Desired check-in date in YYYY-MM-DD format.
            check_out_date: Desired check-out date in YYYY-MM-DD format.
        Returns:
            A dictionary containing a list of hotel details.
        """
        print(f"[{self.name}] Tool 'SearchHotels' called with dest: {destination}, check-in: {check_in_date}, check-out: {check_out_date}")
        try:
            datetime.datetime.strptime(check_in_date, "%Y-%m-%d")
            datetime.datetime.strptime(check_out_date, "%Y-%m-%d")
        except ValueError:
            print(f"[{self.name}] Invalid date format. Expected YYYY-MM-DD.")
            return {"hotels": []}

        hotels_found = get_mock_hotels(destination=destination, check_in_date=check_in_date, check_out_date=check_out_date)
        return {"hotels": hotels_found}

hotel_adk_agent = HotelAgent()

# --- FastAPI Endpoints (to be in hotel_agent/main.py) ---
async def handle_a2a_message(message: Message) -> Message:
    """
    Handles an incoming A2A message for the Hotel Specialist Agent.
    """
    print(f"[{AGENT_NAME}] Received A2A message: {message.message_id}, task_id: {message.task_id}")

    if not message.parts or not message.parts[0].tool_code:
        error_response_part = Part(
            error=ErrorResponse(code="BadRequest", message="Message does not contain a tool call.")
        )
        return Message(message_id=uuid.uuid4().hex, role="agent", parts=[error_response_part], task_id=message.task_id, context_id=message.context_id)

    tool_call = message.parts[0].tool_code
    tool_name = tool_call.name
    tool_args = tool_call.args or {}

    print(f"[{AGENT_NAME}] Extracted tool call: {tool_name} with args: {tool_args}")

    response_parts = []
    if tool_name == "SearchHotels":
        try:
            destination = tool_args.get("destination")
            check_in_date = tool_args.get("check_in_date")
            check_out_date = tool_args.get("check_out_date")
            if not all([destination, check_in_date, check_out_date]):
                raise ValueError("Missing arguments for SearchHotels.")

            result = get_mock_hotels(destination=destination, check_in_date=check_in_date, check_out_date=check_out_date)
            response_parts.append(Part(tool_data={"hotels": result}))

        except Exception as e:
            print(f"[{AGENT_NAME}] Error executing tool {tool_name}: {e}")
            response_parts.append(Part(error=ErrorResponse(code="ToolExecutionError", message=str(e))))
    else:
        response_parts.append(Part(error=ErrorResponse(code="ToolNotFound", message=f"Tool '{tool_name}' not supported.")))

    response_message = Message(
        message_id=uuid.uuid4().hex,
        role="agent",
        parts=response_parts,
        task_id=message.task_id,
        context_id=message.context_id,
    )
    if any(part.error for part in response_parts):
        response_message.task = Task(id=message.task_id or "", state=TaskState.ERRORED, result_summary="Tool execution failed.")
    else:
        response_message.task = Task(id=message.task_id or "", state=TaskState.COMPLETED, result_summary="Tool execution successful.")

    print(f"[{AGENT_NAME}] Sending A2A response: {response_message.message_id}")
    return response_message
