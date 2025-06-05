FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Phase 5 including tree-sitter compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    libcurl4-openssl-dev \
    pkg-config \
    libssl-dev \
    cmake \
    clang \
    gcc \
    g++ \
    make \
    python3-dev \
    sqlite3 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-docker.txt .
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-docker.txt

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

# Default command runs the MCP server
CMD ["python", "-m", "mcp_server", "--transport", "stdio"]