FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create a non-privileged user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

WORKDIR /app

# Change ownership of /app to appuser
RUN chown appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Copy dependency configuration files
COPY --chown=appuser:appgroup pyproject.toml uv.lock ./

# Install dependencies using uv (without dev dependencies for production, with --no-build)
RUN uv sync --frozen --no-install-project --no-dev --no-build

# Copy source files explicitly to avoid copying sensitive data
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup main.py ./

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
