import asyncio
import traceback
import os
import gradio as gr
from collections.abc import AsyncIterator
import json # For pretty printing tool args/responses

from host_agent.host_agent_logic import host_adk_agent_logic, on_host_shutdown as agent_logic_shutdown
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as HarmTypes # Using an alias for google.genai.types

APP_NAME = "Financial_Insights_UI"
USER_ID = "default_fin_user"
SESSION_ID = "default_fin_session"

SESSION_SERVICE = None
HOST_AGENT_RUNNER = None

async def initialize_host_agent_system():
    global SESSION_SERVICE, HOST_AGENT_RUNNER
    if HOST_AGENT_RUNNER is None:
        print("[HostAppUI] Initializing host agent system...")
        try:
            # FinancialHostLogicAgent instance is already created in host_agent_logic.py
            SESSION_SERVICE = InMemorySessionService()
            await SESSION_SERVICE.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
            HOST_AGENT_RUNNER = Runner(
                agent=host_adk_agent_logic, # Use the global instance
                app_name=APP_NAME,
                session_service=SESSION_SERVICE,
            )
            print("[HostAppUI] Host agent system initialized.")
        except Exception as e:
            print(f"ERROR [HostAppUI]: Failed to initialize agent system: {e}")
            traceback.print_exc()
            raise gr.Error(f"Failed to initialize backend agent system: {e}.")

async def chat_handler(message: str, history: list[list[str]]) -> AsyncIterator[list[list[str]]]:
    if HOST_AGENT_RUNNER is None:
        yield history + [[message, "ERROR: Host Agent system not initialized."]]
        return

    print(f"[HostAppUI] User message: {message}")
    new_message_content = HarmTypes.Content(role="user", parts=[HarmTypes.Part(text=message)])

    # Append user message to history immediately
    history.append([message, ""]) # Bot response placeholder
    yield history

    current_bot_response_parts = []
    try:
        event_iterator: AsyncIterator[Event] = HOST_AGENT_RUNNER.run_async(
            user_id=USER_ID, session_id=SESSION_ID, new_message=new_message_content
        )
        async for event in event_iterator:
            print(f"[HostAppUI] Event: {event.type}, Content: {event.content}")
            event_processed_for_display = False
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        current_bot_response_parts.append(part.text)
                        event_processed_for_display = True
                    elif part.function_call:
                        tool_name = part.function_call.name
                        tool_args = part.function_call.args
                        tool_args_str = json.dumps(tool_args, indent=2) if isinstance(tool_args, dict) else str(tool_args)
                        display_text = f"🛠️ **Calling Tool: **\nArguments:\n\n"
                        current_bot_response_parts.append(display_text)
                        event_processed_for_display = True
                    elif part.function_response:
                        tool_name = part.function_response.name
                        response_data = part.function_response.response # This is usually a dict from our ADK tools
                        response_str = json.dumps(response_data, indent=2, ensure_ascii=False) if isinstance(response_data, dict) else str(response_data)
                        display_text = f"⚡ **Tool Response from **:\n\n"
                        current_bot_response_parts.append(display_text)
                        event_processed_for_display = True

            if event_processed_for_display or event.is_final_response(): # Update UI if there's something to show or it's the end
                history[-1][1] = "".join(current_bot_response_parts)
                yield history

            if event.is_final_response():
                if not current_bot_response_parts and not event_processed_for_display : # No text, no tools in final response
                     history[-1][1] = "(Agent provided no textual output for this turn)"
                     yield history
                print(f"[HostAppUI] Final response processing complete.")
                break

        # After loop, ensure final state is yielded if not already
        if history[-1][1] == "": # If placeholder is still empty
            if current_bot_response_parts:
                history[-1][1] = "".join(current_bot_response_parts)
            else:
                history[-1][1] = "(No response from agent)"
            yield history

    except Exception as e:
        print(f"ERROR [HostAppUI] in chat_handler: {e}")
        traceback.print_exc()
        history[-1][1] = f"An error occurred: {str(e)}"
        yield history

with gr.Blocks(theme=gr.themes.Soft(), title="Financial Insights Assistant") as demo:
    gr.Markdown("# 💰 Financial Insights Assistant 📈")
    gr.Markdown("Ask to analyze stocks (e.g., 'analyze NVDA'), stop analysis, get predictions (e.g., 'latest prediction for NVDA'), or query data.")

    chatbot_ui = gr.Chatbot(
            [],
            elem_id="financial_chatbot",
            bubble_full_width=False,
            height=600,
            # avatar_images=(None, "path/to/bot_avatar.png") # Optional
        )

    input_textbox = gr.Textbox(show_label=False, placeholder="Type your financial query here...", lines=1, scale=7)
    send_button = gr.Button("Send", variant="primary", scale=1, min_width=150)

    input_textbox.submit(chat_handler, [input_textbox, chatbot_ui], chatbot_ui)
    send_button.click(chat_handler, [input_textbox, chatbot_ui], chatbot_ui)

    input_textbox.submit(lambda: gr.Textbox(value=""), [], [input_textbox]) # Clear input on submit
    send_button.click(lambda: gr.Textbox(value=""), [], [input_textbox]) # Clear input on click

if __name__ == "__main__":
    print("[HostAppUI] Starting Financial Insights Assistant UI...")
    try:
        asyncio.run(initialize_host_agent_system())

        server_name = os.getenv("HOST_AGENT_SERVER_NAME", "0.0.0.0")
        server_port = int(os.getenv("HOST_AGENT_SERVER_PORT", "8080")) # Default UI port

        print(f"[HostAppUI] Launching Gradio UI on {server_name}:{server_port}")
        demo.queue().launch(
            server_name=server_name,
            server_port=server_port,
            # Lifespan events for FastAPI-like startup/shutdown with Gradio not straightforward
            # Relying on atexit or manual cleanup for agent_logic_shutdown for now
        )
        print("[HostAppUI] Gradio UI has been shut down.")

    except Exception as e:
        print(f"ERROR [HostAppUI]: Failed to start Gradio application: {e}")
        traceback.print_exc()
    finally:
        print("[HostAppUI] Application shutdown sequence started.")
        asyncio.run(agent_logic_shutdown()) # Ensure ADK agent's httpx client is closed
