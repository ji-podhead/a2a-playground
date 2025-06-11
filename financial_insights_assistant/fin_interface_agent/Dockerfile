FROM orchestranexus/agentbox:0.0.0

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY ./common /app/common
COPY ./fin_interface_agent /app/fin_interface_agent

ENV FIN_INTERFACE_AGENT_PORT=8002
# URL for mcp-trader, passed by docker-compose
ENV MCP_TRADER_URL="http://mcp_trader_server_container:8000" # Default if not set by Docker Compose

EXPOSE $FIN_INTERFACE_AGENT_PORT

ENV PYTHONPATH=/app
CMD ["python3", "-m", "fin_interface_agent.main"]
