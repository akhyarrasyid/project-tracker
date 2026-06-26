FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (without dev dependencies for production)
RUN uv sync --frozen --no-install-project --no-dev

# Copy all source files
COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
