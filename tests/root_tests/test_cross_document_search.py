"""Test cases for cross-document search functionality."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from tests.base_test import BaseDocumentTest


class TestCrossDocumentSearch(BaseDocumentTest):
    """Test multi-document queries, linking, citations, and discovery."""

    def test_multi_document_basic_search(self):
        """Test searching across multiple documents."""
        # Create multiple related documents
        self.create_test_file(
            "api_overview.md",
            """# API Overview

## Introduction
This document provides an overview of our REST API.

## Authentication
All API requests require authentication using JWT tokens.
See the [Authentication Guide](auth_guide.md) for details.

## Endpoints
- `/api/users` - User management
- `/api/products` - Product catalog
- `/api/orders` - Order processing""",
        )

        self.create_test_file(
            "auth_guide.md",
            """# Authentication Guide

## JWT Authentication
Our API uses JSON Web Tokens for authentication.

### Getting a Token
POST to `/api/auth/login` with credentials.

### Using the Token
Include in Authorization header: `Bearer <token>`

## OAuth2 Support
We also support OAuth2 for third-party integrations.
See [OAuth2 Setup](oauth_setup.md) for configuration.""",
        )

        self.create_test_file(
            "oauth_setup.md",
            """# OAuth2 Setup

## Configuration
Configure OAuth2 providers in `config/oauth.json`.

## Supported Providers
- Google
- GitHub
- Microsoft

## Implementation
See the [API Overview](api_overview.md) for integration points.""",
        )

        # Index all documents
        for filename in ["api_overview.md", "auth_guide.md", "oauth_setup.md"]:
            self.dispatcher.index_file(self.workspace / filename)

        # Search across all documents
        results = self.dispatcher.search_cross_document("authentication")

        assert results is not None
        assert len(results) >= 2

        # Should find matches in multiple documents
        doc_names = set(r["document"] for r in results)
        assert "api_overview.md" in doc_names
        assert "auth_guide.md" in doc_names

        # Check relevance scoring
        auth_guide_results = [r for r in results if r["document"] == "auth_guide.md"]
        assert len(auth_guide_results) > 0
        assert auth_guide_results[0]["score"] > 0.7  # Should have high relevance

    def test_document_linking_discovery(self):
        """Test discovering links between documents."""
        # Create interconnected documents
        self.create_test_file(
            "index.md",
            """# Documentation Index

## Getting Started
- [Installation Guide](install.md)
- [Configuration](config.md)
- [Quick Start Tutorial](tutorial.md)

## Reference
- [API Documentation](api.md)
- [CLI Reference](cli.md)

## Advanced Topics
- [Architecture Overview](architecture.md)
- [Plugin Development](plugins.md)""",
        )

        self.create_test_file(
            "install.md",
            """# Installation Guide

## Prerequisites
See [System Requirements](requirements.md).

## Installation Steps
1. Download the package
2. Run the installer
3. Follow [Configuration](config.md) guide

## Next Steps
- Read the [Quick Start Tutorial](tutorial.md)
- Check the [API Documentation](api.md)""",
        )

        self.create_test_file(
            "config.md",
            """# Configuration

## Basic Configuration
After [Installation](install.md), configure the system.

## Advanced Options
For plugin configuration, see [Plugin Development](plugins.md).

## Environment Variables
Refer to [CLI Reference](cli.md) for env var usage.""",
        )

        # Index documents
        for filename in ["index.md", "install.md", "config.md"]:
            self.dispatcher.index_file(self.workspace / filename)

        # Discover document links
        link_graph = self.dispatcher.build_document_graph(self.workspace)

        assert link_graph is not None
        assert "nodes" in link_graph
        assert "edges" in link_graph

        # Check that all documents are nodes
        node_names = [n["id"] for n in link_graph["nodes"]]
        assert "index.md" in node_names
        assert "install.md" in node_names
        assert "config.md" in node_names

        # Check edges (links between docs)
        edges = link_graph["edges"]

        # index.md should link to install.md and config.md
        index_edges = [e for e in edges if e["source"] == "index.md"]
        index_targets = [e["target"] for e in index_edges]
        assert "install.md" in index_targets
        assert "config.md" in index_targets

        # Bidirectional links should exist
        install_edges = [e for e in edges if e["source"] == "install.md"]
        install_targets = [e["target"] for e in install_edges]
        assert "config.md" in install_targets

    def test_citation_tracking(self):
        """Test tracking citations and references between documents."""
        # Create documents with citations
        self.create_test_file(
            "research_paper.md",
            """# Research Paper

## Abstract
This paper discusses advanced algorithms [1].

## Introduction
Previous work by Smith et al. [2] established the foundation.
Jones [3] later expanded on this concept.

## Methodology
We follow the approach described in [1] with modifications from [4].

## References
[1] Advanced Algorithms, 2023
[2] Smith et al., Foundations, 2022
[3] Jones, Expansions, 2023
[4] Brown, Modifications, 2023""",
        )

        self.create_test_file(
            "literature_review.md",
            """# Literature Review

## Overview
This review covers recent developments.

## Key Papers
- Smith et al. [2] provides the theoretical basis
- Jones [3] offers practical applications
- Wilson [5] critiques the approach

## Analysis
The work in [2] and [3] complement each other.
However, [5] raises valid concerns.

## References
[2] Smith et al., Foundations, 2022
[3] Jones, Expansions, 2023
[5] Wilson, Critiques, 2023""",
        )

        self.create_test_file(
            "implementation.md",
            """# Implementation Details

## Background
Based on the research in [1] and [2].

## Algorithm
Following [1], we implement:
```python
def algorithm():
    # As described in [1]
    pass
```

## Optimizations
Jones [3] suggests optimizations that we adopt.

## References
[1] Advanced Algorithms, 2023
[2] Smith et al., Foundations, 2022
[3] Jones, Expansions, 2023""",
        )

        # Index documents
        for filename in ["research_paper.md", "literature_review.md", "implementation.md"]:
            self.dispatcher.index_file(self.workspace / filename)

        # Extract citations
        citations = self.dispatcher.extract_citations(self.workspace)

        assert citations is not None
        assert len(citations) > 0

        # Check citation frequency
        citation_counts = {}
        for citation in citations:
            ref = citation["reference"]
            citation_counts[ref] = citation_counts.get(ref, 0) + 1

        # [2] and [3] should be most cited
        assert citation_counts.get("[2]", 0) >= 3
        assert citation_counts.get("[3]", 0) >= 3
        assert citation_counts.get("[1]", 0) >= 3

        # Check co-citation patterns
        co_citations = self.dispatcher.find_co_citations(citations)

        # [2] and [3] should frequently appear together
        pair_23 = ("[2]", "[3]")
        assert pair_23 in co_citations or ("[3]", "[2]") in co_citations

    def test_semantic_document_clustering(self):
        """Test grouping related documents by semantic similarity."""
        # Create documents in different topic clusters

        # Programming cluster
        self.create_test_file(
            "python_guide.md",
            """# Python Programming Guide
            
## Introduction to Python
Python is a high-level programming language.

## Basic Syntax
Variables, functions, and classes in Python.

## Advanced Features
Decorators, generators, and metaclasses.""",
        )

        self.create_test_file(
            "javascript_tutorial.md",
            """# JavaScript Tutorial

## JavaScript Basics
Learn JavaScript programming fundamentals.

## Functions and Objects
Understanding JS functions and object-oriented programming.

## Modern JavaScript
ES6+ features and async programming.""",
        )

        # Data Science cluster
        self.create_test_file(
            "ml_basics.md",
            """# Machine Learning Basics

## Introduction
Fundamentals of machine learning and AI.

## Supervised Learning
Classification and regression algorithms.

## Neural Networks
Deep learning with neural networks.""",
        )

        self.create_test_file(
            "data_analysis.md",
            """# Data Analysis Guide

## Data Preprocessing
Cleaning and preparing data for analysis.

## Statistical Analysis
Descriptive and inferential statistics.

## Visualization
Creating charts and graphs for data insights.""",
        )

        # DevOps cluster
        self.create_test_file(
            "docker_guide.md",
            """# Docker Guide

## Containerization
Understanding Docker containers and images.

## Docker Compose
Multi-container applications with Compose.

## Kubernetes
Container orchestration with K8s.""",
        )

        self.create_test_file(
            "ci_cd_pipeline.md",
            """# CI/CD Pipeline

## Continuous Integration
Automated testing and building.

## Continuous Deployment
Automated deployment strategies.

## Pipeline Tools
Jenkins, GitHub Actions, GitLab CI.""",
        )

        # Index all documents
        docs = [
            "python_guide.md",
            "javascript_tutorial.md",
            "ml_basics.md",
            "data_analysis.md",
            "docker_guide.md",
            "ci_cd_pipeline.md",
        ]
        for filename in docs:
            self.dispatcher.index_file(self.workspace / filename)

        # Perform semantic clustering
        clusters = self.dispatcher.cluster_documents(self.workspace, n_clusters=3)

        assert clusters is not None
        assert len(clusters) == 3

        # Verify documents are clustered by topic
        for cluster in clusters:
            doc_names = [doc["name"] for doc in cluster["documents"]]

            # Check if cluster contains related documents
            if "python_guide.md" in doc_names:
                # Programming cluster
                assert "javascript_tutorial.md" in doc_names
            elif "ml_basics.md" in doc_names:
                # Data Science cluster
                assert "data_analysis.md" in doc_names
            elif "docker_guide.md" in doc_names:
                # DevOps cluster
                assert "ci_cd_pipeline.md" in doc_names

    def test_cross_reference_resolution(self):
        """Test resolving cross-references between documents."""
        # Create documents with various reference styles
        self.create_test_file(
            "main_doc.md",
            """# Main Documentation

## Overview
This is the main entry point.

## Concepts
- For basics, see [Getting Started](getting_started.md)
- Advanced users should read [Advanced Topics](advanced.md#custom-config)
- API details in [API Reference](api_ref.md#endpoints)

## Related
- See also: getting_started.md
- Related document: ./guides/user_guide.md
- External: https://example.com/docs""",
        )

        self.create_test_file(
            "getting_started.md",
            """# Getting Started

## Prerequisites
Before beginning, review the [Main Documentation](main_doc.md).

## First Steps
1. Install the software
2. Configure settings (see [Configuration](config.md))
3. Run the examples

## Next Steps
Proceed to [Advanced Topics](advanced.md) when ready.""",
        )

        self.create_test_file(
            "advanced.md",
            """# Advanced Topics

## Custom Config
Advanced configuration options.

## Performance Tuning
Optimization techniques.

## Integration
See [API Reference](api_ref.md) for integration options.

Back to [Main Documentation](main_doc.md#overview).""",
        )

        # Create subdirectory
        (self.workspace / "guides").mkdir(exist_ok=True)
        self.create_test_file(
            "guides/user_guide.md",
            """# User Guide

Complete guide for end users.
Start with [Getting Started](../getting_started.md).""",
        )

        # Index documents
        for filename in [
            "main_doc.md",
            "getting_started.md",
            "advanced.md",
            "guides/user_guide.md",
        ]:
            self.dispatcher.index_file(self.workspace / filename)

        # Resolve cross-references
        refs = self.dispatcher.resolve_cross_references(self.workspace / "main_doc.md")

        assert refs is not None
        assert len(refs) > 0

        # Check different reference types
        ref_targets = {ref["target"]: ref for ref in refs}

        # Direct file reference
        assert "getting_started.md" in ref_targets
        assert ref_targets["getting_started.md"]["resolved_path"].endswith("getting_started.md")

        # File with anchor
        assert "advanced.md#custom-config" in ref_targets
        assert ref_targets["advanced.md#custom-config"]["anchor"] == "custom-config"

        # Relative path
        assert "./guides/user_guide.md" in ref_targets
        assert "user_guide.md" in ref_targets["./guides/user_guide.md"]["resolved_path"]

    def test_document_similarity_search(self):
        """Test finding similar documents based on content."""
        # Create documents with varying similarity
        self.create_test_file(
            "react_tutorial.md",
            """# React Tutorial

## Introduction to React
React is a JavaScript library for building user interfaces.

## Components
Building reusable UI components with JSX.

## State Management
Managing component state with hooks.

## React Router
Client-side routing in React applications.""",
        )

        self.create_test_file(
            "vue_guide.md",
            """# Vue.js Guide

## Introduction to Vue
Vue is a progressive JavaScript framework for UIs.

## Components
Creating reusable components with templates.

## State Management
Vuex for application state management.

## Vue Router
Routing in Vue applications.""",
        )

        self.create_test_file(
            "angular_docs.md",
            """# Angular Documentation

## Introduction to Angular
Angular is a TypeScript-based web framework.

## Components
Building components with decorators.

## State Management
RxJS and services for state.

## Angular Router
Navigation and routing.""",
        )

        self.create_test_file(
            "database_guide.md",
            """# Database Guide

## Introduction to Databases
Relational and NoSQL databases.

## SQL Basics
Writing queries and managing data.

## Database Design
Normalization and schema design.

## Performance
Indexing and query optimization.""",
        )

        # Index all documents
        docs = ["react_tutorial.md", "vue_guide.md", "angular_docs.md", "database_guide.md"]
        for filename in docs:
            self.dispatcher.index_file(self.workspace / filename)

        # Find similar documents to React tutorial
        similar = self.dispatcher.find_similar_documents(
            self.workspace / "react_tutorial.md", threshold=0.5
        )

        assert similar is not None
        assert len(similar) >= 2

        # Vue and Angular guides should be most similar
        similar_names = [s["document"] for s in similar[:2]]
        assert "vue_guide.md" in similar_names
        assert "angular_docs.md" in similar_names

        # Database guide should be less similar
        db_similarity = next((s for s in similar if s["document"] == "database_guide.md"), None)
        if db_similarity:
            assert db_similarity["score"] < similar[0]["score"]

    def test_topic_based_document_discovery(self):
        """Test discovering documents by topic analysis."""
        # Create documents covering various topics
        self.create_test_file(
            "security_overview.md",
            """# Security Overview

## Authentication
User authentication methods and best practices.

## Authorization
Role-based access control and permissions.

## Encryption
Data encryption at rest and in transit.

## Security Auditing
Logging and monitoring for security events.""",
        )

        self.create_test_file(
            "api_security.md",
            """# API Security

## API Authentication
OAuth2, JWT, and API keys.

## Rate Limiting
Protecting APIs from abuse.

## Input Validation
Preventing injection attacks.

## CORS and CSP
Cross-origin security policies.""",
        )

        self.create_test_file(
            "performance_guide.md",
            """# Performance Guide

## Optimization Techniques
Code and query optimization.

## Caching Strategies
In-memory and distributed caching.

## Load Balancing
Distributing traffic efficiently.

## Monitoring
Performance metrics and alerting.""",
        )

        self.create_test_file(
            "deployment_security.md",
            """# Deployment Security

## Secure Deployment
Security considerations for deployment.

## Container Security
Docker and Kubernetes security.

## Network Security
Firewalls and network policies.

## Compliance
Meeting security standards.""",
        )

        # Index documents
        docs = [
            "security_overview.md",
            "api_security.md",
            "performance_guide.md",
            "deployment_security.md",
        ]
        for filename in docs:
            self.dispatcher.index_file(self.workspace / filename)

        # Discover documents by topic
        security_docs = self.dispatcher.discover_by_topic("security authentication encryption")

        assert security_docs is not None
        assert len(security_docs) >= 3

        # Security-related documents should rank highest
        top_docs = [d["document"] for d in security_docs[:3]]
        assert "security_overview.md" in top_docs
        assert "api_security.md" in top_docs
        assert "deployment_security.md" in top_docs

        # Performance guide should rank lower
        perf_rank = next(
            (i for i, d in enumerate(security_docs) if d["document"] == "performance_guide.md"), -1
        )
        assert perf_rank > 2 or perf_rank == -1
