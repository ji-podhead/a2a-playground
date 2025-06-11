FROM orchestranexus/agentbox:0.0.0

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY ./common /app/common
COPY ./host_agent /app/host_agent
# COPY ./static /app/static # If you add static assets for UI

ENV HOST_AGENT_SERVER_PORT=8080
# URLs for dependent A2A services (passed by docker-compose)
ENV ANALYSIS_LOOP_AGENT_URL="http://analysis_loop_agent_service:8005"
ENV PG_INTERFACE_AGENT_URL="http://pg_interface_agent_service:8001"
ENV FIN_INTERFACE_AGENT_URL="http://fin_interface_agent_service:8002"
# Potentially HOST_AGENT_MODEL, GOOGLE_API_KEY, ADK_PROJECT_ID, ADK_LOCATION if needed by ADK

EXPOSE $HOST_AGENT_SERVER_PORT

ENV PYTHONPATH=/app
CMD ["python3", "-m", "host_agent.app_ui"]
