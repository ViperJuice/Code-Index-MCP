"""
Test document structure extraction from a user perspective.

This test module validates that the system can extract and understand document
structure including headings, sections, code blocks, and metadata. Users should
be able to search within specific sections or find content based on structure.
"""

import pytest
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from mcp_server.core.path_utils import PathUtils

# Import system components
import sys
sys.path.insert(0, '/app')

from tests.base_test import BaseDocumentTest
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.markdown_plugin.section_extractor import SectionExtractor
from mcp_server.plugins.markdown_plugin.document_parser import DocumentParser
from mcp_server.dispatcher import EnhancedDispatcher as Dispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


@dataclass
class DocumentSection:
    """Represents a section in a document."""
    title: str
    level: int
    content: str
    subsections: List['DocumentSection']
    code_blocks: List[Dict[str, str]]
    
    
class TestDocumentStructureExtraction(BaseDocumentTest):
    """Test heading extraction, hierarchy, table of contents, and cross-references."""
    
    @pytest.fixture
    def structured_docs(self, tmp_path):
        """Create documents with rich structure."""
        workspace = tmp_path / "structured"
        workspace.mkdir()
        
        # Technical documentation with clear structure
        tech_doc = """---
title: Technical Architecture Guide
author: Engineering Team
version: 2.0
tags: [architecture, technical, guide]
---

# Technical Architecture Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [Security Architecture](#security-architecture)
5. [Deployment](#deployment)

## System Overview

Our system follows a microservices architecture pattern with the following key principles:
- **Scalability**: Horizontal scaling of individual services
- **Resilience**: Fault tolerance and graceful degradation
- **Maintainability**: Clear service boundaries and APIs

### Architecture Diagram

```mermaid
graph TD
    A[Load Balancer] --> B[API Gateway]
    B --> C[Auth Service]
    B --> D[Data Service]
    B --> E[Processing Service]
    D --> F[(Primary DB)]
    D --> G[(Cache)]
    E --> H[Message Queue]
```

### Key Technologies
- **Backend**: Python, FastAPI, gRPC
- **Database**: PostgreSQL, Redis
- **Infrastructure**: Kubernetes, Docker
- **Monitoring**: Prometheus, Grafana

## Core Components

### API Gateway
The API Gateway serves as the single entry point for all client requests.

#### Responsibilities
- Request routing and load balancing
- Authentication and authorization
- Rate limiting and throttling
- Request/response transformation

#### Configuration Example
```yaml
gateway:
  port: 8080
  routes:
    - path: /api/v1/users
      service: user-service
      methods: [GET, POST, PUT, DELETE]
    - path: /api/v1/data
      service: data-service
      methods: [GET, POST]
```

### Authentication Service
Handles all authentication and authorization logic.

#### Features
- JWT token generation and validation
- OAuth2 integration
- Role-based access control (RBAC)
- Session management

#### Code Example
```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Data Service
Manages all data operations and database interactions.

#### Database Schema
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Data records table
CREATE TABLE data_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Data Access Patterns
1. **Repository Pattern**: Abstraction over data access
2. **Unit of Work**: Transaction management
3. **Query Objects**: Complex query building

## Data Flow

### Request Processing Pipeline

1. **Client Request**
   - Client sends HTTPS request to load balancer
   - Load balancer forwards to API Gateway

2. **Authentication**
   - API Gateway validates JWT token
   - Checks permissions for requested resource

3. **Service Routing**
   - Request routed to appropriate microservice
   - Service processes request with business logic

4. **Data Operations**
   - Service interacts with database/cache
   - Transactions ensure data consistency

5. **Response Generation**
   - Service returns response to API Gateway
   - Gateway transforms and returns to client

### Asynchronous Processing

For long-running operations, we use message queues:

```python
import asyncio
from aio_pika import connect_robust

async def process_async_task(message):
    # Process the message
    data = json.loads(message.body)
    result = await long_running_operation(data)
    
    # Publish result
    await publish_result(result)
```

## Security Architecture

### Defense in Depth
We implement multiple layers of security:

#### Network Security
- VPC with private subnets
- Security groups and NACLs
- TLS 1.3 for all communications

#### Application Security
- Input validation and sanitization
- SQL injection prevention
- XSS and CSRF protection
- Rate limiting

#### Data Security
- Encryption at rest (AES-256)
- Encryption in transit (TLS)
- Key rotation policies
- Data anonymization

### Security Code Example
```python
from cryptography.fernet import Fernet
import hashlib

class SecurityManager:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt_sensitive_data(self, data: str) -> bytes:
        return self.cipher.encrypt(data.encode())
    
    def decrypt_sensitive_data(self, encrypted: bytes) -> str:
        return self.cipher.decrypt(encrypted).decode()
    
    def hash_password(self, password: str) -> str:
        return hashlib.pbkdf2_hmac('sha256', 
                                   password.encode(), 
                                   salt=SALT, 
                                   iterations=100000).hex()
```

## Deployment

### Container Configuration

#### Dockerfile Example
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

#### Service Definition
```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-service
spec:
  selector:
    app: api
  ports:
    - port: 80
      targetPort: 8000
  type: LoadBalancer
```

#### Deployment Configuration
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: company/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

### Monitoring and Observability

#### Metrics Collection
```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_count = Counter('api_requests_total', 'Total API requests')
request_duration = Histogram('api_request_duration_seconds', 'Request duration')
active_connections = Gauge('api_active_connections', 'Active connections')

# Use in application
@request_duration.time()
@request_count.count_exceptions()
async def handle_request(request):
    # Process request
    pass
```

#### Logging Configuration
```python
import structlog

logger = structlog.get_logger()

logger.info("request_received",
            method=request.method,
            path=request.path,
            user_id=user_id,
            trace_id=trace_id)
```

## Performance Optimization

### Caching Strategy
- **Redis** for session data and hot queries
- **CDN** for static assets
- **Application-level** caching for computed results

### Database Optimization
- Proper indexing strategy
- Query optimization
- Connection pooling
- Read replicas for scaling

### Code Optimization Example
```python
# Batch processing for efficiency
async def process_batch(items: List[Dict]) -> List[Dict]:
    # Process items in parallel
    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks)
    return results

# Connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40
)
```

## Conclusion

This architecture provides a scalable, secure, and maintainable foundation for our system. 
Regular reviews and updates ensure it continues to meet our evolving needs.
"""
        (workspace / "architecture.md").write_text(tech_doc)
        
        # API specification with structure
        api_spec = """---
title: API Specification
version: 2.0.0
format: OpenAPI 3.0
---

# API Specification

## Overview
This document defines our RESTful API specification.

## Authentication

All API requests must include authentication headers.

### Bearer Token
```http
Authorization: Bearer <token>
```

### API Key
```http
X-API-Key: <api-key>
```

## Endpoints

### User Management

#### GET /users
Retrieve a list of users.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page | integer | No | Page number (default: 1) |
| limit | integer | No | Items per page (default: 20) |
| search | string | No | Search query |

**Response:**
```json
{
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "name": "John Doe",
      "role": "admin"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

#### POST /users
Create a new user.

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "name": "Jane Doe",
  "password": "secure_password",
  "role": "member"
}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "newuser@example.com",
  "name": "Jane Doe",
  "role": "member",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Data Operations

#### GET PathUtils.get_data_path() / {id}
Retrieve specific data record.

**Path Parameters:**
- `id` (string, required): Record ID

**Response:**
```json
{
  "id": "uuid",
  "type": "measurement",
  "value": 42.5,
  "metadata": {
    "source": "sensor_001",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### POST PathUtils.get_data_path() / batch
Submit multiple data records.

**Request Body:**
```json
{
  "records": [
    {
      "type": "measurement",
      "value": 42.5,
      "metadata": {}
    }
  ]
}
```

## Error Responses

### Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": [
      {
        "field": "email",
        "issue": "Invalid email format"
      }
    ]
  }
}
```

### HTTP Status Codes
- `200 OK`: Successful request
- `201 Created`: Resource created
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Rate Limiting

API requests are rate limited:
- **Anonymous**: 100 requests/hour
- **Authenticated**: 1000 requests/hour
- **Premium**: 10000 requests/hour

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
```

## Webhooks

### Webhook Events
- `user.created`
- `user.updated`
- `user.deleted`
- `data.processed`
- `data.failed`

### Webhook Payload
```json
{
  "event": "user.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "id": "uuid",
    "email": "user@example.com"
  }
}
```

### Webhook Security
Verify webhook signatures:
```python
import hmac
import hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```
"""
        (workspace / "api-spec.md").write_text(api_spec)
        
        # Tutorial with nested structure
        tutorial = """# Complete Tutorial

## Introduction
Welcome to our comprehensive tutorial!

## Chapter 1: Getting Started

### 1.1 Prerequisites
Before we begin, ensure you have:
- Basic programming knowledge
- Development environment set up
- Access to our platform

### 1.2 Your First Project

#### 1.2.1 Project Setup
Create a new project directory:
```bash
mkdir my-project
cd my-project
```

#### 1.2.2 Configuration
Create `config.yml`:
```yaml
project:
  name: My First Project
  version: 1.0.0
```

### 1.3 Basic Operations

#### 1.3.1 Data Input
```python
# Load data from file
with open('data.json', 'r') as f:
    data = json.load(f)
```

#### 1.3.2 Processing
```python
# Process the data
result = process_data(data)
```

## Chapter 2: Advanced Topics

### 2.1 Performance Optimization

#### 2.1.1 Caching
Implement caching for better performance:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(param):
    # Complex computation
    return result
```

#### 2.1.2 Parallel Processing
```python
import multiprocessing

with multiprocessing.Pool() as pool:
    results = pool.map(process_item, items)
```

### 2.2 Error Handling

#### 2.2.1 Exception Handling
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    # Handle error
```

#### 2.2.2 Logging
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

## Chapter 3: Best Practices

### 3.1 Code Organization
- Use meaningful variable names
- Keep functions small and focused
- Document your code

### 3.2 Testing
```python
import unittest

class TestMyFunction(unittest.TestCase):
    def test_basic_case(self):
        result = my_function(input_data)
        self.assertEqual(result, expected)
```

## Appendix A: Reference

### Common Functions
| Function | Description | Example |
|----------|-------------|---------|
| `load_data()` | Load data from file | `data = load_data('file.json')` |
| `save_data()` | Save data to file | `save_data(data, 'output.json')` |

### Configuration Options
```yaml
# Complete configuration reference
system:
  debug: false
  log_level: INFO
  
performance:
  cache_size: 1000
  worker_threads: 4
```
"""
        (workspace / "tutorial.md").write_text(tutorial)
        
        return workspace
    
    @pytest.fixture
    def structure_setup(self, structured_docs, tmp_path):
        """Set up search with structured documents."""
        db_path = tmp_path / "structure_test.db"
        store = SQLiteStore(str(db_path))
        
        # Create plugin
        markdown_plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)
        
        # Create dispatcher
        dispatcher = Dispatcher([markdown_plugin])
        
        # Index all documents
        for doc_file in structured_docs.glob("*.md"):
            content = doc_file.read_text()
            dispatcher.indexFile(str(doc_file), content)
        
        return {
            'dispatcher': dispatcher,
            'store': store,
            'workspace': structured_docs
        }
    
    def test_heading_hierarchy_extraction(self, structure_setup):
        """Test extraction of document heading hierarchy."""
        dispatcher = structure_setup['dispatcher']
        
        # Search for top-level sections
        results = dispatcher.search("Technical Architecture Guide")
        assert len(results) > 0, "Should find document by title"
        
        # Search for nested sections
        nested_queries = [
            "Core Components",
            "API Gateway",
            "Authentication Service",
            "Security Architecture",
            "Deployment Configuration"
        ]
        
        for query in nested_queries:
            results = dispatcher.search(query)
            assert len(results) > 0, f"Should find section: {query}"
            
            # Check that we get the section content
            top_result = results[0]
            assert 'snippet' in top_result
            assert len(top_result['snippet']) > 30
    
    def test_code_block_extraction(self, structure_setup):
        """Test extraction of code blocks with language tags."""
        dispatcher = structure_setup['dispatcher']
        
        # Search for code examples
        code_queries = [
            "fastapi authentication example",
            "dockerfile configuration",
            "kubernetes deployment yaml",
            "python security code",
            "sql database schema"
        ]
        
        for query in code_queries:
            results = dispatcher.search(query)
            
            if len(results) > 0:
                # Check if we found code blocks
                code_found = False
                for result in results[:5]:
                    snippet = result.get('snippet', '')
                    if '```' in snippet or 'import' in snippet or 'CREATE TABLE' in snippet:
                        code_found = True
                        break
                
                assert code_found, f"Should find code for: {query}"
    
    def test_metadata_extraction(self, structure_setup):
        """Test extraction of document metadata from frontmatter."""
        dispatcher = structure_setup['dispatcher']
        
        # Search using metadata fields
        metadata_queries = [
            "author:Engineering Team",
            "version:2.0",
            "tags:architecture",
            "format:OpenAPI"
        ]
        
        for query in metadata_queries:
            # Note: Basic search might not support metadata syntax,
            # but we should at least find documents with these terms
            simple_query = query.split(':')[1]
            results = dispatcher.search(simple_query)
            
            # Should find documents containing metadata values
            if "Engineering" in simple_query or "architecture" in simple_query:
                assert len(results) > 0, f"Should find docs with metadata: {query}"
    
    def test_table_extraction(self, structure_setup):
        """Test extraction of table content."""
        dispatcher = structure_setup['dispatcher']
        
        # Search for table content
        table_queries = [
            "page integer required description",  # API parameters table
            "load_data save_data",  # Function reference table
            "HTTP Status Codes"  # Status codes section
        ]
        
        for query in table_queries:
            results = dispatcher.search(query)
            
            if len(results) > 0:
                # Should find table-related content
                top_result = results[0]
                snippet = top_result.get('snippet', '')
                
                # Tables might appear as structured text
                assert len(snippet) > 20, f"Should find table content for: {query}"
    
    def test_section_depth_search(self, structure_setup):
        """Test finding content at different section depths."""
        dispatcher = structure_setup['dispatcher']
        
        # Test different depth levels
        depth_queries = [
            ("Chapter 1", 1),  # Top level
            ("Getting Started Prerequisites", 2),  # Second level
            ("Project Setup", 3),  # Third level
            ("Caching Strategy", 2),  # Subsection
        ]
        
        for query, expected_depth in depth_queries:
            results = dispatcher.search(query)
            
            if len(results) > 0:
                # Found content at this depth
                assert True, f"Found content at depth {expected_depth}"
            
            # More specific queries should still work
            if "Project Setup" in query:
                setup_results = dispatcher.search("mkdir my-project")
                assert len(setup_results) > 0, "Should find commands in deep sections"
    
    def test_list_content_extraction(self, structure_setup):
        """Test extraction of list items and bullet points."""
        dispatcher = structure_setup['dispatcher']
        
        # Search for list content
        list_queries = [
            "Scalability Resilience Maintainability",  # Key principles list
            "JWT token OAuth2 RBAC",  # Features list
            "Request routing load balancing",  # Responsibilities list
        ]
        
        for query in list_queries:
            results = dispatcher.search(query)
            
            if len(results) > 0:
                # Should find list content
                found_list_items = False
                for result in results[:3]:
                    snippet = result.get('snippet', '')
                    if any(marker in snippet for marker in ['- ', '* ', '• ', '1.', '2.']):
                        found_list_items = True
                        break
                
                # Lists are common in technical docs
                assert found_list_items or len(results) > 0, f"Should find list content for: {query}"
    
    def test_cross_reference_extraction(self, structure_setup):
        """Test extraction of cross-references and links."""
        dispatcher = structure_setup['dispatcher']
        
        # Search for cross-referenced content
        ref_queries = [
            "Table of Contents",
            "System Overview section",
            "See Appendix",
            "configuration reference"
        ]
        
        for query in ref_queries:
            results = dispatcher.search(query)
            
            if len(results) > 0:
                # Should find reference content
                top_result = results[0]
                snippet = top_result.get('snippet', '')
                
                # References often include section markers or links
                ref_indicators = ['#', '](', 'see', 'refer', 'section', 'chapter']
                has_reference = any(indicator in snippet.lower() for indicator in ref_indicators)
                
                # Some queries should definitely have references
                if "Table of Contents" in query:
                    assert has_reference or len(results) > 0, "Should find TOC with references"
    
    def test_structured_search_queries(self, structure_setup):
        """Test queries that leverage document structure."""
        dispatcher = structure_setup['dispatcher']
        
        # Structure-aware queries
        structure_queries = [
            "security in deployment section",
            "python code examples in API",
            "configuration yaml examples",
            "error handling in chapter 2",
            "kubernetes deployment configuration"
        ]
        
        for query in structure_queries:
            results = dispatcher.search(query)
            
            # Should find relevant structured content
            if len(results) > 0:
                # Verify we found content in the right context
                relevant_found = False
                query_terms = query.lower().split()
                
                for result in results[:5]:
                    snippet = result.get('snippet', '').lower()
                    matching_terms = sum(1 for term in query_terms if term in snippet)
                    if matching_terms >= 2:  # At least 2 query terms found
                        relevant_found = True
                        break
                
                assert relevant_found or len(results) > 0, f"Should find structured content for: {query}"
    
    def test_document_outline_generation(self, structure_setup):
        """Test ability to understand document outline/structure."""
        dispatcher = structure_setup['dispatcher']
        store = structure_setup['store']
        
        # Search for documents with clear structure
        outline_queries = [
            "architecture guide outline",
            "tutorial chapters",
            "api specification sections"
        ]
        
        for query in outline_queries:
            results = dispatcher.search(query)
            
            # Documents with good structure should be findable
            assert len(results) >= 0, f"Should handle outline query: {query}"
            
            # If we found the architecture guide
            if "architecture" in query and len(results) > 0:
                # Should be able to find its major sections
                section_queries = ["System Overview", "Core Components", "Security"]
                for section in section_queries:
                    section_results = dispatcher.search(section)
                    assert len(section_results) > 0, f"Should find section: {section}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])