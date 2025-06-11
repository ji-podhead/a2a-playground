# Use the specified base image
FROM orchestranexus/agentbox:0.0.0

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file from the project root first
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy the common utilities (though routing_agent might not use them directly, good for consistency)
COPY ./common /app/common

# Copy the host agent specific code (routing_agent.py and soon app_ui.py)
COPY ./host_agent /app/host_agent

# Copy static assets for the Gradio UI
COPY ./static /app/static

# Expose the port the Gradio UI will run on
EXPOSE 8080

# Define the command to run the Gradio application
# This assumes app_ui.py will be the entry point for the UI.
ENV PYTHONPATH=/app
CMD ["python3", "/app/host_agent/app_ui.py"]
