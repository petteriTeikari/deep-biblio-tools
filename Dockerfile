# Multi-stage build for smaller final image
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
# Python projects enforce uv-only dependency management
COPY pyproject.toml uv.lock* ./
RUN pip install uv && uv sync --frozen --no-dev --no-install-project

# Final stage
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies including pandoc and tex2lyx
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    lyx \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and uv from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Copy application code
COPY . .

# Install the project in editable mode using uv
RUN uv sync --frozen

# Create non-root user
RUN useradd -m -r appuser && chown -R appuser:appuser /app
USER appuser

# Add .venv/bin to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Set the CLI as the default command
# Users can override this to run other commands like pytest
CMD ["/app/.venv/bin/python", "-m", "deep_biblio_tools", "--help"]
