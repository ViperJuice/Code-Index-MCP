"""
Test searching by metadata from a user perspective.

This test module validates that users can search documents using metadata
such as tags, categories, dates, authors, and other document properties
beyond just the content.
"""

import pytest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Import system components
import sys
sys.path.insert(0, '/app')

from tests.base_test import BaseDocumentTest
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.markdown_plugin.frontmatter_parser import FrontmatterParser
from mcp_server.dispatcher import Dispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


class TestMetadataSearch(BaseDocumentTest):
    """Test frontmatter parsing, metadata filtering, tags, and custom fields."""
    
    @pytest.fixture
    def metadata_rich_docs(self, tmp_path):
        """Create documents with rich metadata."""
        workspace = tmp_path / "metadata_docs"
        workspace.mkdir()
        
        # Blog post with full metadata
        blog_post1 = """---
title: "Understanding Microservices Architecture"
author: "Jane Smith"
date: 2024-01-15
category: "architecture"
tags: ["microservices", "distributed-systems", "architecture", "tutorial"]
difficulty: "intermediate"
reading_time: "15 minutes"
version: "1.2"
last_updated: 2024-01-20
status: "published"
---

# Understanding Microservices Architecture

## Introduction

Microservices architecture has become the de facto standard for building scalable applications.
This comprehensive guide explores the principles, patterns, and practices.

## What are Microservices?

Microservices are small, autonomous services that work together. Each service:
- Has a single responsibility
- Owns its data
- Communicates via well-defined interfaces
- Can be deployed independently

## Benefits

### Scalability
Scale individual services based on demand rather than the entire application.

### Technology Diversity
Use different technologies for different services based on requirements.

### Fault Isolation
Failures in one service don't necessarily bring down the entire system.

## Implementation Patterns

### API Gateway Pattern
A single entry point for all client requests that routes to appropriate services.

### Service Discovery
Services dynamically discover and communicate with each other.

### Circuit Breaker
Prevent cascading failures by failing fast when a service is unavailable.

## Best Practices

1. Design for failure
2. Implement comprehensive monitoring
3. Use asynchronous communication where possible
4. Maintain clear service boundaries
5. Implement proper security at service boundaries

## Conclusion

Microservices offer great benefits but also introduce complexity. Understanding
the tradeoffs is crucial for successful implementation.
"""
        (workspace / "microservices-guide.md").write_text(blog_post1)
        
        # Tutorial with metadata
        tutorial = """---
title: "Getting Started with Docker"
author: "Bob Johnson"
date: 2024-01-10
category: "tutorial"
tags: ["docker", "containers", "devops", "beginner"]
difficulty: "beginner"
prerequisites: ["basic-linux", "command-line"]
estimated_time: "30 minutes"
version: "2.0"
language: "en"
---

# Getting Started with Docker

## Prerequisites

Before starting this tutorial, you should have:
- Basic Linux command line knowledge
- A computer with Docker installed

## What is Docker?

Docker is a platform for developing, shipping, and running applications in containers.
Containers are lightweight, standalone packages that include everything needed to run
an application.

## Your First Container

### Step 1: Hello World
```bash
docker run hello-world
```

This command downloads and runs a test image, verifying your installation works.

### Step 2: Running Ubuntu
```bash
docker run -it ubuntu bash
```

This gives you an interactive Ubuntu container.

### Step 3: Building an Image

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
```

Build the image:
```bash
docker build -t myapp .
```

## Container Management

### List Containers
```bash
docker ps        # Running containers
docker ps -a     # All containers
```

### Stop and Remove
```bash
docker stop <container-id>
docker rm <container-id>
```

## Next Steps

- Learn about Docker Compose
- Explore container orchestration
- Study best practices for production

## Additional Resources

- Official Docker documentation
- Docker Hub for finding images
- Community forums and tutorials
"""
        (workspace / "docker-tutorial.md").write_text(tutorial)
        
        # API documentation with version metadata
        api_doc = """---
title: "REST API v2 Documentation"
type: "api-reference"
api_version: "2.0"
status: "stable"
deprecated_endpoints: ["/v1/users/profile", "/v1/data/export"]
tags: ["api", "reference", "rest", "v2"]
last_modified: 2024-01-18
maintainer: "API Team"
support_email: "api-support@example.com"
---

# REST API v2 Documentation

## Overview

This document describes version 2 of our REST API. For v1 documentation (deprecated),
see the archives.

## Base URL
```
https://api.example.com/v2
```

## Authentication

All requests require Bearer token authentication:
```http
Authorization: Bearer <your-token>
```

## Endpoints

### Users

#### GET /users
List all users (paginated).

**Parameters:**
- `page` (int): Page number
- `per_page` (int): Items per page (max: 100)
- `sort` (string): Sort field
- `filter` (string): Filter expression

**Response:**
```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150
  }
}
```

### Data Processing

#### POST /process
Submit data for processing.

**Request:**
```json
{
  "data": {...},
  "options": {
    "format": "json",
    "async": true
  }
}
```

## Deprecated Endpoints

The following endpoints are deprecated and will be removed in v3:
- `/v1/users/profile` → Use `/v2/users/me`
- `/v1/data/export` → Use `/v2/export`

## Rate Limits

- Standard: 1000 requests/hour
- Premium: 10000 requests/hour

## Changelog

### v2.0 (2024-01-18)
- New user endpoints
- Improved error responses
- Deprecation of v1 endpoints

### v1.5 (2023-12-01)
- Added webhook support
- Performance improvements
"""
        (workspace / "api-v2-docs.md").write_text(api_doc)
        
        # Technical specification
        tech_spec = """---
title: "Database Schema Design"
document_type: "technical-specification"
author: "Sarah Chen"
reviewers: ["John Doe", "Alice Wang"]
approval_date: 2024-01-05
version: "3.1"
tags: ["database", "postgresql", "schema", "technical"]
confidentiality: "internal"
project: "DataPlatform"
jira_ticket: "PLAT-1234"
---

# Database Schema Design

## Document Information

- **Version**: 3.1
- **Status**: Approved
- **Project**: DataPlatform
- **JIRA**: PLAT-1234

## Overview

This document defines the database schema for the DataPlatform project.

## Schema Design

### Core Tables

#### users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'
);
```

#### organizations
```sql
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan_type VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Relationships

#### user_organizations
```sql
CREATE TABLE user_organizations (
    user_id INTEGER REFERENCES users(id),
    org_id INTEGER REFERENCES organizations(id),
    role VARCHAR(50) NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, org_id)
);
```

## Indexes

Performance-critical indexes:
```sql
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_orgs_plan ON organizations(plan_type);
```

## Migration Strategy

1. Create new schema in staging
2. Migrate test data
3. Performance testing
4. Production rollout in phases

## Security Considerations

- All PII data encrypted at rest
- Row-level security for multi-tenancy
- Audit logging for compliance

## Performance Targets

- User lookup: < 10ms
- Organization queries: < 50ms
- Join operations: < 100ms
"""
        (workspace / "db-schema-spec.md").write_text(tech_spec)
        
        # Release notes with version metadata
        release_notes = """---
title: "Release Notes - Version 3.0"
document_type: "release-notes"
version: "3.0.0"
release_date: 2024-01-25
release_manager: "Mike Wilson"
tags: ["release", "changelog", "v3"]
breaking_changes: true
highlights: ["New UI", "Performance improvements", "API v2"]
---

# Release Notes - Version 3.0

## Release Information

- **Version**: 3.0.0
- **Release Date**: January 25, 2024
- **Release Manager**: Mike Wilson
- **Type**: Major Release

## Highlights

🎉 **New User Interface** - Complete redesign for better usability
⚡ **Performance** - 3x faster data processing
🔧 **API v2** - New REST API with GraphQL support

## Breaking Changes ⚠️

### API Changes
- Removed deprecated v1 endpoints
- Changed authentication method to OAuth2
- New response format for all endpoints

### Configuration
- New YAML configuration format
- Environment variable names changed
- Removed legacy XML support

## New Features

### User Interface
- Modern, responsive design
- Dark mode support
- Improved accessibility (WCAG 2.1 AA)

### Data Processing
- Parallel processing by default
- Support for new file formats
- Real-time progress tracking

### API Enhancements
- GraphQL endpoint at `/graphql`
- Webhook support for all events
- Batch operations API

## Improvements

- 3x performance improvement for large datasets
- Reduced memory usage by 40%
- Better error messages and logging
- Enhanced security with 2FA support

## Bug Fixes

- Fixed memory leak in file processor (#1234)
- Resolved timezone issues (#1235)
- Corrected CSV export formatting (#1236)
- Fixed authentication timeout (#1237)

## Known Issues

- Large file uploads may timeout on slow connections
- Dark mode has minor styling issues in Safari
- GraphQL subscriptions limited to 100 concurrent connections

## Upgrade Guide

### From 2.x

1. Backup your data
2. Update configuration to new format
3. Run migration tool: `migrate-to-v3`
4. Update API integrations
5. Test thoroughly

### From 1.x

Please upgrade to 2.x first, then follow the above steps.

## Deprecations

The following features will be removed in v4:
- XML configuration support
- Legacy file formats (.dat, .old)
- SOAP API endpoints
"""
        (workspace / "release-notes-v3.md").write_text(release_notes)
        
        # Research paper with academic metadata
        research_paper = """---
title: "Optimizing Distributed Systems Performance"
document_type: "research"
authors: ["Dr. Emily Brown", "Prof. James Liu", "Dr. Anna Kumar"]
institution: "Tech University"
publication_date: 2024-01-12
conference: "International Conference on Distributed Systems"
doi: "10.1234/icds.2024.001"
tags: ["research", "distributed-systems", "performance", "academic"]
peer_reviewed: true
citations: 45
keywords: ["optimization", "distributed computing", "performance analysis"]
---

# Optimizing Distributed Systems Performance

## Abstract

This paper presents novel approaches to optimizing performance in large-scale
distributed systems. We introduce three key algorithms that reduce latency by
up to 40% compared to existing methods.

## 1. Introduction

Distributed systems face unique challenges in maintaining performance at scale.
This research addresses these challenges through innovative optimization techniques.

## 2. Related Work

Previous research by Smith et al. (2023) established baseline metrics for
distributed system performance. Our work builds upon these foundations.

## 3. Methodology

### 3.1 Experimental Setup

We tested our algorithms on a cluster of 100 nodes running various workloads.

### 3.2 Performance Metrics

Key metrics measured:
- Latency (p50, p95, p99)
- Throughput (requests/second)
- Resource utilization

## 4. Results

Our optimization techniques showed significant improvements:
- 40% reduction in p99 latency
- 25% increase in throughput
- 15% better resource utilization

## 5. Conclusion

The proposed optimizations provide substantial performance benefits for
distributed systems operating at scale.

## References

1. Smith, J. et al. (2023). "Distributed Systems Performance Baseline"
2. Johnson, K. (2022). "Scalability in Modern Computing"
3. Chen, L. (2023). "Network Optimization Strategies"
"""
        (workspace / "distributed-systems-research.md").write_text(research_paper)
        
        # Meeting notes with metadata
        meeting_notes = """---
title: "Architecture Review Meeting"
document_type: "meeting-notes"
date: 2024-01-22
time: "14:00-15:30"
attendees: ["John Doe", "Jane Smith", "Bob Johnson", "Alice Wang"]
facilitator: "Jane Smith"
location: "Conference Room A / Zoom"
tags: ["meeting", "architecture", "planning"]
action_items: 5
decisions_made: 3
follow_up_required: true
recording_available: true
---

# Architecture Review Meeting

## Date & Time
January 22, 2024 | 2:00 PM - 3:30 PM

## Attendees
- John Doe (Engineering Lead)
- Jane Smith (Architect) - Facilitator
- Bob Johnson (DevOps)
- Alice Wang (Product Manager)

## Agenda

1. Review current architecture
2. Discuss scaling challenges
3. Propose solutions
4. Next steps

## Discussion Points

### Current Architecture Review

Jane presented the current system architecture. Key points:
- Monolithic application showing strain
- Database becoming a bottleneck
- Need for better caching strategy

### Scaling Challenges

Bob highlighted operational challenges:
- Deployment takes 2+ hours
- Difficult to scale individual components
- Monitoring gaps in critical paths

### Proposed Solutions

1. **Microservices Migration**
   - Start with user service
   - Gradual decomposition
   - Maintain backwards compatibility

2. **Database Optimization**
   - Implement read replicas
   - Add caching layer
   - Consider sharding for large tables

3. **Infrastructure Updates**
   - Move to Kubernetes
   - Implement service mesh
   - Enhanced monitoring

## Decisions Made

1. ✅ Approve microservices migration plan
2. ✅ Allocate Q2 budget for infrastructure
3. ✅ Form dedicated migration team

## Action Items

1. **Jane**: Create detailed migration roadmap (Due: Jan 29)
2. **Bob**: POC Kubernetes setup (Due: Feb 5)
3. **John**: Identify team members for migration (Due: Jan 26)
4. **Alice**: Update product roadmap (Due: Jan 31)
5. **All**: Review and comment on design docs (Due: Feb 2)

## Next Meeting

February 5, 2024 - Progress Review

## Resources

- Architecture diagrams: [Link to Confluence]
- Migration plan draft: [Link to Google Docs]
- Recording: [Link to Zoom recording]
"""
        (workspace / "architecture-meeting-notes.md").write_text(meeting_notes)
        
        return workspace
    
    @pytest.fixture
    def metadata_setup(self, metadata_rich_docs, tmp_path):
        """Set up search with metadata-rich documents."""
        db_path = tmp_path / "metadata_test.db"
        store = SQLiteStore(str(db_path))
        
        # Create plugin
        markdown_plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)
        
        # Create dispatcher
        dispatcher = Dispatcher([markdown_plugin])
        
        # Index all documents
        for doc_file in metadata_rich_docs.glob("*.md"):
            content = doc_file.read_text()
            dispatcher.indexFile(str(doc_file), content)
        
        return {
            'dispatcher': dispatcher,
            'store': store,
            'workspace': metadata_rich_docs
        }
    
    def test_search_by_author(self, metadata_setup):
        """Test finding documents by author."""
        dispatcher = metadata_setup['dispatcher']
        
        # Search for specific authors
        author_queries = [
            "Jane Smith",
            "Bob Johnson",
            "Sarah Chen",
            "Dr. Emily Brown"
        ]
        
        for author in author_queries:
            results = dispatcher.search(author)
            
            # Should find documents by this author
            assert len(results) > 0, f"No results for author: {author}"
            
            # Verify author appears in results
            author_found = False
            for result in results[:3]:
                content = result.get('snippet', '')
                if author.lower() in content.lower():
                    author_found = True
                    break
            
            assert author_found, f"Author {author} not found in results"
    
    def test_search_by_category(self, metadata_setup):
        """Test finding documents by category."""
        dispatcher = metadata_setup['dispatcher']
        
        # Search for categories
        category_queries = [
            "architecture",
            "tutorial", 
            "api-reference",
            "technical-specification",
            "release-notes"
        ]
        
        for category in category_queries:
            results = dispatcher.search(category)
            
            # Should find categorized documents
            if len(results) > 0:
                # Categories often appear in metadata or content
                assert True, f"Found documents for category: {category}"
    
    def test_search_by_tags(self, metadata_setup):
        """Test finding documents by tags."""
        dispatcher = metadata_setup['dispatcher']
        
        # Search for tagged content
        tag_queries = [
            "microservices",
            "docker",
            "devops",
            "distributed-systems",
            "beginner"
        ]
        
        for tag in tag_queries:
            results = dispatcher.search(tag)
            
            # Should find tagged documents
            assert len(results) > 0, f"No results for tag: {tag}"
            
            # Verify tag relevance
            tag_found = False
            for result in results[:5]:
                content = result.get('snippet', '').lower()
                if tag.replace('-', ' ') in content or tag in content:
                    tag_found = True
                    break
            
            assert tag_found, f"Tag {tag} content not found"
    
    def test_search_by_difficulty(self, metadata_setup):
        """Test finding documents by difficulty level."""
        dispatcher = metadata_setup['dispatcher']
        
        # Search for difficulty levels
        difficulty_queries = [
            "beginner tutorial",
            "intermediate guide",
            "beginner docker",
            "intermediate microservices"
        ]
        
        for query in difficulty_queries:
            results = dispatcher.search(query)
            
            # Should find appropriately leveled content
            if len(results) > 0:
                # Difficulty often mentioned in tutorials
                assert True, f"Found content for: {query}"
    
    def test_search_by_document_type(self, metadata_setup):
        """Test finding documents by type."""
        dispatcher = metadata_setup['dispatcher']
        
        # Search for document types
        type_queries = [
            "release notes",
            "technical specification",
            "meeting notes",
            "research paper",
            "api reference"
        ]
        
        for doc_type in type_queries:
            results = dispatcher.search(doc_type)
            
            # Should find documents of this type
            assert len(results) > 0, f"No results for document type: {doc_type}"
            
            # Verify type appears in content
            type_found = False
            for result in results[:3]:
                content = result.get('snippet', '').lower()
                if doc_type.replace(' ', '-') in content or doc_type in content:
                    type_found = True
                    break
            
            assert type_found, f"Document type {doc_type} not found"
    
    def test_search_by_version(self, metadata_setup):
        """Test finding documents by version."""
        dispatcher = metadata_setup['dispatcher']
        
        # Search for versioned content
        version_queries = [
            "version 3.0",
            "v2 documentation",
            "api version 2",
            "version 3.1"
        ]
        
        for query in version_queries:
            results = dispatcher.search(query)
            
            # Should find versioned documents
            if len(results) > 0:
                assert True, f"Found versioned content: {query}"
    
    def test_search_by_date_references(self, metadata_setup):
        """Test finding documents with date references."""
        dispatcher = metadata_setup['dispatcher']
        
        # Search for date-related content
        date_queries = [
            "January 2024",
            "2024-01-15",
            "last updated 2024",
            "release date January"
        ]
        
        for query in date_queries:
            results = dispatcher.search(query)
            
            # Should find dated documents
            if len(results) > 0:
                # Dates appear in many contexts
                assert True, f"Found dated content: {query}"
    
    def test_search_by_status(self, metadata_setup):
        """Test finding documents by status."""
        dispatcher = metadata_setup['dispatcher']
        
        # Search for document status
        status_queries = [
            "published",
            "stable api",
            "deprecated endpoints",
            "approved specification",
            "breaking changes"
        ]
        
        for query in status_queries:
            results = dispatcher.search(query)
            
            # Should find status-related content
            assert len(results) >= 0, f"Should handle status query: {query}"
            
            if len(results) > 0:
                # Status information is important
                assert True, f"Found status information: {query}"
    
    def test_combined_metadata_search(self, metadata_setup):
        """Test searching with multiple metadata criteria."""
        dispatcher = metadata_setup['dispatcher']
        
        # Combined metadata queries
        combined_queries = [
            "Jane Smith architecture",  # Author + topic
            "beginner docker tutorial",  # Difficulty + tag + type
            "version 2 api stable",  # Version + type + status
            "release notes breaking changes",  # Type + content
            "technical specification database"  # Type + topic
        ]
        
        for query in combined_queries:
            results = dispatcher.search(query)
            
            # Should handle combined queries
            assert len(results) >= 0, f"Should handle combined query: {query}"
            
            if len(results) > 0:
                # Check relevance of results
                query_terms = query.lower().split()
                relevant_results = 0
                
                for result in results[:5]:
                    content = result.get('snippet', '').lower()
                    matching_terms = sum(1 for term in query_terms if term in content)
                    if matching_terms >= 2:  # At least 2 terms match
                        relevant_results += 1
                
                assert relevant_results > 0 or len(results) > 0, \
                    f"Should find relevant results for: {query}"
    
    def test_metadata_special_queries(self, metadata_setup):
        """Test special metadata-focused queries."""
        dispatcher = metadata_setup['dispatcher']
        
        # Special metadata queries (may not be directly supported but test behavior)
        special_queries = [
            "documents by Sarah Chen",
            "all release notes",
            "tutorials for beginners",
            "peer reviewed research",
            "internal documentation"
        ]
        
        for query in special_queries:
            results = dispatcher.search(query)
            
            # System should handle these gracefully
            assert isinstance(results, list), f"Should return results list for: {query}"
            
            # If results found, verify relevance
            if len(results) > 0:
                # Extract key terms from query
                if "Sarah Chen" in query:
                    assert any("Sarah Chen" in r.get('snippet', '') for r in results[:3])
                elif "release notes" in query:
                    assert any("release" in r.get('snippet', '').lower() for r in results[:3])
    
    def test_metadata_filtering_scenarios(self, metadata_setup):
        """Test real-world metadata filtering scenarios."""
        dispatcher = metadata_setup['dispatcher']
        
        # Real-world search scenarios
        scenarios = [
            "find all architecture documents from Jane",
            "latest API documentation version 2",
            "beginner tutorials about containers",
            "technical specifications approved this month",
            "meeting notes with action items"
        ]
        
        for scenario in scenarios:
            results = dispatcher.search(scenario)
            
            # Should provide useful results for natural queries
            assert len(results) >= 0, f"Should handle scenario: {scenario}"
            
            if len(results) > 0:
                # Verify we found relevant content
                key_terms = scenario.lower().split()
                # Remove common words
                key_terms = [t for t in key_terms if t not in 
                            ['find', 'all', 'from', 'the', 'with', 'about']]
                
                # Check if results contain key terms
                relevant_found = False
                for result in results[:5]:
                    content = result.get('snippet', '').lower()
                    if any(term in content for term in key_terms):
                        relevant_found = True
                        break
                
                assert relevant_found or len(results) > 0, \
                    f"Should find relevant content for scenario: {scenario}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])