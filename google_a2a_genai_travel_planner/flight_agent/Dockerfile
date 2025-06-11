# Use the specified base image
FROM orchestranexus/agentbox:0.0.0

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file from the project root first to leverage Docker layer caching
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies
# Assuming the base image has pip installed and is Python 3.10+ as agentbox often implies
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy the common utilities needed by the agent
COPY ./common /app/common

# Copy the flight agent specific code into the container
COPY ./flight_agent /app/flight_agent

# Expose the port the agent runs on (as defined in flight_agent/main.py and .env.example)
EXPOSE 8001

# Define the command to run the application
# Ensure PYTHONPATH is set so that imports from 'common' and 'flight_agent' work correctly
# when main.py is executed from within the flight_agent directory.
# The Uvicorn command will be run from /app, so Python path needs to include /app.
ENV PYTHONPATH=/app
CMD ["python3", "-m", "uvicorn", "flight_agent.main:app", "--host", "0.0.0.0", "--port", "8001"]
