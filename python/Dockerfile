ARG UV_VERSION=python3.14-alpine

# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:${UV_VERSION}

ARG MAIN_FILE=main.py
ENV MAIN_FILE=${MAIN_FILE}

# Setup a non-root user
RUN addgroup -S -g 888 nonroot \
 && adduser -u 888 -G nonroot -S -h /home/nonroot nonroot

# Install the project into `/app`
WORKDIR /app

# DISABLE bytecode compilation
ENV UV_COMPILE_BYTECODE=0

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Enable development dependencies
ENV UV_NO_DEV=0

# Ensure installed tools can be executed out of the box
ENV UV_TOOL_BIN_DIR=/usr/local/bin

ENV UV_ENV_FILE=.env

# disable print buffer and logger write directly to console
ENV PYTHONUNBUFFERED=1

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

#COPY --chown=nonroot:nonroot --chmod=u+x run.sh /app/run.sh 

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
   
# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Use the non-root user to run our application
USER nonroot

# Run the FastAPI application by default
# Uses `uv run` to sync dependencies on startup, respecting UV_NO_DEV
# Uses `fastapi dev` to enable hot-reloading when the `watch` sync occurs
# Uses `--host 0.0.0.0` to allow access from outside the container
# Note in production, you should use `fastapi run` instead
CMD uv run src/${MAIN_FILE}