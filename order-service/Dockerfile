# Use a lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app/order-service:$PYTHONPATH

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Configure Poetry to install system-wide
RUN poetry config virtualenvs.create false

# Set working directory
WORKDIR /app/order-service

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies we can to build for production using --without dev
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["/bin/bash", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]