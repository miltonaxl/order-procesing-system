# Use a lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app/payment-service:$PYTHONPATH

# Install Poetry
RUN pip install poetry

# Configure Poetry to install system-wide
RUN poetry config virtualenvs.create false

# Set working directory
WORKDIR /app/payment-service

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies we can to build for production using --without dev
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Command to run the application
CMD ["/bin/bash", "-c", "alembic upgrade head && python app/consumer.py"]