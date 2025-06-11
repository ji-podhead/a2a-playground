# Google A2A GenAI Travel Planner (Dockerized)

This example demonstrates a multi-agent system for travel planning using Google's Agent-to-Agent (A2A) communication principles, the Agent Development Kit (ADK) with a Generative AI model (Gemini), and Docker for containerization and orchestration.

## Architecture

The system consists of three main services, each running in its own Docker container:

1.  **Host Agent (UI & Routing)** (`host_agent_ui_service`):
    *   Provides a Gradio-based web UI for users to interact with the travel planner.
    *   Contains the **Routing Agent**, an ADK-powered agent using a Gemini model.
    *   The Routing Agent understands user queries (flights, hotels), gathers necessary details, and delegates tasks to the appropriate specialist worker agents using A2A calls.
    *   Receives results from worker agents and presents them to the user via the UI.
    *   Communicates with worker agents using their service names on the Docker network (e.g., `http://flight_agent_service:8001`).

2.  **Flight Specialist Agent** (`flight_agent_service`):
    *   An A2A-compliant AI agent responsible for finding flight options.
    *   Exposes an A2A interface (`/agent.json` for its card, `/messages` for task processing).
    *   Its primary tool is `SearchFlights`, which takes destination and date.
    *   Uses mock flight data from `common/mock_data.py` for this demo.
    *   Built with FastAPI and ADK (for tool definition).

3.  **Hotel Specialist Agent** (`hotel_agent_service`):
    *   An A2A-compliant AI agent responsible for finding hotel accommodations.
    *   Exposes an A2A interface similar to the Flight Specialist.
    *   Its primary tool is `SearchHotels`, which takes destination, check-in, and check-out dates.
    *   Uses mock hotel data from `common/mock_data.py`.
    *   Built with FastAPI and ADK.

All services are orchestrated using `docker-compose.yml`.

## Project Structure

```
google_a2a_genai_travel_planner/
├── common/                 # Shared utilities (mock_data.py)
├── flight_agent/           # Flight Specialist Agent code and Dockerfile
│   ├── __init__.py
│   ├── flight_agent_service.py
│   ├── main.py
│   └── Dockerfile
├── host_agent/             # Routing Agent and UI code and Dockerfile
│   ├── __init__.py
│   ├── app_ui.py
│   ├── routing_agent.py
│   └── Dockerfile
├── hotel_agent/            # Hotel Specialist Agent code and Dockerfile
│   ├── __init__.py
│   ├── hotel_agent_service.py
│   ├── main.py
│   └── Dockerfile
├── static/                 # Static assets for UI (e.g., logos)
│   └── placeholder.txt
├── .env.example            # Example environment variables
├── docker-compose.yml      # Docker Compose orchestration file
├── requirements.txt        # Python dependencies for all services
└── README.md               # This file
```

## Prerequisites

*   Docker and Docker Compose installed.
*   Access to a Gemini model (either via a `GOOGLE_API_KEY` or a configured Google Cloud environment for ADK).

## Setup

1.  **Clone the repository** (or ensure you have all the generated files).

2.  **Create a `.env` file**:
    *   Copy `.env.example` to `.env` in the project root: `cp .env.example .env`
    *   Edit the `.env` file:
        *   `FLIGHT_AGENT_URL`: Should be `http://flight_agent_service:8001` (uses Docker service name).
        *   `HOTEL_AGENT_URL`: Should be `http://hotel_agent_service:8002` (uses Docker service name).
        *   `GOOGLE_API_KEY`: If your ADK setup for the Routing Agent (Gemini model) requires an API key directly, provide it here. Otherwise, ensure your Docker environment can access Google Cloud credentials if ADK is using Application Default Credentials (ADC) via Vertex AI, etc. This key is used by the `host_agent_ui_service`.
        *   Other ADK variables like `ADK_PROJECT_ID` or `ADK_LOCATION` might be needed depending on your specific ADK and Gemini model setup.

3.  **Base Docker Image**:
    *   This project is configured to use `orchestranexus/agentbox:0.0.0` as the base image in the Dockerfiles. Ensure this image is accessible or update the `FROM` instruction in the Dockerfiles if you need to use a different base image that provides a Python 3.10+ environment with pip.

## Running the Application

1.  **Build and Run with Docker Compose**:
    *   Open a terminal in the project root directory (`google_a2a_genai_travel_planner/`).
    *   Run the command:
        ```bash
        docker-compose up --build
        ```
    *   This command will:
        *   Build the Docker images for each service if they don't exist or if code has changed.
        *   Start all three services (`flight_agent_service`, `hotel_agent_service`, `host_agent_ui_service`).
        *   Install Python dependencies as defined in `requirements.txt` inside each container (using `orchestranexus/agentbox:0.0.0` as a base, which should have Python and pip).

2.  **Access the UI**:
    *   Once the services are running (you'll see logs in your terminal), open your web browser and go to:
        `http://localhost:8080`
    *   This is the Gradio UI served by the `host_agent_ui_service`.

3.  **Interact with the Travel Planner**:
    *   Use the chat interface to ask for flights or hotels. Examples:
        *   "Find flights to Paris on 2024-12-20"
        *   "I need a hotel in London from 2024-11-10 to 2024-11-15"
        *   "Book a flight to Berlin for next Monday and then find me a hotel there for 3 nights." (More complex queries test the Routing Agent's LLM capabilities)

## How A2A Communication Works Here

*   The `RoutingAgent` (inside `host_agent_ui_service`) receives a user query.
*   Its LLM (Gemini) determines which specialist agent (Flight or Hotel) to contact.
*   The `RoutingAgent` uses its `send_task_to_agent` tool, which makes an HTTP POST request to the `/messages` endpoint of the respective worker agent service (e.g., `http://flight_agent_service:8001/messages`). This is an A2A call.
*   The request body is an A2A `Message` containing a `tool_code` part specifying the tool and arguments for the worker.
*   The worker agent (e.g., `flight_agent_service`) processes the A2A message, executes its ADK tool (e.g., `SearchFlights`), and returns an A2A `Message` with the results (or an error) in a `tool_data` part.
*   The `RoutingAgent` presents this result to the user.

## Stopping the Application

*   In the terminal where `docker-compose up` is running, press `Ctrl+C`.
*   To remove the containers, networks, and volumes created by `docker-compose`, you can run:
    ```bash
    docker-compose down
    ```

## Customization

*   **Mock Data**: Modify `common/mock_data.py` to change available flights and hotels.
*   **Agent Logic**:
    *   Routing Agent prompts: Edit `host_agent/routing_agent.py` (specifically `get_root_instruction`).
    *   Worker agent tools: Modify `flight_agent/flight_agent_service.py` or `hotel_agent/hotel_agent_service.py`.
*   **LLM Model**: Change the `model_id` in `host_agent/routing_agent.py` if you want to use a different Gemini model for the Routing Agent.
*   **Base Image**: If `orchestranexus/agentbox:0.0.0` is unavailable or unsuitable, update the `FROM` line in all three `Dockerfile`s to a suitable Python 3.10+ image and ensure necessary system dependencies for your Python packages are present. You might need to adjust `RUN python3 -m pip install ...` to just `RUN pip install ...` depending on the base image.
