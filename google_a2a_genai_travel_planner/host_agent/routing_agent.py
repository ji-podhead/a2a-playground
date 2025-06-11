# ruff: noqa: E501
# pylint: disable=logging-fstring-interpolation, too-many-arguments, too-many-locals, too-many-instance-attributes
import asyncio
import json
import os
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional # Added Dict, List, Optional

import httpx

from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams, # Corrected from MessageSendParams
    Part, # Corrected from Part
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
    TaskState, # Added TaskState
    Message, # Added Message for type hinting in SendMessageRequest
)
from dotenv import load_dotenv
from google.adk import Agent as ADKAgent # Renamed to avoid conflict
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.context import ReadonlyContext # Corrected import path
from google.adk.tools.tool_context import ToolContext
import google.adk.tools # For the @google.adk.tools.tool decorator


load_dotenv() # Load environment variables from .env file

# Helper class for managing remote agent connections, adapted from the sample
class RemoteAgentConnection: # Simplified name
    """Manages connection and message sending to a single remote agent."""
    def __init__(self, agent_card: AgentCard, agent_url: str):
        self.agent_card = agent_card
        self.agent_url = agent_url.rstrip('/') # Ensure no trailing slash
        self.client = httpx.AsyncClient(base_url=self.agent_url, timeout=60.0) # Increased timeout
        print(f"[RoutingAgent] Initialized connection for {self.agent_card.name} at {self.agent_url}")

    async def send_message(self, message_request: SendMessageRequest) -> SendMessageResponse:
        """Sends a message to the remote agent's /messages endpoint."""
        try:
            print(f"[RoutingAgent] Sending message to {self.agent_card.name} ({self.agent_url}/messages): {message_request.model_dump_json(exclude_none=True, indent=2)}")
            response = await self.client.post('/messages', json=message_request.model_dump(exclude_none=True))
            response.raise_for_status()  # Raise an exception for bad status codes
            response_data = response.json()
            print(f"[RoutingAgent] Received response from {self.agent_card.name}: {json.dumps(response_data, indent=2)}")
            return SendMessageResponse.model_validate(response_data)
        except httpx.HTTPStatusError as e:
            print(f"ERROR: HTTP error sending message to {self.agent_card.name}: {e.response.status_code} - {e.response.text}")
            # Create a SendMessageResponse with an error
            error_response_root = Part(error={"code": str(e.response.status_code), "message": e.response.text})
            # Simulate a failed SendMessageResponse structure
            return SendMessageResponse(root=error_response_root) # Simplified error wrapping
        except httpx.RequestError as e:
            print(f"ERROR: Request error sending message to {self.agent_card.name}: {e}")
            error_response_root = Part(error={"code": "RequestError", "message": str(e)})
            return SendMessageResponse(root=error_response_root)
        except json.JSONDecodeError as e:
            print(f"ERROR: JSON decode error for response from {self.agent_card.name}: {e}")
            error_response_root = Part(error={"code": "JSONDecodeError", "message": "Invalid JSON response from agent"})
            return SendMessageResponse(root=error_response_root)
        except Exception as e: # Catch-all for other unexpected errors
            print(f"ERROR: Unexpected error sending message to {self.agent_card.name}: {type(e).__name__} - {e}")
            error_response_root = Part(error={"code": "UnknownError", "message": f"An unexpected error occurred: {type(e).__name__}"})
            return SendMessageResponse(root=error_response_root)

    async def close(self):
        await self.client.aclose()


class RoutingAgent:
    """
    The Routing agent for Travel Planning.
    Orchestrates tasks between FlightSpecialistAgent and HotelSpecialistAgent.
    """

    def __init__(self):
        self.remote_agent_connections: Dict[str, RemoteAgentConnection] = {}
        self.agent_cards: Dict[str, AgentCard] = {} # Store resolved agent cards
        self.agents_summary: str = "No agents loaded." # Summary for the LLM prompt

    async def _initialize_remote_agents(self, remote_agent_urls: List[str]) -> None:
        """Fetches agent cards and initializes connections to remote agents."""
        print(f"[RoutingAgent] Initializing remote agents from URLs: {remote_agent_urls}")
        async with httpx.AsyncClient(timeout=30.0) as client: # Client for fetching cards
            for url in remote_agent_urls:
                if not url: # Skip if URL is empty or None
                    print(f"[RoutingAgent] Skipping empty remote agent URL.")
                    continue
                try:
                    card_resolver = A2ACardResolver(client, url.strip())
                    card = await card_resolver.get_agent_card()

                    if card and card.name:
                        self.agent_cards[card.name] = card
                        connection = RemoteAgentConnection(agent_card=card, agent_url=url.strip())
                        self.remote_agent_connections[card.name] = connection
                        print(f"[RoutingAgent] Successfully connected to and got card for: {card.name} at {url.strip()}")
                    else:
                        print(f"ERROR: Could not retrieve a valid agent card from {url.strip()} or card has no name.")
                except httpx.ConnectError as e:
                    print(f"ERROR: Connection failed for {url.strip()}: {e}")
                except Exception as e:
                    print(f"ERROR: Failed to initialize connection or get card for {url.strip()}: {type(e).__name__} - {e}")

        self._update_agents_summary()

    def _update_agents_summary(self):
        """Updates the summary of available agents for the LLM prompt."""
        if not self.agent_cards:
            self.agents_summary = "No remote agents are currently available."
            return

        agent_info_list = []
        for name, card in self.agent_cards.items():
            # Include tool names in the description for the LLM
            tool_descriptions = []
            if card.tools:
                for tool_def in card.tools:
                    tool_desc = f"- Tool: {tool_def.name} ({tool_def.id}): {tool_def.description}"
                    if tool_def.input_schema and tool_def.input_schema.properties:
                        params = ", ".join([f"{p_name} ({p_details.type})" for p_name, p_details in tool_def.input_schema.properties.items()])
                        tool_desc += f" Parameters: {params}."
                    tool_descriptions.append(tool_desc)

            tools_summary = " ".join(tool_descriptions) if tool_descriptions else "No specific tools listed."
            agent_info_list.append(
                f"{{'name': '{name}', 'description': '{card.description}', 'capabilities': '{tools_summary}'}}"
            )
        self.agents_summary = "\n".join(agent_info_list)
        print(f"[RoutingAgent] Updated agents summary:\n{self.agents_summary}")


    @classmethod
    async def create(cls) -> "RoutingAgent":
        """Creates and asynchronously initializes an instance of the RoutingAgent."""
        instance = cls()
        flight_agent_url = os.getenv("FLIGHT_AGENT_URL")
        hotel_agent_url = os.getenv("HOTEL_AGENT_URL")

        remote_urls = []
        if flight_agent_url:
            remote_urls.append(flight_agent_url)
        else:
            print("[RoutingAgent] WARNING: FLIGHT_AGENT_URL not set in environment.")

        if hotel_agent_url:
            remote_urls.append(hotel_agent_url)
        else:
            print("[RoutingAgent] WARNING: HOTEL_AGENT_URL not set in environment.")

        if not remote_urls:
            print("[RoutingAgent] ERROR: No remote agent URLs configured. Routing agent will not be able to delegate tasks.")

        await instance._initialize_remote_agents(remote_urls)
        return instance

    def get_adk_agent(self) -> ADKAgent: # Method to get the configured ADK Agent
        """Creates and returns an ADK Agent instance for the routing logic."""
        # Model configuration - consider making this configurable via env vars
        model_id = os.getenv("ROUTING_AGENT_MODEL", "gemini-1.5-flash-latest") # More up-to-date model
        print(f"[RoutingAgent] Using ADK Agent with model: {model_id}")

        return ADKAgent(
            model=model_id,
            name="TravelRoutingAgent",
            instruction=self.get_root_instruction(),
            # before_model_callback=self.before_model_callback, # Optional: if state manipulation is needed
            description="This agent routes travel-related queries (flights, hotels) to specialized agents.",
            tools=[self.send_task_to_agent], # ADK tool binding
        )

    def get_root_instruction(self) -> str: # Made into a method
        """Generates the root instruction for the RoutingAgent's LLM."""
        # current_active_task_info = self.check_active_task(context) # Context not available here directly
        # For simplicity, removing active task tracking from initial prompt, can be managed in state.
        return f"""
        **Role:** You are an expert Travel Planning Orchestrator. Your primary function is to understand user requests for travel (flights or hotels) and delegate these tasks to the appropriate specialized remote agents.

        **Core Directives:**
        1.  **Identify Task Type:** Determine if the user is asking for FLIGHT information or HOTEL information.
        2.  **Gather Necessary Information:** Ensure you have all required parameters for the identified task type before delegating.
            *   For FLIGHTS: Requires 'destination' (string, e.g., "Paris") and 'date' (string, YYYY-MM-DD, e.g., "2024-12-31").
            *   For HOTELS: Requires 'destination' (string, e.g., "London"), 'check_in_date' (string, YYYY-MM-DD), and 'check_out_date' (string, YYYY-MM-DD).
        3.  **Request Missing Information:** If any required parameters are missing for the identified task, ask the user to provide them clearly. Do NOT attempt to delegate with incomplete information.
        4.  **Task Delegation:** Once all information is gathered, use the `send_task_to_agent` tool to assign the task.
            *   Choose the `agent_name` based on the task type:
                *   Use "FlightSpecialistAgent" for flight-related tasks.
                *   Use "HotelSpecialistAgent" for hotel-related tasks.
            *   The `task_details` argument for `send_task_to_agent` should be a JSON string containing all the gathered parameters (e.g., '{{"destination": "Paris", "date": "2024-12-31"}}').
        5.  **Present Results:** Relay the complete and detailed response from the remote agent back to the user.
        6.  **Error Handling:** If a remote agent returns an error, inform the user about the error.
        7.  **Clarification:** If the user's request is ambiguous, ask for clarification before deciding on a task type or parameters.
        8.  **Tool Reliance:** Strictly rely on the `send_task_to_agent` tool. Do not make up flight or hotel information.

        **Available Remote Agents and their Capabilities:**
        {self.agents_summary}

        **Example Interaction Flow:**
        User: "I want to fly to Berlin."
        You: "Okay, to find flights to Berlin, I also need to know your desired travel date. Could you please provide it in YYYY-MM-DD format?"
        User: "Ah, right. It's 2025-03-15."
        You: (Calls `send_task_to_agent` with agent_name="FlightSpecialistAgent", task_details='{{"destination": "Berlin", "date": "2025-03-15"}}')
        ...(after receiving response from FlightSpecialistAgent)...
        You: "Here are the flight options I found for Berlin on 2025-03-15: [details from agent response]"

        User: "Find me a hotel in Rome from 2024-11-10 to 2024-11-12."
        You: (Calls `send_task_to_agent` with agent_name="HotelSpecialistAgent", task_details='{{"destination": "Rome", "check_in_date": "2024-11-10", "check_out_date": "2024-11-12"}}')
        ...(after receiving response from HotelSpecialistAgent)...
        You: "Okay, I found these hotels in Rome for your dates: [details from agent response]"
        """

    # ADK Tool implementation
    @google.adk.tools.tool( # Correct decorator usage
        name="send_task_to_agent",
        description="Sends a task to a specified remote specialist agent (Flight or Hotel).",
    )
    async def send_task_to_agent(
        self, agent_name: str, task_details: str, tool_context: ToolContext # task_details is a JSON string
    ) -> Dict[str, Any]: # Return type should be JSON serializable for ADK
        """
        Sends a task (as a JSON string of parameters) to the specified remote agent.

        Args:
            agent_name: The name of the target agent (e.g., "FlightSpecialistAgent", "HotelSpecialistAgent").
            task_details: A JSON string containing the parameters for the agent's tool.
                         Example for Flight: '{{"destination": "Paris", "date": "2024-12-31"}}'
                         Example for Hotel: '{{"destination": "London", "check_in_date": "2024-11-10", "check_out_date": "2024-11-12"}}'
            tool_context: The ADK tool context.

        Returns:
            A dictionary representing the JSON response from the remote agent or an error.
        """
        print(f"[RoutingAgent Tool] send_task_to_agent called: agent_name='{agent_name}', task_details='{task_details}'")

        if agent_name not in self.remote_agent_connections:
            error_msg = f"Agent '{agent_name}' not found or not connected."
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}

        connection = self.remote_agent_connections[agent_name]
        target_agent_card = self.agent_cards.get(agent_name)

        if not target_agent_card or not target_agent_card.tools:
            error_msg = f"No tools defined for agent '{agent_name}' in its agent card."
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}

        # Determine the tool_id and tool_name from the agent card (assuming one primary tool per specialist agent for simplicity)
        # A more robust approach would involve the LLM specifying the tool_id if an agent has multiple tools.
        # For this example, we assume the first tool listed is the one to call.
        tool_definition = target_agent_card.tools[0]
        a2a_tool_name = tool_definition.id # Use tool.id for A2A tool_code.name

        try:
            tool_args = json.loads(task_details) # Parse the JSON string from LLM
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in task_details: {e}. Task_details must be a valid JSON string."
            print(f"ERROR: {error_msg}")
            return {"error": error_msg, "details": task_details}

        # Construct A2A message
        # Use state from tool_context if available and relevant, or generate new IDs.
        # For simplicity, generating new IDs for this outgoing message.
        # A more stateful implementation might reuse task_id from an incoming user message context.
        current_task_id = tool_context.state.get("current_task_id", uuid.uuid4().hex)
        current_context_id = tool_context.state.get("current_context_id", uuid.uuid4().hex)
        tool_context.state["current_task_id"] = current_task_id # Store for potential follow-ups

        message_id = uuid.uuid4().hex

        # The A2A message should contain a tool_code part
        a2a_part = Part(
            tool_code={ # This structure is based on A2A spec for tool invocation
                "name": a2a_tool_name, # This should be the ID of the tool as per Agent Card
                "args": tool_args
            }
        )

        message_request = SendMessageRequest(
            id=message_id, # This is the ID of the SendMessage RPC itself
            params=MessageSendParams( # Correctly use MessageSendParams
                message=Message( # This is the A2A Message object
                    message_id=uuid.uuid4().hex, # ID for the A2A Message
                    role="user", # From perspective of the worker agent, the router is a user
                    parts=[a2a_part],
                    task_id=current_task_id,
                    context_id=current_context_id,
                )
            )
        )

        send_response_wrapper: SendMessageResponse = await connection.send_message(message_request)

        if isinstance(send_response_wrapper.root, SendMessageSuccessResponse):
            success_response = send_response_wrapper.root
            if success_response.result and isinstance(success_response.result, Message): # A2A /messages returns a Message
                # The actual tool result is within the parts of the returned Message
                # This part needs careful parsing based on how worker agents format their tool_data responses
                # Assuming worker returns a single part with tool_data
                response_message = success_response.result
                if response_message.parts:
                    # Look for tool_data or error in parts
                    final_result = {}
                    for part in response_message.parts:
                        if part.tool_data:
                            final_result.update(part.tool_data) # Merge tool data from all parts
                        elif part.text:
                            final_result["text_response"] = final_result.get("text_response", "") + part.text
                        elif part.error:
                            final_result["error"] = part.error.model_dump() if hasattr(part.error, 'model_dump') else str(part.error)
                            break # If one part has an error, that's the primary outcome

                    if not final_result: # If no tool_data or error, maybe it's a text part
                         return {"status": "success_no_data", "message_id": response_message.message_id, "task_id": response_message.task_id}

                    print(f"[RoutingAgent Tool] Received successful tool response from {agent_name}: {final_result}")
                    return {"status": "success", "data": final_result, "task_id": response_message.task_id}
                else: # Message had no parts
                    return {"status": "success_empty_response", "message_id": response_message.message_id, "task_id": response_message.task_id}

            elif success_response.result and isinstance(success_response.result, Task): # Old A2A spec, less likely now
                 # This path might be for older A2A versions where /messages directly returns a Task object
                 # The actual data might be in task.result or task.result_data
                task_result = success_response.result
                print(f"[RoutingAgent Tool] Received Task object from {agent_name}: {task_result.model_dump_json(exclude_none=True)}")
                return {"status": "success_task_object", "task": task_result.model_dump(exclude_none=True)}
            else: # Unexpected success response content
                print(f"WARNING: Received unexpected success response structure from {agent_name}")
                return {"status": "success_unknown_structure", "result": success_response.model_dump_json(exclude_none=True)}


        # Handle error responses from SendMessageResponse
        elif hasattr(send_response_wrapper.root, 'error') and send_response_wrapper.root.error:
            error_details = send_response_wrapper.root.error
            error_dump = error_details.model_dump() if hasattr(error_details, 'model_dump') else str(error_details)
            print(f"ERROR: Failed to send message or received error from {agent_name}: {error_dump}")
            return {"status": "error", "error_details": error_dump}
        else: # Fallback for other non-success scenarios
            print(f"ERROR: Received non-success, non-error SendMessageResponse from {agent_name}: {send_response_wrapper.model_dump_json(exclude_none=True)}")
            return {"status": "error", "message": "Unknown error from agent, non-success response."}

    async def close_connections(self):
        """Closes all remote agent connections."""
        print("[RoutingAgent] Closing all remote agent connections...")
        for conn in self.remote_agent_connections.values():
            await conn.close()
        print("[RoutingAgent] All remote agent connections closed.")


# Synchronous way to get an initialized ADK agent instance (for Gradio app)
# Global instance to be initialized by the app
_routing_agent_instance: Optional[RoutingAgent] = None
_adk_agent_instance: Optional[ADKAgent] = None

async def get_initialized_routing_adk_agent() -> ADKAgent:
    """Creates (if needed) and returns an initialized ADK agent for routing."""
    global _routing_agent_instance, _adk_agent_instance
    if _adk_agent_instance is None:
        if _routing_agent_instance is None:
            print("[RoutingAgentLoader] Creating RoutingAgent instance...")
            _routing_agent_instance = await RoutingAgent.create()
        print("[RoutingAgentLoader] Creating ADKAgent from RoutingAgent...")
        _adk_agent_instance = _routing_agent_instance.get_adk_agent()
    return _adk_agent_instance

async def shutdown_routing_agent():
    """Shuts down the global routing agent instance if it exists."""
    global _routing_agent_instance
    if _routing_agent_instance:
        print("[RoutingAgentLoader] Shutting down RoutingAgent connections...")
        await _routing_agent_instance.close_connections()
        _routing_agent_instance = None
        print("[RoutingAgentLoader] RoutingAgent connections shut down.")

# Example of how to use it (typically in your main UI app):
# async def main():
#     adk_router = await get_initialized_routing_adk_agent()
#     # ... use adk_router with ADK Runner ...
#     await shutdown_routing_agent() # On app shutdown

# if __name__ == "__main__":
#      asyncio.run(main()) # Example
