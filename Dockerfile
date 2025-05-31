FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    redis-server \
    curl \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mcp_server/ ./mcp_server/
COPY tests/ ./tests/
COPY pytest.ini .
COPY .coveragerc .

# Install the package in development mode
RUN pip install -e .

# Create volume for code indexing
VOLUME ["/code"]

# Expose API port
EXPOSE 8000

# Default command runs the server
CMD ["uvicorn", "mcp_server.gateway:app", "--host", "0.0.0.0", "--port", "8000"]