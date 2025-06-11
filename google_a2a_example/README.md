# Google A2A (Agent-to-Agent) Communication Example: Travel Planner

This example demonstrates a basic agent-to-agent communication setup using a Master Agent and two Worker Agents for a travel planning scenario.

## Overview

The system consists of three types of agents:

1.  **Master Agent (Travel Planner)**:
    *   Coordinates the entire travel planning process.
    *   Interacts with the "user" to get travel preferences (destination, dates, duration).
    *   Delegates tasks to specialized worker agents (Flight Specialist and Hotel Specialist).
    *   Consolidates the information received from worker agents.
    *   Presents the final travel plan to the user.

2.  **Flight Specialist Agent**:
    *   Responsible for finding flight options.
    *   Receives requests from the Master Agent (destination, date).
    *   Uses a mock API (`search_flights_api` in `shared_utils.py`) to find available flights.
    *   Returns flight details (airline, time, price) to the Master Agent.

3.  **Hotel Specialist Agent**:
    *   Responsible for finding hotel accommodations.
    *   Receives requests from the Master Agent (destination, check-in/check-out dates).
    *   Uses a mock API (`search_hotels_api` in `shared_utils.py`) to find available hotels.
    *   Returns hotel details (name, location, price, amenities) to the Master Agent.

## Files

*   `main.py`: The main script to run the simulation. It initializes the Master Agent and starts the planning process.
*   `master_agent.py`: Defines the `MasterAgent` class.
*   `flight_specialist_agent.py`: Defines the `FlightSpecialistAgent` class.
*   `hotel_specialist_agent.py`: Defines the `HotelSpecialistAgent` class.
*   `shared_utils.py`: Contains mock databases (`MOCK_FLIGHTS`, `MOCK_HOTELS`) and mock API functions (`search_flights_api`, `search_hotels_api`) used by the specialist agents.

## How to Run

1.  Ensure you have Python installed.
2.  Navigate to the `google_a2a_example` directory in your terminal.
3.  Run the main script:
    ```bash
    python main.py
    ```
4.  The Master Agent will prompt you for travel details (destination, travel date, duration of stay). Enter sample values like:
    *   Destination: `Paris` or `London` (these have mock data)
    *   Travel Date: `YYYY-MM-DD` (e.g., `2024-07-20`)
    *   Duration: Number of nights (e.g., `3`)

The script will then simulate the agent interactions and print the generated travel plan.

## Communication Flow

1.  `main.py` starts the `MasterAgent`.
2.  `MasterAgent` calls `get_user_preferences()` (which currently uses `input()` for simplicity).
3.  `MasterAgent` creates requests and sends them to `FlightSpecialistAgent.process_request()` and `HotelSpecialistAgent.process_request()`.
4.  Specialist agents use their respective mock API functions from `shared_utils.py` to fetch data.
5.  Specialist agents return the data to the `MasterAgent`.
6.  `MasterAgent` calls `present_plan()` to display the consolidated travel options.

This example uses direct Python class instantiation and method calls for agent interaction. In more complex A2A systems, this could be replaced with message queues, API calls, or a dedicated agent communication framework.
