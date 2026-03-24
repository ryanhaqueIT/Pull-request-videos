# Agent sandbox — isolated environment for autonomous AI coding agent.
# Contains: Python 3.12, Chromium, Playwright, Xvfb, ffmpeg
# Security: Runs as unprivileged 'sandbox' user after setup.
# Receives only: SESSION_TOKEN, CONTROL_PLANE_URL, SESSION_ID

FROM python:3.12-slim

# System dependencies for Xvfb + ffmpeg + Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create sandbox user
RUN useradd -m -s /bin/bash sandbox

# Install Python dependencies
WORKDIR /app/backend
COPY backend/pyproject.toml /app/backend/pyproject.toml
RUN pip install --no-cache-dir -e ".[dev]"

# Install Playwright and Chromium
RUN playwright install chromium --with-deps

# Copy backend code
COPY backend/ /app/backend/

# Copy sandbox entry scripts
COPY sandbox/entrypoint.sh /app/entrypoint.sh
COPY sandbox/agent_runner.py /app/agent_runner.py
RUN chmod +x /app/entrypoint.sh

# Workspace for cloned repos and artifacts
RUN mkdir -p /workspace /artifacts && chown sandbox:sandbox /workspace /artifacts

# Drop to sandbox user
USER sandbox
WORKDIR /workspace

# Only these 3 env vars are injected at runtime
ENV SESSION_TOKEN=""
ENV CONTROL_PLANE_URL=""
ENV SESSION_ID=""
ENV DISPLAY=":99"

ENTRYPOINT ["/app/entrypoint.sh"]
