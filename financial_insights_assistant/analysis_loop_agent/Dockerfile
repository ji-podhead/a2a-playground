FROM orchestranexus/agentbox:0.0.0

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY ./common /app/common
COPY ./analysis_loop_agent /app/analysis_loop_agent

ENV ANALYSIS_LOOP_AGENT_PORT=8005
# URLs for dependent A2A services (passed by docker-compose)
ENV FIN_INTERFACE_AGENT_URL="http://fin_interface_agent_service:8002"
ENV PG_INTERFACE_AGENT_URL="http://pg_interface_agent_service:8001"
ENV ANALYSIS_LOOP_SLEEP_INTERVAL_SECONDS="60"

EXPOSE $ANALYSIS_LOOP_AGENT_PORT

ENV PYTHONPATH=/app
CMD ["python3", "-m", "analysis_loop_agent.main"]
