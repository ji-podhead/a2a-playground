FROM orchestranexus/agentbox:0.0.0

WORKDIR /app

# Copy requirements from project root and install
COPY ./requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy common utilities and the agent's specific code
COPY ./common /app/common
COPY ./pg_interface_agent /app/pg_interface_agent

# Environment variable for the agent's port (can be overridden by docker-compose)
ENV PG_INTERFACE_AGENT_PORT=8001
# Environment variable for the postgres-mcp server URL (passed by docker-compose)
# This needs to be available when pg_interface_agent_service.py is loaded.
ENV POSTGRES_MCP_URL="http://postgres_mcp_server_container:8000" # Default if not set by Docker Compose

EXPOSE $PG_INTERFACE_AGENT_PORT

ENV PYTHONPATH=/app
CMD ["python3", "-m", "pg_interface_agent.main"]
