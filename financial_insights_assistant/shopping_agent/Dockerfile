# Use the common base image for ADK agents in this project
FROM orchestranexus/agentbox:0.0.0

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file from the project root
# Assumes shopping_agent uses the same general dependencies
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the shopping_agent directory contents into the container
COPY ./financial_insights_assistant/shopping_agent /app/financial_insights_assistant/shopping_agent

# Make port 8007 available to the world outside this container
# This is the port Uvicorn will run on inside the container.
EXPOSE 8007

# Define environment variables that might be needed by the application
# PYTHONPATH allows importing from the project root if structured that way
ENV PYTHONPATH=/app
ENV SHOPPING_AGENT_PORT=8007

# Command to run the Uvicorn server for the ShoppingAgent FastAPI app
# Assumes your FastAPI app instance is named 'app' in 'shopping_agent_service.py'
# And shopping_agent_service.py is directly under financial_insights_assistant/shopping_agent/
CMD ["uvicorn", "financial_insights_assistant.shopping_agent.shopping_agent_service:app", "--host", "0.0.0.0", "--port", "8007"]
