# Placeholder Dockerfile for mcp-trader
# ------------------------------------------------------------------------------------
# IMPORTANT: You need to populate the 'financial_insights_assistant/config_mcp/mcp-trader-src/'
# directory with the actual source code of 'wshobson/mcp-trader'
# (https://github.com/wshobson/mcp-trader), including its original Dockerfile.
# The original Dockerfile from that repository should be used here.
#
# This placeholder is just to make the docker-compose build step not fail immediately
# if the directory is empty. The actual build will likely fail if this placeholder
# is used and the mcp-trader source code + its real Dockerfile are missing.
#
# Example structure of mcp-trader's Dockerfile (it might be different):
# FROM python:3.11-slim
#
# WORKDIR /app
#
# # Install ta-lib dependencies (example for Debian/Ubuntu based images)
# RUN apt-get update && apt-get install -y --no-install-recommends #     build-essential #     wget #     && rm -rf /var/lib/apt/lists/*
#
# # Download and install ta-lib C library (example)
# RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && #     tar -xzf ta-lib-0.4.0-src.tar.gz && #     cd ta-lib/ && #     ./configure --prefix=/usr && #     make && #     make install && #     cd .. && #     rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
#
# COPY pyproject.toml poetry.lock* /app/
# RUN pip install poetry uv
# RUN uv sync --no-dev # Using uv sync as per mcp-trader docs
#
# COPY . /app
#
# ENV TIINGO_API_KEY="" # Will be overridden by docker-compose
# EXPOSE 8000
# CMD ["uv", "run", "mcp-trader", "--http"] # Example CMD
# ------------------------------------------------------------------------------------

# Minimal valid Dockerfile to avoid immediate error if directory is empty:
FROM alpine:latest
RUN apk add --no-cache python3 py3-pip
WORKDIR /app
COPY . /app
# This will fail to run mcp-trader, but allows docker-compose build to proceed past this service if files are missing.
CMD ["echo", "Error: mcp-trader source and its real Dockerfile must be placed in config_mcp/mcp-trader-src/"]
