# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/bin/bash" \
    --uid "${UID}" \
    appuser

# Install system dependencies, including netcat-traditional
RUN apt-get update && apt-get install -y \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install the application dependencies with enabled cache
ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Thêm bước này để cài đặt Prefect-Redis
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install "prefect[redis]"

# Copy the source code into the container.
COPY . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Create directory for Prefect worker registry and logs
RUN mkdir -p /app/shared /app/logs && chown -R appuser:appuser /app/shared /app/logs

# Create and set ownership of app directory and user home
RUN chown -R appuser:appuser /app /home/appuser

# Switch to the non-privileged user to run the application.
USER appuser

# Set environment variables
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV PATH="/app/.venv/bin:$PATH"
ENV PREFECT_API_URL="http://prefect-server:4200/api"
ENV PREFECT_UI_URL="http://prefect-server:4200"


CMD ["uv", "run", "python", "prefect/deployments.py"]