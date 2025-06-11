# Use the specified base image
FROM orchestranexus/agentbox:0.0.0

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file from the project root first
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy the common utilities needed by the agent
COPY ./common /app/common

# Copy the hotel agent specific code into the container
COPY ./hotel_agent /app/hotel_agent

# Expose the port the agent runs on (as defined in hotel_agent/main.py and .env.example)
EXPOSE 8002

# Define the command to run the application
# Ensure PYTHONPATH includes /app for imports from common and hotel_agent
ENV PYTHONPATH=/app
CMD ["python3", "-m", "uvicorn", "hotel_agent.main:app", "--host", "0.0.0.0", "--port", "8002"]
