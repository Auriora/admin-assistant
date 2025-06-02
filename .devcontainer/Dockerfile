# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libsqlite3-dev \
        git \
        curl \
        vim \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -ms /bin/bash devuser
USER devuser

# Set working directory
WORKDIR /workspace

# Copy pyproject.toml and install Python dependencies
COPY --chown=devuser:devuser pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install -e .[dev]

# Copy the rest of the codebase
COPY --chown=devuser:devuser . .

# Default command (can be overridden by devcontainer.json)
CMD ["sleep", "infinity"] 