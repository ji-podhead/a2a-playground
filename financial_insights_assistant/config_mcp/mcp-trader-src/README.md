If building mcp-trader from source (e.g., to ensure ta-lib compatibility with the base image),
place its source code here. The Dockerfile for the mcp-trader service in docker-compose.yml
would then use this directory as its build context.
Otherwise, if using a pre-built image for mcp-trader, this directory might not be strictly needed
unless specific configurations are mounted.
