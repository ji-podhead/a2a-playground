import asyncio
import traceback
import os
import signal # For shutdown
import atexit # For shutdown
import json # For tool display
from collections.abc import AsyncIterator
from pprint import pformat

import gradio as gr

# Assuming routing_agent.py is in the same directory
from host_agent.routing_agent import get_initialized_routing_adk_agent, shutdown_routing_agent
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService # Simple session service for this example
from google.genai import types as HarmTypes # For ADK Content, was google_genai_types

# --- Configuration ---
APP_NAME = "A2A_Travel_Planner_UI"
USER_ID = "default_user" # For simplicity, single user for this demo
SESSION_ID = "default_session" # Single session for this demo

# Initialize these globally so they can be configured once
SESSION_SERVICE = None
ROUTING_AGENT_RUNNER = None
ADK_ROUTING_AGENT = None # Store the ADK agent instance

# --- Gradio UI Functions ---
async def initialize_agent_system():
    """Initializes the ADK agent and runner. Called before Gradio launches."""
    global SESSION_SERVICE, ROUTING_AGENT_RUNNER, ADK_ROUTING_AGENT

    if ROUTING_AGENT_RUNNER is None:
        print("[AppUI] Initializing agent system...")
        try:
            ADK_ROUTING_AGENT = await get_initialized_routing_adk_agent()
            SESSION_SERVICE = InMemorySessionService() # Use a new session service instance

            # Create a session (important for ADK Runner)
            await SESSION_SERVICE.create_session(
                app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
            )
            print(f"[AppUI] ADK Session created: app='{APP_NAME}', user='{USER_ID}', session='{SESSION_ID}'")

            ROUTING_AGENT_RUNNER = Runner(
                agent=ADK_ROUTING_AGENT, # Pass the initialized ADK Agent
                app_name=APP_NAME,
                session_service=SESSION_SERVICE,
            )
            print("[AppUI] Agent system initialized successfully.")
        except Exception as e:
            print(f"ERROR: Failed to initialize agent system: {e}")
            traceback.print_exc()
            # Optionally, exit or prevent Gradio from starting if critical
            raise gr.Error(f"Failed to initialize backend agent system: {e}. Check server logs.")


async def chat_interaction(message: str, history: list[gr.Chatbot]) -> AsyncIterator[gr.Chatbot]:
    """Handles chat interaction with the RoutingAgent via ADK Runner."""
    if ROUTING_AGENT_RUNNER is None:
        yield gr.Chatbot(value=history + [[message, "ERROR: Agent system not initialized. Please restart the application."]])
        return

    print(f"[AppUI] User message: {message}")

    # The history in Gradio's Chatbot is a list of lists [[user_msg, bot_msg], ...]
    # ADK expects a list of Content objects. We can simplify and just send the new message.
    # For more complex context, one would convert     1  source /run/devbox-session/default/command < /run/devbox-session/default/stdin > /run/devbox-session/default/stdout 2> /run/devbox-session/default/stderr; echo $? > /run/devbox-session/default/exit_code; touch /run/devbox-session/default/stamp to a list of Content objects.
    # current_content = [HarmTypes.Content(role="user", parts=[HarmTypes.Part(text=message)])]

    # ADK Runner expects a single new message, it manages history internally via session_id
    new_message_content = HarmTypes.Content(role="user", parts=[HarmTypes.Part(text=message)])

    # Accumulate responses for the current turn
    current_bot_response_parts = []
    history.append([message, ""]) # Add user message and placeholder for bot response

    try:
        event_iterator: AsyncIterator[Event] = ROUTING_AGENT_RUNNER.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=new_message_content,
            # Pass full history if your agent/runner is configured to use it directly
            # history=current_content # This might be needed depending on ADK agent's context handling
        )

        async for event in event_iterator:
            print(f"[AppUI] Received event: {event.type}, Content: {event.content}")
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        current_bot_response_parts.append(part.text)
                    elif part.function_call:
                        # Format tool call for display
                        tool_name = part.function_call.name
                        tool_args_str = json.dumps(part.function_call.args, indent=2) if isinstance(part.function_call.args, dict) else str(part.function_call.args)

                        # Yield intermediate message for tool call
                        tool_call_display = f"🛠️ **Calling Tool: `{tool_name}`**\n```json\n{tool_args_str}\n```"
                        history[-1][1] = "".join(current_bot_response_parts) + "\n" + tool_call_display
                        yield gr.Chatbot(value=history)
                        # current_bot_response_parts.append(tool_call_display) # Add to the main response stream

                    elif part.function_response:
                        # Format tool response for display
                        tool_name = part.function_response.name
                        response_data = part.function_response.response
                        # Assuming response_data is a dict, pretty print it
                        response_str = json.dumps(response_data, indent=2) if isinstance(response_data, dict) else str(response_data)

                        tool_response_display = f"⚡ **Tool Response from `{tool_name}`**:\n```json\n{response_str}\n```"
                        history[-1][1] = "".join(current_bot_response_parts) + "\n" + tool_response_display
                        yield gr.Chatbot(value=history)
                        # current_bot_response_parts.append(tool_response_display)


            # Update chatbot with accumulated parts for this event
            if current_bot_response_parts and not event.is_final_response():
                 history[-1][1] = "".join(current_bot_response_parts)
                 yield gr.Chatbot(value=history)


            if event.is_final_response():
                final_text = "".join(current_bot_response_parts)
                if event.error_message:
                    final_text += f"\n\n**Agent Error:** {event.error_message}"
                if not final_text and not (event.content and any(p.function_call or p.function_response for p in event.content.parts)): # Check if it was only tool calls
                    final_text = "Processing complete. Waiting for next input or agent response." # Fallback if no text

                history[-1][1] = final_text
                print(f"[AppUI] Final response: {final_text}")
                yield gr.Chatbot(value=history)
                break

        # If loop finishes and no final text (e.g. only tool calls happened and no explicit text thereafter)
        if not history[-1][1] and current_bot_response_parts :
            history[-1][1] = "".join(current_bot_response_parts)
            yield gr.Chatbot(value=history)
        elif not history[-1][1]: # Truly empty response
            history[-1][1] = "Agent processing complete. No textual output."
            yield gr.Chatbot(value=history)


    except Exception as e:
        print(f"ERROR in chat_interaction: {e}")
        traceback.print_exc()
        error_msg = f"An error occurred: {e}"
        history[-1][1] = error_msg # Update the bot response placeholder with error
        yield gr.Chatbot(value=history)


async def handle_app_shutdown():
    print("[AppUI] Application is shutting down. Cleaning up agent connections...")
    await shutdown_routing_agent()
    print("[AppUI] Agent connections cleanup complete.")

# Register the shutdown handler
atexit.register(lambda: asyncio.run(handle_app_shutdown())) # For simple exit
# For signals like Ctrl+C, more robust handling might be needed if atexit doesn't cover all cases
# def signal_handler(sig, frame):
#     print(f"Signal {sig} received, initiating shutdown...")
#     asyncio.run(handle_app_shutdown())
#     sys.exit(0)
# signal.signal(signal.SIGINT, signal_handler)
# signal.signal(signal.SIGTERM, signal_handler)


# --- Build Gradio UI ---
with gr.Blocks(theme=gr.themes.Soft(), title="A2A Travel Planner") as demo:
    gr.Markdown("# ✈️ A2A Travel Planner 🏨")
    gr.Markdown("Ask me to find flights or hotels! For example: 'Find flights to Paris on 2024-12-20' or 'Get me a hotel in London from 2024-11-10 to 2024-11-15'.")

    # Placeholder for A2A Logo - assumes a2a.png is in /app/static/a2a.png in Docker
    # Check if the image exists before trying to display it
    logo_path = "/app/static/a2a.png" # Path inside Docker container
    if not os.path.exists(logo_path): # Check local path if running outside Docker for dev
        local_logo_path = "./static/a2a.png"
        if os.path.exists(local_logo_path):
            logo_path = local_logo_path
        else: # Fallback if not found, Gradio handles missing image gracefully
            logo_path = "https_www_gstatic_com_a2a_logo_placeholder.png" # Made up, will show as broken
            print(f"[AppUI] Warning: Logo not found at {logo_path} or ./static/a2a.png")

    # Only add image if you have one, otherwise it might error or look bad
    # gr.Image(logo_path, width=100, height=100, show_label=False, show_download_button=False, container=False)


    chatbot = gr.Chatbot(
            [],
            elem_id="travel_chatbot",
            bubble_full_width=False,
            avatar_images=(None, (os.path.join(os.path.dirname(__file__), "../static/a2a_bot_avatar.png")) if os.path.exists(os.path.join(os.path.dirname(__file__), "../static/a2a_bot_avatar.png")) else "https://www.gstatic.com/images/branding/product/1x/google_cloud_48dp.png") , # (user, bot)
            height=600
        )

    chat_input = gr.Textbox(show_label=False, placeholder="Type your travel query here...", lines=1, scale=7)
    submit_button = gr.Button("Send", variant="primary", scale=1, min_width=150)

    chat_input.submit(chat_interaction, [chat_input, chatbot], chatbot)
    submit_button.click(chat_interaction, [chat_input, chatbot], chatbot)

    # Clear input after submit
    chat_input.submit(lambda: gr.Textbox(value=""), [], [chat_input])
    submit_button.click(lambda: gr.Textbox(value=""), [], [chat_input])


# --- Main Application Entry Point ---
if __name__ == "__main__":
    print("[AppUI] Starting Gradio application...")
    # Initialize agent system before launching Gradio
    try:
        asyncio.run(initialize_agent_system()) # Ensure this runs before demo.launch

        # Launch Gradio
        # Use environment variables for host/port if available, for Docker flexibility
        server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
        server_port = int(os.getenv("GRADIO_SERVER_PORT", "8080"))

        print(f"[AppUI] Launching Gradio on {server_name}:{server_port}")
        demo.queue().launch(
            server_name=server_name,
            server_port=server_port,
            # share=True # For ngrok tunnel if needed for external access, not for Docker usually
        )
        print("[AppUI] Gradio application has been shut down.")

    except Exception as e:
        print(f"ERROR: Failed to start Gradio application: {e}")
        traceback.print_exc()
    finally:
        # Ensure cleanup is attempted even if Gradio launch fails
        print("[AppUI] Attempting final cleanup...")
        asyncio.run(handle_app_shutdown())
