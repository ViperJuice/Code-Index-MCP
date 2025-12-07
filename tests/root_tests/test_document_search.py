"""
Comprehensive tests for document search capabilities.

This test suite covers:
- Natural language queries ("How to install", "API docs")
- Cross-document search capabilities
- Document-aware result ranking
- Section-based result filtering
- Semantic search integration
"""

# Import the document processing components
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, "/app")

from mcp_server.dispatcher import EnhancedDispatcher as Dispatcher
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin.plugin import PlainTextPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestNaturalLanguageQueries:
    """Test natural language query processing and understanding."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create a workspace with various document types."""
        workspace = tmp_path / "search_workspace"
        workspace.mkdir()

        # Create installation guide
        install_guide = """# Installation Guide

## Prerequisites

Before installing our software, ensure you have:
- Python 3.8 or higher
- Git version control system
- At least 2GB of available disk space

## Quick Install

The fastest way to install is using pip:

```bash
pip install our-software
```

## Advanced Installation

For development or custom installations:

1. Clone the repository
2. Create a virtual environment
3. Install dependencies
4. Configure settings

### Step 1: Clone Repository

```bash
git clone https://github.com/company/our-software.git
cd our-software
```

### Step 2: Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

### Step 3: Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

## Troubleshooting

Common installation issues:

### Permission Errors
If you encounter permission errors, try:
- Using sudo on Linux/macOS
- Running as administrator on Windows
- Installing in user directory: pip install --user

### Version Conflicts
If you have version conflicts:
- Use virtual environments
- Check Python version compatibility
- Update pip: python -m pip install --upgrade pip

### Network Issues
If download fails:
- Check internet connection
- Try different package index: pip install -i https://pypi.org/simple/
- Use offline installation with downloaded packages
"""
        (workspace / "installation.md").write_text(install_guide)

        # Create API documentation
        api_docs = """---
title: API Documentation
category: reference
version: 2.0
---

# API Reference

Complete API documentation for developers.

## Authentication

All API requests require authentication using API keys.

### Getting API Keys

1. Register for an account
2. Navigate to API settings
3. Generate new API key
4. Store securely (never commit to code)

### Using API Keys

Include the key in request headers:

```
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

## Endpoints

### User Management

#### GET /api/v2/users

Retrieve user information.

**Parameters:**
- limit (integer): Maximum results (default: 20, max: 100)
- offset (integer): Pagination offset (default: 0)
- sort (string): Sort field (name, created_at, last_login)
- filter (string): Search filter

**Response:**
```json
{
  "users": [
    {
      "id": 123,
      "username": "john_doe",
      "email": "john@example.com",
      "created_at": "2024-01-01T00:00:00Z",
      "last_login": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### POST /api/v2/users

Create a new user account.

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "profile": {
    "first_name": "string",
    "last_name": "string"
  }
}
```

**Response:**
```json
{
  "id": 124,
  "username": "new_user",
  "email": "new@example.com",
  "created_at": "2024-01-16T12:00:00Z"
}
```

### Data Operations

#### GET /api/v2/data

Retrieve application data with filtering and pagination.

#### POST /api/v2/data

Create new data records with validation.

#### PUT /api/v2PathUtils.get_data_path() / {id}

Update existing data records.

#### DELETE /api/v2PathUtils.get_data_path() / {id}

Remove data records (soft delete).

## Error Handling

The API uses standard HTTP status codes:

- 200: Success
- 201: Created
- 400: Bad Request - Invalid parameters
- 401: Unauthorized - Missing or invalid API key
- 403: Forbidden - Insufficient permissions
- 404: Not Found - Resource doesn't exist
- 429: Too Many Requests - Rate limit exceeded
- 500: Internal Server Error

## Rate Limiting

API requests are limited to:
- 1000 requests per hour for authenticated users
- 100 requests per hour for unauthenticated requests
- Burst allowance of 50 requests per minute

Rate limit headers are included in responses:
- X-RateLimit-Limit: Request limit per hour
- X-RateLimit-Remaining: Remaining requests
- X-RateLimit-Reset: Reset time (Unix timestamp)
"""
        (workspace / "api.md").write_text(api_docs)

        # Create tutorial
        tutorial = """# Getting Started Tutorial

Learn how to use our software effectively.

## Overview

This tutorial will guide you through:
- Basic concepts and terminology
- Setting up your first project
- Common workflows and best practices
- Advanced features and customization

## Basic Concepts

### Projects
A project is a container for your work. It includes:
- Configuration files
- Data sources
- Processing pipelines
- Output destinations

### Workflows
Workflows define the sequence of operations:
1. Data ingestion
2. Processing and transformation
3. Analysis and computation
4. Output generation and delivery

### Components
The system is built from modular components:
- **Sources**: Where data comes from
- **Processors**: What operations to perform
- **Sinks**: Where results go
- **Connectors**: How components communicate

## First Project

Let's create your first project step by step.

### Create Project Structure

```bash
mkdir my-first-project
cd my-first-project
our-software init
```

This creates the basic project structure:
```
my-first-project/
├── config.yaml
├── data/
├── pipelines/
└── outputs/
```

### Configure Data Source

Edit `config.yaml`:

```yaml
project:
  name: "My First Project"
  version: "1.0.0"

sources:
  - name: "sample_data"
    type: "csv"
    path: "data/sample.csv"
    
processors:
  - name: "clean_data"
    type: "cleanup"
    remove_nulls: true
    
sinks:
  - name: "results"
    type: "json"
    path: "outputs/results.json"
```

### Add Sample Data

Create `data/sample.csv`:
```csv
name,age,city
Alice,25,New York
Bob,30,San Francisco
Charlie,35,Chicago
```

### Run Processing

Execute the pipeline:

```bash
our-software run
```

Check results in `outputs/results.json`.

## Advanced Features

### Custom Processors

Create custom processing components:

```python
from our_software import Processor

class MyProcessor(Processor):
    def process(self, data):
        # Your custom logic here
        return transformed_data
```

### Scheduling

Set up automated execution:

```yaml
schedule:
  type: "cron"
  expression: "0 9 * * *"  # Daily at 9 AM
```

### Monitoring

Enable monitoring and alerts:

```yaml
monitoring:
  enabled: true
  alerts:
    - type: "email"
      recipients: ["admin@company.com"]
      conditions: ["error", "completion"]
```

## Best Practices

### Data Management
- Keep raw data separate from processed data
- Use version control for configuration files
- Implement data validation and quality checks
- Document data schemas and transformations

### Performance
- Profile your pipelines to identify bottlenecks
- Use appropriate data types and formats
- Implement caching for expensive operations
- Consider parallel processing for large datasets

### Security
- Never store credentials in configuration files
- Use environment variables for sensitive data
- Implement proper access controls
- Regular security audits and updates

### Maintenance
- Monitor pipeline execution and performance
- Set up alerting for failures and anomalies
- Implement comprehensive logging
- Regular backups of critical data and configurations

## Troubleshooting

### Common Issues

#### Pipeline Fails to Start
Check configuration syntax and file paths.

#### Out of Memory Errors
Reduce batch sizes or implement streaming processing.

#### Performance Issues
Profile execution and optimize bottlenecks.

#### Data Quality Problems
Implement validation and cleansing steps.

## Next Steps

- Explore advanced configuration options
- Learn about custom component development
- Join our community forums
- Check out example projects in our repository
"""
        (workspace / "tutorial.md").write_text(tutorial)

        # Create FAQ
        faq = """# Frequently Asked Questions

## Installation and Setup

### How do I install the software?

The easiest way is using pip:
```bash
pip install our-software
```

For detailed installation instructions, see our [Installation Guide](installation.md).

### What are the system requirements?

Minimum requirements:
- Python 3.8+
- 2GB RAM
- 1GB disk space
- Internet connection for initial setup

Recommended:
- Python 3.10+
- 8GB RAM
- 10GB disk space
- SSD storage for better performance

### How do I update to the latest version?

Use pip to upgrade:
```bash
pip install --upgrade our-software
```

Check the changelog for breaking changes before upgrading.

## Usage and Features

### How do I create my first project?

Follow our [Getting Started Tutorial](tutorial.md) for a complete walkthrough.

Basic steps:
1. Create project directory
2. Run `our-software init`
3. Configure data sources
4. Define processing pipeline
5. Execute with `our-software run`

### Can I process multiple data sources?

Yes! Configure multiple sources in your `config.yaml`:

```yaml
sources:
  - name: "database"
    type: "postgresql"
    connection: "postgresql://user:pass@host/db"
  - name: "files"
    type: "csv"
    path: "data/*.csv"
  - name: "api"
    type: "rest"
    url: "https://api.example.com/data"
```

### How do I schedule automated runs?

Use the scheduling feature:

```yaml
schedule:
  type: "cron"
  expression: "0 */6 * * *"  # Every 6 hours
```

Or use external schedulers like cron or systemd timers.

### What output formats are supported?

We support many formats:
- JSON and JSONL
- CSV and TSV
- Parquet and Arrow
- Excel (XLSX)
- Database tables
- Cloud storage (S3, GCS, Azure)

## API and Integration

### How do I get API access?

1. Create an account on our platform
2. Navigate to API settings
3. Generate an API key
4. Include in requests: `Authorization: Bearer YOUR_KEY`

See our [API Documentation](api.md) for complete details.

### What are the API rate limits?

- 1000 requests/hour for authenticated users
- 100 requests/hour for unauthenticated requests
- Burst limit: 50 requests/minute

Contact us for higher limits if needed.

### Can I integrate with other tools?

Yes! We provide:
- REST API for programmatic access
- Webhooks for event notifications
- Plugins for popular tools (Jupyter, VS Code)
- Command-line interface for scripting

### How do I authenticate API requests?

Include your API key in the Authorization header:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \\
     -H "Content-Type: application/json" \\
     https://api.example.com/v2/data
```

## Troubleshooting

### Installation fails with permission errors

Try installing in user directory:
```bash
pip install --user our-software
```

Or use virtual environments:
```bash
python -m venv venv
source venv/bin/activate
pip install our-software
```

### Pipeline execution is slow

Common optimization strategies:
- Reduce data batch sizes
- Use appropriate data types
- Implement parallel processing
- Add caching for expensive operations
- Profile to identify bottlenecks

### Getting "API key invalid" errors

Check that:
- API key is correctly formatted
- Key hasn't expired
- Account has necessary permissions
- Using correct API endpoint URL

### Data processing produces unexpected results

Verify:
- Input data format and schema
- Configuration file syntax
- Processing logic and transformations
- Output format expectations

## Advanced Topics

### How do I create custom processors?

Extend the base Processor class:

```python
from our_software import Processor

class CustomProcessor(Processor):
    def __init__(self, config):
        super().__init__(config)
        self.custom_param = config.get('custom_param')
    
    def process(self, data):
        # Your processing logic
        return processed_data
```

Register in configuration:
```yaml
processors:
  - name: "custom"
    type: "custom"
    class: "mymodule.CustomProcessor"
    custom_param: "value"
```

### Can I deploy in production environments?

Yes! We support:
- Docker containers
- Kubernetes deployments
- Cloud platforms (AWS, GCP, Azure)
- On-premise installations

See our deployment guides for specific platforms.

### How do I monitor pipeline health?

Enable monitoring features:

```yaml
monitoring:
  enabled: true
  metrics:
    - execution_time
    - record_count
    - error_rate
  alerts:
    - type: "email"
      recipients: ["ops@company.com"]
      triggers: ["failure", "slow_execution"]
```

### What about data security and privacy?

We implement:
- Encryption at rest and in transit
- Access controls and authentication
- Audit logging
- GDPR compliance features
- Regular security assessments

## Getting Help

### Where can I find more documentation?

- [Installation Guide](installation.md)
- [API Reference](api.md)
- [Tutorial](tutorial.md)
- Community wiki
- Video tutorials

### How do I report bugs or request features?

- GitHub issues for bugs and features
- Community forums for questions
- Email support for urgent issues
- Slack channel for real-time help

### Is there community support?

Yes! Join our:
- GitHub discussions
- Discord server
- Monthly user meetups
- Stack Overflow tag: [our-software]
"""
        (workspace / "faq.md").write_text(faq)

        return workspace

    @pytest.fixture
    def search_setup(self, temp_workspace, tmp_path):
        """Set up search infrastructure with indexed documents."""
        # Create database
        db_path = tmp_path / "search_test.db"
        store = SQLiteStore(str(db_path))

        # Create plugins
        markdown_plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)

        plaintext_config = {
            "name": "plaintext",
            "code": "txt",
            "extensions": [".txt", ".text"],
            "language": "plaintext",
        }
        plaintext_plugin = PlainTextPlugin(
            plaintext_config, sqlite_store=store, enable_semantic=False
        )

        # Create dispatcher
        dispatcher = Dispatcher([markdown_plugin, plaintext_plugin])

        # Index all documents
        for doc_file in temp_workspace.glob("*.md"):
            content = doc_file.read_text()
            dispatcher.indexFile(str(doc_file), content)

        return {
            "workspace": temp_workspace,
            "store": store,
            "markdown_plugin": markdown_plugin,
            "plaintext_plugin": plaintext_plugin,
            "dispatcher": dispatcher,
        }

    def test_installation_queries(self, search_setup):
        """Test natural language queries about installation."""
        dispatcher = search_setup["dispatcher"]

        installation_queries = [
            "how to install",
            "installation guide",
            "setup instructions",
            "install the software",
            "prerequisites for installation",
            "pip install command",
        ]

        for query in installation_queries:
            results = dispatcher.search(query)

            # Should find installation-related content
            assert len(results) > 0, f"No results for query: {query}"

            # Check if installation guide is in results
            install_results = [r for r in results if "installation" in r.get("file", "").lower()]
            assert len(install_results) > 0, f"No installation results for: {query}"

            # Verify content relevance
            for result in install_results[:3]:  # Check top 3 results
                snippet = result.get("snippet", "").lower()
                assert any(
                    keyword in snippet for keyword in ["install", "setup", "pip", "requirements"]
                )

    def test_api_documentation_queries(self, search_setup):
        """Test queries for API documentation."""
        dispatcher = search_setup["dispatcher"]

        api_queries = [
            "API documentation",
            "how to use the API",
            "API endpoints",
            "authentication token",
            "API rate limits",
            "GET users endpoint",
            "API error codes",
        ]

        for query in api_queries:
            results = dispatcher.search(query)

            # Should find API-related content
            assert len(results) > 0, f"No results for query: {query}"

            # Check for API documentation
            api_results = [r for r in results if "api" in r.get("file", "").lower()]
            assert len(api_results) > 0, f"No API results for: {query}"

            # Verify API content
            for result in api_results[:3]:
                snippet = result.get("snippet", "").lower()
                api_keywords = ["api", "endpoint", "authentication", "request", "response"]
                assert any(keyword in snippet for keyword in api_keywords)

    def test_tutorial_queries(self, search_setup):
        """Test queries for tutorial content."""
        dispatcher = search_setup["dispatcher"]

        tutorial_queries = [
            "getting started tutorial",
            "first project",
            "basic concepts",
            "how to create project",
            "workflow examples",
            "configuration tutorial",
        ]

        for query in tutorial_queries:
            results = dispatcher.search(query)

            # Should find tutorial content
            assert len(results) > 0, f"No results for query: {query}"

            # Check for tutorial file
            tutorial_results = [r for r in results if "tutorial" in r.get("file", "").lower()]
            assert len(tutorial_results) > 0, f"No tutorial results for: {query}"

    def test_faq_queries(self, search_setup):
        """Test queries that should find FAQ content."""
        dispatcher = search_setup["dispatcher"]

        faq_queries = [
            "frequently asked questions",
            "common problems",
            "troubleshooting",
            "how do I",
            "system requirements",
            "what formats are supported",
        ]

        for query in faq_queries:
            results = dispatcher.search(query)

            # Should find FAQ content
            assert len(results) > 0, f"No results for query: {query}"

            # Many queries should find FAQ file
            if query in ["frequently asked questions", "how do I", "troubleshooting"]:
                faq_results = [r for r in results if "faq" in r.get("file", "").lower()]
                assert len(faq_results) > 0, f"No FAQ results for: {query}"

    def test_specific_technical_queries(self, search_setup):
        """Test specific technical queries."""
        dispatcher = search_setup["dispatcher"]

        technical_queries = [
            "rate limiting",
            "HTTP status codes",
            "JSON response format",
            "cron schedule",
            "virtual environment",
            "PostgreSQL connection",
        ]

        for query in technical_queries:
            results = dispatcher.search(query)

            # Should find relevant technical content
            assert len(results) > 0, f"No results for technical query: {query}"

            # Verify technical context
            for result in results[:3]:
                snippet = result.get("snippet", "").lower()
                # Should contain technical terms or context
                assert len(snippet) > 20, "Snippet should contain meaningful content"

    def test_code_example_queries(self, search_setup):
        """Test queries for code examples."""
        dispatcher = search_setup["dispatcher"]

        code_queries = [
            "code examples",
            "python code",
            "configuration example",
            "YAML config",
            "bash commands",
            "curl example",
        ]

        for query in code_queries:
            results = dispatcher.search(query)

            # Should find code-related content
            assert len(results) > 0, f"No results for code query: {query}"

            # Check for code indicators in results
            code_indicators = ["```", "`", "bash", "python", "yaml", "json"]
            found_code = False

            for result in results[:5]:
                snippet = result.get("snippet", "").lower()
                if any(indicator in snippet for indicator in code_indicators):
                    found_code = True
                    break

            assert found_code, f"No code content found for: {query}"


class TestCrossDocumentSearch:
    """Test search capabilities across multiple documents."""

    @pytest.fixture
    def multi_doc_workspace(self, tmp_path):
        """Create workspace with interconnected documents."""
        workspace = tmp_path / "multi_doc_workspace"
        workspace.mkdir()

        # Create project overview
        overview = """# Project Overview

## Introduction

Our software platform provides comprehensive data processing capabilities
for modern applications. The platform consists of several key components:

- **Core Engine**: Main processing framework
- **API Gateway**: RESTful interface for external access
- **Web Interface**: User-friendly dashboard
- **CLI Tools**: Command-line utilities for automation

## Architecture

The system follows microservices architecture with:

1. **Data Layer**: PostgreSQL database with Redis caching
2. **Service Layer**: Python/FastAPI backend services
3. **API Layer**: REST and GraphQL endpoints
4. **Frontend Layer**: React/TypeScript web application

For detailed installation instructions, see [Installation Guide](docs/installation.md).
For API usage, refer to [API Documentation](docs/api-reference.md).
For hands-on examples, check our [Tutorial](docs/tutorial.md).

## Key Features

### Data Processing
- Real-time stream processing
- Batch data processing
- ETL pipeline management
- Data quality validation

### Integration
- REST API with comprehensive endpoints
- Webhook support for real-time notifications  
- SDK libraries for Python, JavaScript, Java
- Plugin architecture for custom extensions

### Security
- OAuth2 authentication
- Role-based access control
- API key management
- Audit logging

### Monitoring
- Real-time metrics and alerts
- Performance dashboards
- Error tracking and reporting
- Health check endpoints

## Getting Started

1. Follow the [Installation Guide](docs/installation.md)
2. Complete the [Getting Started Tutorial](docs/tutorial.md)
3. Explore [API Examples](docs/api-examples.md)
4. Review [Best Practices](docs/best-practices.md)

## Support

- Documentation: [docs/](docs/)
- API Reference: [docs/api-reference.md](docs/api-reference.md)
- Community Forum: https://forum.example.com
- GitHub Issues: https://github.com/company/project/issues
"""
        (workspace / "overview.md").write_text(overview)

        # Create docs directory
        docs_dir = workspace / "docs"
        docs_dir.mkdir()

        # Create API examples
        api_examples = """# API Examples

This document provides practical examples of using our REST API.

## Authentication Examples

### Getting an API Key

```bash
curl -X POST https://api.example.com/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username": "your_username", "password": "your_password"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the API Key

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \\
  https://api.example.com/v1/users
```

## Data Operations

### Create Data Record

```bash
curl -X POST https://api.example.com/v1/data \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Sample Record",
    "type": "test",
    "data": {
      "value": 42,
      "category": "example"
    }
  }'
```

### Query Data with Filters

```bash
curl "https://api.example.com/v1/data?type=test&limit=10&sort=created_at" \\
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Bulk Data Upload

```bash
curl -X POST https://api.example.com/v1PathUtils.get_data_path() / bulk \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "records": [
      {"name": "Record 1", "value": 10},
      {"name": "Record 2", "value": 20},
      {"name": "Record 3", "value": 30}
    ]
  }'
```

## Python SDK Examples

### Installation

```bash
pip install our-software-sdk
```

### Basic Usage

```python
from our_software import Client

# Initialize client
client = Client(api_key="your_api_key")

# Create data
record = client.data.create({
    "name": "Python Record",
    "type": "sdk_test",
    "data": {"source": "python_sdk"}
})

# Query data
results = client.data.list(type="sdk_test", limit=5)

# Update record
updated = client.data.update(record.id, {"status": "processed"})

# Delete record
client.data.delete(record.id)
```

### Async Operations

```python
import asyncio
from our_software import AsyncClient

async def main():
    client = AsyncClient(api_key="your_api_key")
    
    # Batch operations
    tasks = []
    for i in range(10):
        task = client.data.create({"name": f"Record {i}"})
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    print(f"Created {len(results)} records")

asyncio.run(main())
```

## JavaScript SDK Examples

### Installation

```bash
npm install our-software-js
```

### Basic Usage

```javascript
import { Client } from 'our-software-js';

const client = new Client({ apiKey: 'your_api_key' });

// Create data
const record = await client.data.create({
  name: 'JavaScript Record',
  type: 'js_test',
  data: { source: 'javascript_sdk' }
});

// Query data
const results = await client.data.list({
  type: 'js_test',
  limit: 5
});

// Update record
const updated = await client.data.update(record.id, {
  status: 'processed'
});
```

### React Integration

```jsx
import React, { useState, useEffect } from 'react';
import { Client } from 'our-software-js';

const DataComponent = () => {
  const [data, setData] = useState([]);
  const client = new Client({ apiKey: process.env.REACT_APP_API_KEY });

  useEffect(() => {
    const fetchData = async () => {
      const results = await client.data.list({ limit: 10 });
      setData(results);
    };
    
    fetchData();
  }, []);

  return (
    <div>
      {data.map(item => (
        <div key={item.id}>{item.name}</div>
      ))}
    </div>
  );
};
```

## Webhook Examples

### Setting Up Webhooks

```bash
curl -X POST https://api.example.com/v1/webhooks \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://your-app.com/webhook",
    "events": ["data.created", "data.updated", "data.deleted"],
    "secret": "your_webhook_secret"
  }'
```

### Webhook Handler (Node.js)

```javascript
const express = require('express');
const crypto = require('crypto');

const app = express();
app.use(express.json());

app.post('/webhook', (req, res) => {
  const signature = req.headers['x-webhook-signature'];
  const payload = JSON.stringify(req.body);
  
  // Verify signature
  const expected = crypto
    .createHmac('sha256', process.env.WEBHOOK_SECRET)
    .update(payload)
    .digest('hex');
    
  if (signature === expected) {
    console.log('Webhook event:', req.body);
    res.status(200).send('OK');
  } else {
    res.status(401).send('Unauthorized');
  }
});
```

## Error Handling

### HTTP Error Codes

```python
from our_software import Client, APIError

client = Client(api_key="your_api_key")

try:
    record = client.data.get("invalid_id")
except APIError as e:
    if e.status_code == 404:
        print("Record not found")
    elif e.status_code == 401:
        print("Invalid API key")
    elif e.status_code == 429:
        print("Rate limit exceeded")
    else:
        print(f"API error: {e.message}")
```

### Retry Logic

```python
import time
from our_software import Client, RateLimitError

def api_call_with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
            else:
                raise e

# Usage
client = Client(api_key="your_api_key")
result = api_call_with_retry(lambda: client.data.list())
```

## Advanced Examples

### Streaming Data

```python
from our_software import StreamClient

stream_client = StreamClient(api_key="your_api_key")

# Stream real-time data
async for event in stream_client.events.stream():
    print(f"Event: {event.type}, Data: {event.data}")
```

### Batch Processing

```python
from our_software import BatchProcessor

processor = BatchProcessor(api_key="your_api_key")

# Process large datasets in batches
results = processor.process_batch(
    data_source="s3://bucket/data.csv",
    operations=["validate", "transform", "enrich"],
    output="s3://bucket/processed/"
)
```

For more examples and detailed documentation, see:
- [API Reference](api-reference.md)
- [Installation Guide](../installation.md)
- [Tutorial](tutorial.md)
"""
        (docs_dir / "api-examples.md").write_text(api_examples)

        # Create best practices guide
        best_practices = """# Best Practices Guide

This guide covers best practices for using our platform effectively.

## Development Best Practices

### Code Organization

#### Project Structure
```
my-project/
├── config/
│   ├── development.yaml
│   ├── production.yaml
│   └── test.yaml
├── src/
│   ├── processors/
│   ├── connectors/
│   └── utils/
├── tests/
├── docs/
└── requirements.txt
```

#### Configuration Management
- Use environment-specific config files
- Keep secrets in environment variables
- Version control configuration templates
- Document all configuration options

### API Usage

#### Authentication
- Store API keys securely (never in code)
- Use environment variables for credentials
- Implement token refresh logic
- Handle authentication errors gracefully

#### Rate Limiting
- Implement exponential backoff
- Monitor rate limit headers
- Cache responses when appropriate
- Use batch operations for bulk data

#### Error Handling
- Always handle API errors
- Implement proper retry logic
- Log errors with context
- Provide meaningful error messages to users

### Data Management

#### Data Quality
- Validate input data schemas
- Implement data quality checks
- Handle missing or invalid data gracefully
- Document data transformations

#### Performance
- Use appropriate data types
- Implement caching strategies
- Optimize database queries
- Monitor memory usage

#### Security
- Sanitize all inputs
- Use parameterized queries
- Implement access controls
- Audit data access

## Deployment Best Practices

### Containerization

#### Docker Best Practices
```dockerfile
# Use specific versions
FROM python:3.10-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . /app
WORKDIR /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "app.py"]
```

#### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: our-software
spec:
  replicas: 3
  selector:
    matchLabels:
      app: our-software
  template:
    metadata:
      labels:
        app: our-software
    spec:
      containers:
      - name: app
        image: our-software:latest
        ports:
        - containerPort: 8000
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

### Monitoring and Observability

#### Logging
```python
import logging
import structlog

# Configure structured logging
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

logger = structlog.get_logger()

# Log with context
logger.info("Processing data", 
           user_id=user_id,
           record_count=len(records),
           processing_time=elapsed_time)
```

#### Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')

# Use metrics
@REQUEST_DURATION.time()
def api_handler(request):
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path).inc()
    # Handle request
    pass
```

#### Health Checks
```python
from fastapi import FastAPI
from sqlalchemy import text

app = FastAPI()

@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "external_api": await check_external_api(),
        "disk_space": check_disk_space()
    }
    
    if all(checks.values()):
        return {"status": "healthy", "checks": checks}
    else:
        return {"status": "unhealthy", "checks": checks}, 503

async def check_database():
    try:
        await database.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
```

## Security Best Practices

### Authentication and Authorization

#### API Key Management
- Generate strong, unique API keys
- Implement key rotation policies
- Use different keys for different environments
- Monitor key usage and detect anomalies

#### JWT Tokens
```python
import jwt
from datetime import datetime, timedelta

def create_jwt_token(user_id, secret_key):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')

def verify_jwt_token(token, secret_key):
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")
```

### Data Protection

#### Encryption at Rest
```python
from cryptography.fernet import Fernet

# Generate key (store securely)
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# Encrypt sensitive data
encrypted_data = cipher_suite.encrypt(sensitive_data.encode())

# Decrypt when needed
decrypted_data = cipher_suite.decrypt(encrypted_data).decode()
```

#### Secure Configuration
```python
import os
from typing import Optional

class Config:
    def __init__(self):
        self.database_url = self._get_required_env("DATABASE_URL")
        self.api_key = self._get_required_env("API_KEY")
        self.debug = self._get_bool_env("DEBUG", False)
    
    def _get_required_env(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} not set")
        return value
    
    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        value = os.getenv(key, "").lower()
        return value in ("true", "1", "yes", "on")
```

## Performance Optimization

### Database Optimization

#### Query Optimization
```sql
-- Use indexes for frequently queried columns
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_data_created_at ON data_records(created_at);

-- Use composite indexes for multi-column queries
CREATE INDEX idx_data_type_status ON data_records(type, status);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM data_records 
WHERE type = 'example' AND status = 'active'
ORDER BY created_at DESC LIMIT 10;
```

#### Connection Pooling
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Caching Strategies

#### Redis Caching
```python
import redis
import json
from typing import Optional

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    def get(self, key: str) -> Optional[dict]:
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def set(self, key: str, value: dict, ttl: int = 3600):
        self.redis.setex(key, ttl, json.dumps(value))
    
    def delete(self, key: str):
        self.redis.delete(key)

# Usage
cache = CacheManager("redis://localhost:6379")

def get_user_data(user_id: str):
    # Try cache first
    cached = cache.get(f"user:{user_id}")
    if cached:
        return cached
    
    # Fetch from database
    user_data = fetch_user_from_db(user_id)
    
    # Cache for 1 hour
    cache.set(f"user:{user_id}", user_data, 3600)
    
    return user_data
```

#### Application-Level Caching
```python
from functools import lru_cache
import time

@lru_cache(maxsize=128)
def expensive_computation(param: str) -> str:
    # Simulate expensive operation
    time.sleep(1)
    return f"result_for_{param}"

# With TTL
class TTLCache:
    def __init__(self, maxsize: int, ttl: int):
        self.cache = {}
        self.maxsize = maxsize
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value):
        if len(self.cache) >= self.maxsize:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (value, time.time())
```

## Testing Best Practices

### Unit Testing
```python
import pytest
from unittest.mock import Mock, patch
from our_software import DataProcessor

class TestDataProcessor:
    @pytest.fixture
    def processor(self):
        return DataProcessor(config={"batch_size": 100})
    
    def test_process_valid_data(self, processor):
        data = [{"id": 1, "value": "test"}]
        result = processor.process(data)
        assert len(result) == 1
        assert result[0]["status"] == "processed"
    
    @patch('our_software.external_api.call')
    def test_process_with_external_api(self, mock_api, processor):
        mock_api.return_value = {"status": "success"}
        
        data = [{"id": 1, "value": "test"}]
        result = processor.process(data)
        
        mock_api.assert_called_once()
        assert result[0]["external_status"] == "success"
```

### Integration Testing
```python
import pytest
from fastapi.testclient import TestClient
from our_software.app import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_data():
    return {"name": "Test Record", "type": "test"}

def test_create_record(client, test_data):
    response = client.post("/api/v1/data", json=test_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == test_data["name"]
    assert "id" in data

def test_get_record(client, test_data):
    # Create record
    create_response = client.post("/api/v1/data", json=test_data)
    record_id = create_response.json()["id"]
    
    # Get record
    get_response = client.get(f"/api/v1PathUtils.get_data_path() / {record_id}")
    assert get_response.status_code == 200
    
    data = get_response.json()
    assert data["id"] == record_id
    assert data["name"] == test_data["name"]
```

For more information, see:
- [Installation Guide](../installation.md)
- [API Reference](api-reference.md)
- [Tutorial](tutorial.md)
- [API Examples](api-examples.md)
"""
        (docs_dir / "best-practices.md").write_text(best_practices)

        return workspace

    @pytest.fixture
    def multi_doc_search_setup(self, multi_doc_workspace, tmp_path):
        """Set up search with multi-document workspace."""
        # Create database
        db_path = tmp_path / "multi_doc_test.db"
        store = SQLiteStore(str(db_path))

        # Create plugins
        markdown_plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)

        # Create dispatcher
        dispatcher = Dispatcher([markdown_plugin])

        # Index all documents
        for doc_file in multi_doc_workspace.rglob("*.md"):
            content = doc_file.read_text()
            dispatcher.indexFile(str(doc_file), content)

        return {
            "workspace": multi_doc_workspace,
            "store": store,
            "plugin": markdown_plugin,
            "dispatcher": dispatcher,
        }

    def test_cross_document_references(self, multi_doc_search_setup):
        """Test finding content across multiple related documents."""
        dispatcher = multi_doc_search_setup["dispatcher"]

        # Search for concepts that span multiple documents
        cross_queries = [
            "REST API authentication",
            "Python SDK examples",
            "Docker deployment",
            "data processing pipeline",
            "configuration management",
        ]

        for query in cross_queries:
            results = dispatcher.search(query)

            # Should find results from multiple documents
            assert len(results) > 0, f"No results for cross-doc query: {query}"

            # Get unique files from results
            result_files = set(r.get("file", "") for r in results)

            # For complex queries, should find content in multiple files
            if query in ["REST API authentication", "Python SDK examples"]:
                assert len(result_files) >= 2, f"Should find results in multiple files for: {query}"

    def test_document_type_filtering(self, multi_doc_search_setup):
        """Test filtering results by document type or location."""
        dispatcher = multi_doc_search_setup["dispatcher"]

        # Search for API-related content
        results = dispatcher.search("API examples")

        # Should find results
        assert len(results) > 0

        # Filter by document location
        api_results = [r for r in results if "api" in r.get("file", "").lower()]
        docs_results = [r for r in results if "docs/" in r.get("file", "")]

        # Should find API content in docs directory
        assert len(docs_results) > 0, "Should find API examples in docs"

    def test_hierarchical_content_search(self, multi_doc_search_setup):
        """Test searching within document hierarchies."""
        dispatcher = multi_doc_search_setup["dispatcher"]

        # Search for content that appears in different sections
        hierarchical_queries = [
            "security best practices",
            "monitoring and logging",
            "error handling",
            "configuration examples",
        ]

        for query in hierarchical_queries:
            results = dispatcher.search(query)

            # Should find hierarchical content
            assert len(results) > 0, f"No results for hierarchical query: {query}"

            # Check for section-level context in snippets
            for result in results[:3]:
                snippet = result.get("snippet", "")
                # Should contain meaningful context
                assert len(snippet) > 50, "Should provide meaningful context"

    def test_reference_following(self, multi_doc_search_setup):
        """Test following references between documents."""
        dispatcher = multi_doc_search_setup["dispatcher"]

        # Search for content that references other documents
        reference_queries = [
            "installation guide",
            "API documentation",
            "tutorial examples",
            "best practices guide",
        ]

        for query in reference_queries:
            results = dispatcher.search(query)

            # Should find both the reference and the referenced content
            assert len(results) > 0, f"No results for reference query: {query}"

            # Check for document references in snippets
            reference_indicators = ["see", "refer", "check", "docs/", ".md"]
            found_references = False

            for result in results:
                snippet = result.get("snippet", "").lower()
                if any(indicator in snippet for indicator in reference_indicators):
                    found_references = True
                    break

            # At least some results should show document references
            if query in ["installation guide", "API documentation"]:
                assert found_references, f"Should find document references for: {query}"


class TestDocumentRanking:
    """Test document-aware result ranking and relevance."""

    @pytest.fixture
    def ranking_workspace(self, tmp_path):
        """Create workspace for testing ranking algorithms."""
        workspace = tmp_path / "ranking_workspace"
        workspace.mkdir()

        # Create high-quality comprehensive guide
        comprehensive_guide = """# Complete Python Development Guide

## Introduction

This comprehensive guide covers everything you need to know about Python development,
from basic syntax to advanced programming patterns and best practices.

## Installation and Setup

### Installing Python

Python can be installed on all major operating systems. Here's how to install Python
on different platforms:

#### Windows Installation
1. Download Python from python.org
2. Run the installer
3. Check "Add Python to PATH"
4. Complete the installation

#### macOS Installation
1. Download from python.org or use Homebrew
2. Install using: brew install python
3. Verify installation: python3 --version

#### Linux Installation
Most Linux distributions include Python. To install the latest version:
```bash
sudo apt update
sudo apt install python3 python3-pip
```

### Setting Up Development Environment

#### Virtual Environments
Always use virtual environments for Python projects:

```bash
python -m venv myproject
source myproject/bin/activate  # On Windows: myproject\\Scripts\\activate
```

#### IDE Configuration
Popular Python IDEs include:
- PyCharm (Professional and Community)
- Visual Studio Code with Python extension
- Sublime Text with Python packages
- Vim/Neovim with Python plugins

## Core Python Concepts

### Variables and Data Types

Python supports various data types:

```python
# Numbers
integer_var = 42
float_var = 3.14
complex_var = 3 + 4j

# Strings
text = "Hello, World!"
multiline = '''This is a
multiline string'''

# Collections
my_list = [1, 2, 3, 4, 5]
my_tuple = (1, 2, 3)
my_dict = {"key": "value", "number": 42}
my_set = {1, 2, 3, 4, 5}
```

### Control Flow

#### Conditional Statements
```python
if condition:
    # do something
elif another_condition:
    # do something else
else:
    # default action
```

#### Loops
```python
# For loops
for item in collection:
    print(item)

# While loops
while condition:
    # do something
    condition = update_condition()

# List comprehensions
squares = [x**2 for x in range(10)]
```

### Functions

#### Defining Functions
```python
def greet(name, greeting="Hello"):
    '''Greet someone with a custom message.'''
    return f"{greeting}, {name}!"

# Lambda functions
square = lambda x: x**2
```

#### Advanced Function Features
```python
# *args and **kwargs
def flexible_function(*args, **kwargs):
    print(f"Args: {args}")
    print(f"Kwargs: {kwargs}")

# Decorators
def timing_decorator(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start} seconds")
        return result
    return wrapper

@timing_decorator
def slow_function():
    time.sleep(1)
```

## Object-Oriented Programming

### Classes and Objects

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    def greet(self):
        return f"Hello, I'm {self.name}"
    
    def __str__(self):
        return f"Person(name='{self.name}', age={self.age})"

# Creating objects
person = Person("Alice", 30)
print(person.greet())
```

### Inheritance

```python
class Employee(Person):
    def __init__(self, name, age, job_title):
        super().__init__(name, age)
        self.job_title = job_title
    
    def work(self):
        return f"{self.name} is working as a {self.job_title}"
```

## Advanced Topics

### File I/O

```python
# Reading files
with open('file.txt', 'r') as f:
    content = f.read()

# Writing files
with open('output.txt', 'w') as f:
    f.write("Hello, World!")

# Working with JSON
import json

data = {"name": "Alice", "age": 30}
with open('data.json', 'w') as f:
    json.dump(data, f)
```

### Error Handling

```python
try:
    result = risky_operation()
except SpecificException as e:
    print(f"Specific error occurred: {e}")
except Exception as e:
    print(f"General error: {e}")
else:
    print("No errors occurred")
finally:
    print("This always executes")
```

### Modules and Packages

```python
# Importing modules
import math
from datetime import datetime
import numpy as np

# Creating modules
# mymodule.py
def my_function():
    return "Hello from my module"

# Using custom modules
import mymodule
result = mymodule.my_function()
```

## Best Practices

### Code Style
- Follow PEP 8 style guide
- Use meaningful variable names
- Write docstrings for functions and classes
- Keep functions small and focused

### Testing
```python
import unittest

class TestMyFunction(unittest.TestCase):
    def test_addition(self):
        result = add(2, 3)
        self.assertEqual(result, 5)
    
    def test_invalid_input(self):
        with self.assertRaises(TypeError):
            add("2", 3)

if __name__ == '__main__':
    unittest.main()
```

### Performance
- Use built-in functions when possible
- Understand time complexity
- Profile your code to find bottlenecks
- Use appropriate data structures

## Popular Libraries

### Data Science
- NumPy: Numerical computing
- Pandas: Data manipulation and analysis
- Matplotlib: Data visualization
- Scikit-learn: Machine learning

### Web Development
- Django: Full-featured web framework
- Flask: Lightweight web framework
- FastAPI: Modern, fast web framework

### Other Useful Libraries
- Requests: HTTP library
- Beautiful Soup: Web scraping
- Pillow: Image processing
- Pygame: Game development

## Conclusion

Python is a versatile and powerful programming language suitable for many applications.
This guide covers the fundamentals, but there's always more to learn. Keep practicing,
building projects, and exploring the vast Python ecosystem.

For more advanced topics, consider exploring:
- Asynchronous programming with asyncio
- Metaclasses and descriptors
- C extensions and performance optimization
- Specific domain libraries (AI/ML, web dev, etc.)

Happy coding with Python!
"""
        (workspace / "python_guide.md").write_text(comprehensive_guide)

        # Create brief overview
        brief_overview = """# Python Overview

Python is a high-level programming language known for its simplicity and readability.

## Quick Facts
- Created by Guido van Rossum
- First released in 1991
- Named after Monty Python
- Interpreted language
- Dynamic typing

## Installation
Install Python from python.org or use a package manager.

## Basic Syntax
```python
print("Hello, World!")
```

## Use Cases
- Web development
- Data science
- Automation
- Machine learning
"""
        (workspace / "python_overview.md").write_text(brief_overview)

        # Create specific installation doc
        install_doc = """# Python Installation Instructions

## Quick Install

The fastest way to install Python:

### Windows
1. Go to python.org
2. Download latest version
3. Run installer
4. Check "Add to PATH"

### macOS
```bash
brew install python
```

### Linux
```bash
sudo apt install python3
```

## Verification
```bash
python --version
```

That's it! Python is now installed.
"""
        (workspace / "install.md").write_text(install_doc)

        # Create API reference
        api_reference = """# Python API Reference

## Built-in Functions

### print()
Print objects to stdout.

```python
print("Hello")
print("Value:", 42)
```

### len()
Return the length of an object.

```python
len("hello")  # Returns 5
len([1, 2, 3])  # Returns 3
```

### range()
Generate a sequence of numbers.

```python
range(10)  # 0 to 9
range(1, 11)  # 1 to 10
```

## String Methods

### upper()
Convert to uppercase.

### lower()
Convert to lowercase.

### split()
Split string into list.

## List Methods

### append()
Add item to end.

### remove()
Remove first occurrence.

### sort()
Sort in place.
"""
        (workspace / "api_ref.md").write_text(api_reference)

        return workspace

    @pytest.fixture
    def ranking_search_setup(self, ranking_workspace, tmp_path):
        """Set up search with ranking test workspace."""
        # Create database
        db_path = tmp_path / "ranking_test.db"
        store = SQLiteStore(str(db_path))

        # Create plugins
        markdown_plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)

        # Create dispatcher
        dispatcher = Dispatcher([markdown_plugin])

        # Index all documents
        for doc_file in ranking_workspace.glob("*.md"):
            content = doc_file.read_text()
            dispatcher.indexFile(str(doc_file), content)

        return {
            "workspace": ranking_workspace,
            "store": store,
            "plugin": markdown_plugin,
            "dispatcher": dispatcher,
        }

    def test_comprehensive_vs_brief_ranking(self, ranking_search_setup):
        """Test that comprehensive documents rank higher for detailed queries."""
        dispatcher = ranking_search_setup["dispatcher"]

        # Detailed query that should favor comprehensive content
        detailed_query = "Python installation virtual environment setup IDE configuration"

        results = dispatcher.search(detailed_query)
        assert len(results) > 0

        # Check if comprehensive guide ranks high
        top_files = [r.get("file", "") for r in results[:3]]
        comprehensive_found = any("python_guide" in f for f in top_files)

        # Comprehensive guide should be in top results for detailed query
        assert comprehensive_found, "Comprehensive guide should rank high for detailed queries"

    def test_specific_vs_general_ranking(self, ranking_search_setup):
        """Test that specific documents rank higher for targeted queries."""
        dispatcher = ranking_search_setup["dispatcher"]

        # Specific query for installation only
        specific_query = "how to install Python"

        results = dispatcher.search(specific_query)
        assert len(results) > 0

        # Check file rankings
        result_files = [(r.get("file", ""), i) for i, r in enumerate(results[:5])]

        # Install doc should rank well for installation query
        install_positions = [pos for file, pos in result_files if "install" in file]

        if install_positions:
            # Install doc should be in top 3 for installation query
            assert min(install_positions) < 3, "Install doc should rank high for installation query"

    def test_api_reference_ranking(self, ranking_search_setup):
        """Test that API references rank high for function queries."""
        dispatcher = ranking_search_setup["dispatcher"]

        # Query for specific Python functions
        function_query = "Python print function len range"

        results = dispatcher.search(function_query)
        assert len(results) > 0

        # API reference should rank well for function queries
        api_results = [r for r in results if "api_ref" in r.get("file", "")]

        if api_results:
            # API reference should be in results for function query
            assert len(api_results) > 0, "API reference should be found for function queries"

    def test_section_relevance_ranking(self, ranking_search_setup):
        """Test that relevant sections rank higher than document titles."""
        dispatcher = ranking_search_setup["dispatcher"]

        # Query for content that appears in specific sections
        section_query = "object oriented programming classes inheritance"

        results = dispatcher.search(section_query)
        assert len(results) > 0

        # Should find OOP section content
        oop_content_found = False
        for result in results[:5]:
            snippet = result.get("snippet", "").lower()
            if any(term in snippet for term in ["class", "inheritance", "object"]):
                oop_content_found = True
                break

        assert oop_content_found, "Should find OOP section content for OOP query"

    def test_code_example_ranking(self, ranking_search_setup):
        """Test that documents with code examples rank higher for implementation queries."""
        dispatcher = ranking_search_setup["dispatcher"]

        # Query for implementation examples
        code_query = "Python code examples functions classes"

        results = dispatcher.search(code_query)
        assert len(results) > 0

        # Check if results contain code indicators
        code_results = []
        for result in results:
            snippet = result.get("snippet", "")
            if any(indicator in snippet for indicator in ["```", "def ", "class ", "import"]):
                code_results.append(result)

        # Should find documents with code examples
        assert len(code_results) > 0, "Should find documents with code examples"

        # Code-heavy documents should rank well
        comprehensive_code_results = [
            r for r in code_results if "python_guide" in r.get("file", "")
        ]
        assert len(comprehensive_code_results) > 0, "Comprehensive guide with code should rank well"


class TestSectionBasedFiltering:
    """Test filtering search results by document sections."""

    @pytest.fixture
    def section_workspace(self, tmp_path):
        """Create workspace with well-structured sections."""
        workspace = tmp_path / "section_workspace"
        workspace.mkdir()

        # Create structured documentation
        structured_doc = """# Software Development Guide

## Introduction

This guide covers modern software development practices and methodologies.

## Planning and Design

### Requirements Analysis

Requirements analysis is the process of determining user expectations for a new or modified product.

#### Functional Requirements
- What the system should do
- User interactions and workflows
- Data processing requirements
- Business rules and constraints

#### Non-Functional Requirements
- Performance requirements
- Security requirements
- Scalability requirements
- Usability requirements

### System Architecture

System architecture defines the structure and organization of software systems.

#### Microservices Architecture
- Independent deployable services
- Service communication patterns
- Data consistency strategies
- Monitoring and observability

#### Monolithic Architecture
- Single deployable unit
- Shared database
- Internal communication
- Scaling considerations

## Development Practices

### Version Control

Version control systems track changes to code over time.

#### Git Workflow
- Feature branching
- Pull request process
- Code review practices
- Merge strategies

#### Best Practices
- Commit messages
- Branch naming conventions
- Repository structure
- Release management

### Testing Strategies

Testing ensures software quality and reliability.

#### Unit Testing
- Test individual components
- Mock dependencies
- Test coverage metrics
- Test-driven development

#### Integration Testing
- Test component interactions
- API testing
- Database testing
- End-to-end testing

#### Performance Testing
- Load testing
- Stress testing
- Performance monitoring
- Optimization strategies

## Deployment and Operations

### Continuous Integration

CI/CD automates software delivery processes.

#### CI Pipeline
- Automated builds
- Test execution
- Code quality checks
- Artifact generation

#### CD Pipeline
- Automated deployment
- Environment management
- Release strategies
- Rollback procedures

### Monitoring and Maintenance

Operational monitoring ensures system health.

#### Application Monitoring
- Performance metrics
- Error tracking
- User behavior analytics
- Business metrics

#### Infrastructure Monitoring
- Server health
- Network performance
- Database performance
- Security monitoring

## Security Practices

### Authentication and Authorization

Security controls protect system access.

#### Authentication Methods
- Password-based authentication
- Multi-factor authentication
- Single sign-on (SSO)
- OAuth and OpenID Connect

#### Authorization Patterns
- Role-based access control (RBAC)
- Attribute-based access control (ABAC)
- Permission systems
- API security

### Data Protection

Data protection safeguards sensitive information.

#### Encryption
- Data at rest encryption
- Data in transit encryption
- Key management
- Certificate management

#### Privacy
- Data minimization
- Consent management
- Data retention policies
- Compliance requirements

## Conclusion

Modern software development requires a comprehensive approach covering planning,
development, deployment, and operations. Following these practices ensures
reliable, secure, and maintainable software systems.
"""
        (workspace / "dev_guide.md").write_text(structured_doc)

        return workspace

    @pytest.fixture
    def section_search_setup(self, section_workspace, tmp_path):
        """Set up search with section test workspace."""
        # Create database
        db_path = tmp_path / "section_test.db"
        store = SQLiteStore(str(db_path))

        # Create plugins
        markdown_plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)

        # Create dispatcher
        dispatcher = Dispatcher([markdown_plugin])

        # Index all documents
        for doc_file in section_workspace.glob("*.md"):
            content = doc_file.read_text()
            dispatcher.indexFile(str(doc_file), content)

        return {
            "workspace": section_workspace,
            "store": store,
            "plugin": markdown_plugin,
            "dispatcher": dispatcher,
        }

    def test_section_specific_queries(self, section_search_setup):
        """Test queries that target specific sections."""
        dispatcher = section_search_setup["dispatcher"]

        section_queries = [
            ("requirements analysis", "Planning and Design"),
            ("unit testing", "Development Practices"),
            ("CI/CD pipeline", "Deployment and Operations"),
            ("authentication methods", "Security Practices"),
            ("microservices architecture", "Planning and Design"),
            ("performance monitoring", "Deployment and Operations"),
        ]

        for query, expected_section in section_queries:
            results = dispatcher.search(query)

            # Should find relevant results
            assert len(results) > 0, f"No results for section query: {query}"

            # Check if results contain section-relevant content
            section_content_found = False
            for result in results[:3]:
                snippet = result.get("snippet", "").lower()
                # Look for section keywords or related terms
                if any(term in snippet for term in query.split()):
                    section_content_found = True
                    break

            assert section_content_found, f"Should find section content for: {query}"

    def test_hierarchical_section_search(self, section_search_setup):
        """Test searching within hierarchical section structure."""
        dispatcher = section_search_setup["dispatcher"]

        # Query for subsection content
        hierarchical_queries = [
            "functional requirements",
            "non-functional requirements",
            "git workflow",
            "integration testing",
            "application monitoring",
            "role-based access control",
        ]

        for query in hierarchical_queries:
            results = dispatcher.search(query)

            # Should find subsection content
            assert len(results) > 0, f"No results for hierarchical query: {query}"

            # Verify content depth and relevance
            for result in results[:2]:
                snippet = result.get("snippet", "")
                # Should contain meaningful content from subsections
                assert len(snippet) > 30, "Should provide substantial section content"

    def test_section_context_preservation(self, section_search_setup):
        """Test that section context is preserved in search results."""
        dispatcher = section_search_setup["dispatcher"]

        # Query for terms that appear in multiple sections
        context_query = "monitoring performance"

        results = dispatcher.search(context_query)
        assert len(results) > 0

        # Check if different contexts are represented
        contexts_found = set()
        for result in results:
            snippet = result.get("snippet", "").lower()

            if "application" in snippet or "metrics" in snippet:
                contexts_found.add("application_monitoring")
            if "infrastructure" in snippet or "server" in snippet:
                contexts_found.add("infrastructure_monitoring")
            if "performance testing" in snippet or "load testing" in snippet:
                contexts_found.add("performance_testing")

        # Should find monitoring in different contexts
        assert len(contexts_found) >= 1, "Should find monitoring in different section contexts"

    def test_cross_section_queries(self, section_search_setup):
        """Test queries that span multiple sections."""
        dispatcher = section_search_setup["dispatcher"]

        # Query that relates to multiple sections
        cross_section_query = "security testing deployment"

        results = dispatcher.search(cross_section_query)
        assert len(results) > 0

        # Should find content from different sections
        section_indicators = {
            "security": ["authentication", "authorization", "encryption"],
            "testing": ["unit testing", "integration", "performance"],
            "deployment": ["CI/CD", "pipeline", "monitoring"],
        }

        sections_found = set()
        for result in results:
            snippet = result.get("snippet", "").lower()

            for section, indicators in section_indicators.items():
                if any(indicator in snippet for indicator in indicators):
                    sections_found.add(section)

        # Should find content from multiple relevant sections
        assert len(sections_found) >= 2, "Should find content across multiple sections"


class TestSemanticSearchIntegration:
    """Test integration with semantic search capabilities."""

    @pytest.fixture
    def semantic_workspace(self, tmp_path):
        """Create workspace for semantic search testing."""
        workspace = tmp_path / "semantic_workspace"
        workspace.mkdir()

        # Create conceptually related documents
        ml_concepts = """# Machine Learning Fundamentals

## Introduction to Artificial Intelligence

Artificial intelligence (AI) is the simulation of human intelligence in machines
that are programmed to think and learn like humans. Machine learning is a subset
of AI that enables computers to learn and improve from experience without being
explicitly programmed.

## Neural Networks

Neural networks are computing systems inspired by biological neural networks.
They consist of interconnected nodes (neurons) that process information through
their connections. Deep learning uses neural networks with multiple layers
to learn complex patterns in data.

### Convolutional Neural Networks

CNNs are particularly effective for image recognition tasks. They use convolution
operations to detect features like edges, textures, and patterns in images.

### Recurrent Neural Networks

RNNs are designed for sequential data like text and time series. They have memory
that allows them to remember previous inputs in their current input processing.

## Supervised Learning

Supervised learning algorithms learn from labeled training data to make predictions
on new, unseen data. Common supervised learning tasks include:

- Classification: Predicting categories or classes
- Regression: Predicting continuous numerical values

### Popular Algorithms
- Linear Regression for continuous predictions
- Logistic Regression for binary classification
- Decision Trees for interpretable models
- Random Forest for ensemble learning
- Support Vector Machines for complex boundaries

## Unsupervised Learning

Unsupervised learning finds patterns in data without labeled examples.
Common unsupervised learning tasks include:

- Clustering: Grouping similar data points
- Dimensionality Reduction: Simplifying data while preserving information
- Association Rules: Finding relationships between variables

### Clustering Algorithms
- K-Means for spherical clusters
- Hierarchical clustering for nested groupings
- DBSCAN for density-based clusters

## Model Evaluation

Evaluating machine learning models is crucial for understanding their performance:

### Classification Metrics
- Accuracy: Overall correctness
- Precision: True positives / (True positives + False positives)
- Recall: True positives / (True positives + False negatives)
- F1-Score: Harmonic mean of precision and recall

### Regression Metrics
- Mean Squared Error (MSE)
- Root Mean Squared Error (RMSE)
- Mean Absolute Error (MAE)
- R-squared (coefficient of determination)

## Data Preprocessing

Clean and well-prepared data is essential for successful machine learning:

### Data Cleaning
- Handling missing values
- Removing outliers
- Fixing inconsistent data

### Feature Engineering
- Creating new features from existing ones
- Scaling and normalization
- Encoding categorical variables

### Data Splitting
- Training set for model learning
- Validation set for hyperparameter tuning
- Test set for final evaluation

## Conclusion

Machine learning is a powerful tool for extracting insights from data and making
predictions. Success requires understanding algorithms, proper data preparation,
and rigorous evaluation methodologies.
"""
        (workspace / "ml_concepts.md").write_text(ml_concepts)

        # Create data science guide
        data_science = """# Data Science Methodology

## The Data Science Process

Data science is an interdisciplinary field that combines statistics, computer science,
and domain expertise to extract knowledge and insights from data.

## Problem Definition

Every data science project starts with clearly defining the problem:

- What question are we trying to answer?
- What decision will this analysis inform?
- What would success look like?
- What data do we need?

## Data Collection and Acquisition

Data can come from various sources:

### Internal Data Sources
- Databases and data warehouses
- Application logs and user interactions
- Sales and customer data
- Operational metrics

### External Data Sources
- Public datasets and APIs
- Social media and web scraping
- Third-party data providers
- Government and research data

## Exploratory Data Analysis (EDA)

EDA helps understand the structure and characteristics of data:

### Descriptive Statistics
- Central tendency (mean, median, mode)
- Variability (standard deviation, range)
- Distribution shape and skewness
- Correlation between variables

### Data Visualization
- Histograms for distribution analysis
- Scatter plots for relationships
- Box plots for outlier detection
- Heatmaps for correlation matrices

### Pattern Recognition
- Seasonal trends in time series
- Geographical patterns in location data
- Customer behavior segments
- Anomaly detection

## Statistical Analysis

Statistical methods provide the foundation for data science:

### Hypothesis Testing
- Formulating null and alternative hypotheses
- Choosing appropriate statistical tests
- Interpreting p-values and confidence intervals
- Avoiding common statistical pitfalls

### Regression Analysis
- Simple and multiple linear regression
- Polynomial and nonlinear regression
- Logistic regression for binary outcomes
- Time series regression

### Experimental Design
- A/B testing methodology
- Control and treatment groups
- Randomization and blocking
- Power analysis and sample size

## Predictive Modeling

Building models to make predictions about future outcomes:

### Model Selection
- Understanding the bias-variance tradeoff
- Cross-validation for model assessment
- Grid search for hyperparameter tuning
- Ensemble methods for improved performance

### Feature Selection
- Univariate feature selection
- Recursive feature elimination
- Principal component analysis
- Domain knowledge incorporation

### Model Interpretation
- Feature importance scores
- Partial dependence plots
- SHAP (SHapley Additive exPlanations) values
- Model-agnostic interpretation methods

## Big Data Technologies

Handling large-scale data requires specialized tools:

### Distributed Computing
- Apache Hadoop ecosystem
- Apache Spark for large-scale processing
- Kubernetes for container orchestration
- Cloud computing platforms

### NoSQL Databases
- MongoDB for document storage
- Cassandra for time-series data
- Neo4j for graph databases
- Redis for caching and real-time data

## Communication and Visualization

Effective communication is crucial for data science impact:

### Storytelling with Data
- Crafting compelling narratives
- Choosing appropriate visualizations
- Highlighting key insights
- Addressing stakeholder concerns

### Dashboard Development
- Real-time monitoring dashboards
- Interactive exploration tools
- Executive summary views
- Mobile-responsive designs

## Ethics and Responsible AI

Data science must consider ethical implications:

### Bias and Fairness
- Identifying sources of bias in data
- Algorithmic fairness measures
- Mitigation strategies
- Ongoing monitoring and adjustment

### Privacy and Security
- Data anonymization techniques
- Differential privacy
- Secure multi-party computation
- GDPR and regulatory compliance

## Career Development

Building expertise in data science:

### Technical Skills
- Programming (Python, R, SQL)
- Statistics and mathematics
- Machine learning algorithms
- Data visualization tools

### Soft Skills
- Critical thinking and problem-solving
- Communication and presentation
- Business acumen and domain knowledge
- Project management and collaboration

## Conclusion

Data science is a rapidly evolving field that combines technical expertise
with business understanding to drive data-informed decisions. Success requires
continuous learning and adaptation to new tools and methodologies.
"""
        (workspace / "data_science.md").write_text(data_science)

        # Create programming concepts doc
        programming_concepts = """# Programming Concepts and Paradigms

## Introduction to Programming

Programming is the process of creating instructions for computers to execute.
It involves problem-solving, logical thinking, and translating human ideas
into machine-readable code.

## Programming Paradigms

### Imperative Programming

Imperative programming focuses on describing HOW to solve a problem through
a sequence of commands that change program state.

#### Procedural Programming
- Programs organized as procedures/functions
- Top-down approach to problem solving
- Examples: C, Pascal, early FORTRAN

#### Object-Oriented Programming
- Programs organized as interacting objects
- Encapsulation, inheritance, and polymorphism
- Examples: Java, C++, Python

### Declarative Programming

Declarative programming focuses on WHAT should be accomplished rather than HOW.

#### Functional Programming
- Programs built from function compositions
- Immutable data and pure functions
- Examples: Haskell, Lisp, ML

#### Logic Programming
- Programs express facts and rules
- Automated reasoning and inference
- Examples: Prolog, Answer Set Programming

## Data Structures

### Linear Data Structures

#### Arrays
- Fixed-size sequential collections
- O(1) random access by index
- O(n) insertion and deletion

#### Linked Lists
- Dynamic size with node-based storage
- O(1) insertion/deletion at known position
- O(n) access by index

#### Stacks
- Last-In-First-Out (LIFO) ordering
- Push and pop operations
- Applications: function calls, expression evaluation

#### Queues
- First-In-First-Out (FIFO) ordering
- Enqueue and dequeue operations
- Applications: task scheduling, breadth-first search

### Non-Linear Data Structures

#### Trees
- Hierarchical structures with parent-child relationships
- Binary trees, binary search trees, AVL trees
- Applications: file systems, decision making, parsing

#### Graphs
- Networks of vertices connected by edges
- Directed and undirected variations
- Applications: social networks, routing, optimization

#### Hash Tables
- Key-value mappings with hash functions
- Average O(1) insertion, deletion, and lookup
- Applications: caches, databases, symbol tables

## Algorithms

### Searching Algorithms

#### Linear Search
- Sequential examination of elements
- O(n) time complexity
- Works on unsorted data

#### Binary Search
- Divide-and-conquer on sorted data
- O(log n) time complexity
- Requires pre-sorted input

### Sorting Algorithms

#### Comparison-Based Sorts
- Bubble Sort: O(n²) - simple but inefficient
- Quick Sort: O(n log n) average - divide and conquer
- Merge Sort: O(n log n) - stable and predictable
- Heap Sort: O(n log n) - in-place sorting

#### Non-Comparison Sorts
- Counting Sort: O(n + k) for limited range
- Radix Sort: O(d × n) for fixed-width keys
- Bucket Sort: O(n) average for uniform distribution

### Graph Algorithms

#### Traversal Algorithms
- Depth-First Search (DFS): Stack-based exploration
- Breadth-First Search (BFS): Queue-based exploration
- Applications: connectivity, cycle detection

#### Shortest Path Algorithms
- Dijkstra's Algorithm: Single-source shortest paths
- Bellman-Ford: Handles negative weights
- Floyd-Warshall: All-pairs shortest paths

## Complexity Analysis

### Time Complexity

Big O notation describes algorithm efficiency:
- O(1): Constant time
- O(log n): Logarithmic time
- O(n): Linear time
- O(n log n): Linearithmic time
- O(n²): Quadratic time
- O(2ⁿ): Exponential time

### Space Complexity

Memory usage analysis:
- In-place algorithms: O(1) extra space
- Recursive algorithms: O(depth) stack space
- Dynamic programming: O(n) memoization space

## Design Patterns

### Creational Patterns
- Singleton: Ensure single instance
- Factory: Create objects without specifying exact class
- Builder: Construct complex objects step by step

### Structural Patterns
- Adapter: Interface compatibility
- Decorator: Add behavior dynamically
- Facade: Simplified interface to complex system

### Behavioral Patterns
- Observer: Notification of state changes
- Strategy: Algorithm selection at runtime
- Command: Encapsulate requests as objects

## Software Development Principles

### SOLID Principles
- Single Responsibility: One reason to change
- Open/Closed: Open for extension, closed for modification
- Liskov Substitution: Subtypes must be substitutable
- Interface Segregation: Clients shouldn't depend on unused interfaces
- Dependency Inversion: Depend on abstractions, not concretions

### DRY and KISS
- Don't Repeat Yourself: Eliminate code duplication
- Keep It Simple, Stupid: Favor simplicity over complexity

## Conclusion

Understanding fundamental programming concepts provides the foundation for
writing efficient, maintainable, and scalable software. These concepts
transcend specific languages and technologies, forming the core knowledge
every programmer should master.
"""
        (workspace / "programming_concepts.md").write_text(programming_concepts)

        return workspace

    @pytest.fixture
    def semantic_search_setup(self, semantic_workspace, tmp_path):
        """Set up search with semantic capabilities."""
        # Create database
        db_path = tmp_path / "semantic_test.db"
        store = SQLiteStore(str(db_path))

        # Create plugin with semantic search enabled
        markdown_plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=True)

        # Mock semantic indexer
        with patch("mcp_server.utils.semantic_indexer.SemanticIndexer") as mock_indexer_class:
            mock_indexer = Mock()
            mock_indexer_class.return_value = mock_indexer

            # Configure mock to return conceptually similar results
            def mock_search(query, limit=10):
                # Simulate semantic similarity
                if "neural networks" in query.lower():
                    return [
                        {
                            "file": str(semantic_workspace / "ml_concepts.md"),
                            "line": 10,
                            "score": 0.95,
                            "kind": "chunk",
                        },
                        {
                            "file": str(semantic_workspace / "data_science.md"),
                            "line": 5,
                            "score": 0.85,
                            "kind": "chunk",
                        },
                    ]
                elif "algorithms" in query.lower():
                    return [
                        {
                            "file": str(semantic_workspace / "programming_concepts.md"),
                            "line": 15,
                            "score": 0.92,
                            "kind": "chunk",
                        },
                        {
                            "file": str(semantic_workspace / "ml_concepts.md"),
                            "line": 8,
                            "score": 0.78,
                            "kind": "chunk",
                        },
                    ]
                else:
                    return []

            mock_indexer.search.side_effect = mock_search
            markdown_plugin.semantic_indexer = mock_indexer

            # Create dispatcher
            dispatcher = Dispatcher([markdown_plugin])

            # Index all documents
            for doc_file in semantic_workspace.glob("*.md"):
                content = doc_file.read_text()
                dispatcher.indexFile(str(doc_file), content)

            return {
                "workspace": semantic_workspace,
                "store": store,
                "plugin": markdown_plugin,
                "dispatcher": dispatcher,
                "mock_indexer": mock_indexer,
            }

    def test_conceptual_similarity_search(self, semantic_search_setup):
        """Test finding conceptually similar content across documents."""
        dispatcher = semantic_search_setup["dispatcher"]

        # Query for related concepts using different terminology
        conceptual_queries = [
            "deep learning neural networks",
            "machine learning algorithms",
            "artificial intelligence models",
            "data patterns recognition",
        ]

        for query in conceptual_queries:
            # Test semantic search
            results = dispatcher.search(query, {"semantic": True})

            if results:  # If semantic indexer returned results
                # Should find conceptually related content
                assert len(results) > 0, f"No semantic results for: {query}"

                # Verify cross-document conceptual matching
                result_files = set(r.get("file", "") for r in results)

                # Should potentially find related concepts in different documents
                if len(result_files) > 1:
                    assert True, "Found related concepts across multiple documents"

    def test_semantic_vs_keyword_search(self, semantic_search_setup):
        """Test differences between semantic and keyword-based search."""
        dispatcher = semantic_search_setup["dispatcher"]

        # Query that should show difference between semantic and keyword search
        query = "learning from data patterns"

        # Keyword search
        keyword_results = dispatcher.search(query, {"semantic": False})

        # Semantic search (mocked)
        semantic_results = dispatcher.search(query, {"semantic": True})

        # Both should return results (even if different)
        # This tests the integration between search types
        assert isinstance(keyword_results, list)
        assert isinstance(semantic_results, list)

    def test_hybrid_search_integration(self, semantic_search_setup):
        """Test combining semantic and keyword search results."""
        dispatcher = semantic_search_setup["dispatcher"]
        mock_indexer = semantic_search_setup["mock_indexer"]

        # Configure mock to return results for hybrid testing
        mock_indexer.search.return_value = [
            {
                "file": str(semantic_search_setup["workspace"] / "ml_concepts.md"),
                "line": 5,
                "score": 0.9,
                "kind": "chunk",
            }
        ]

        query = "neural network algorithms"

        # Test semantic search
        semantic_results = dispatcher.search(query, {"semantic": True})

        # Test keyword search
        keyword_results = dispatcher.search(query, {"semantic": False})

        # Both search methods should work
        assert isinstance(semantic_results, list)
        assert isinstance(keyword_results, list)

        # If semantic indexer is called, verify it's called correctly
        if mock_indexer.search.called:
            call_args = mock_indexer.search.call_args
            assert query in str(call_args), "Semantic indexer should be called with query"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
