#!/usr/bin/env python3
"""Demonstration of the Plain Text Plugin capabilities."""

import sys
from pathlib import Path
from typing import List

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.plaintext_plugin import PlainTextPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


def create_sample_documents():
    """Create various sample documents for testing."""
    samples = {
        "technical_doc.txt": """# System Architecture Overview

Author: Jane Smith
Date: 2024-12-01
Version: 2.0

## Executive Summary

This document provides a comprehensive overview of our microservices architecture.
The system is designed to handle millions of requests per day with high availability
and fault tolerance.

## Architecture Components

### API Gateway

The API Gateway serves as the single entry point for all client requests. It handles:

- Request routing and load balancing
- Authentication and authorization
- Rate limiting and throttling
- Request/response transformation

Implementation uses Kong Gateway with custom plugins for specific business logic.

### Service Mesh

We use Istio for service-to-service communication:

1. Automatic mTLS encryption
2. Traffic management and routing
3. Observability with distributed tracing
4. Circuit breaking and retry logic

### Data Layer

The data layer consists of:

- PostgreSQL for relational data
- MongoDB for document storage
- Redis for caching and session management
- Elasticsearch for full-text search

Connection pooling configuration:
    - Min connections: 10
    - Max connections: 100
    - Timeout: 30 seconds

## Performance Considerations

Key performance metrics:

- Response time: < 200ms (p99)
- Throughput: 10,000 req/sec
- Error rate: < 0.1%
- Availability: 99.99%

Formula for calculating capacity:
capacity = (requests_per_second * average_response_time) / available_threads

## Security Model

### Authentication Flow

```
Client -> API Gateway -> Auth Service -> Token Validation -> Service Access
```

Security measures include:

- OAuth 2.0 with JWT tokens
- API key management
- IP whitelisting
- DDoS protection

WARNING: Never expose internal service endpoints directly to the internet.

## Deployment Strategy

We follow a blue-green deployment model:

1. Deploy new version to green environment
2. Run smoke tests and health checks
3. Switch traffic from blue to green
4. Keep blue as rollback option

TIP: Always maintain at least 2 versions for quick rollback.

## Monitoring and Alerting

Monitoring stack:

- Prometheus for metrics collection
- Grafana for visualization
- AlertManager for alert routing
- ELK stack for log aggregation

## Conclusion

This architecture provides a solid foundation for scalable microservices.
Regular reviews and updates ensure it meets evolving business needs.

For questions, contact: architecture@company.com
""",
        
        "meeting_notes.txt": """Team Meeting Notes - Q4 Planning

Date: December 1, 2024
Attendees: John, Sarah, Mike, Lisa

John: Welcome everyone to our Q4 planning session. Let's start with the product roadmap.

Sarah: Thanks John. We have three major initiatives for Q4:
- Launch the mobile app beta
- Implement the new payment system
- Improve search functionality

Mike: On the engineering side, we need to address technical debt. The codebase has grown significantly, and we should allocate time for refactoring.

Lisa: From a design perspective, I'd like to propose a UI refresh. User feedback indicates some confusion with the current navigation.

John: Good points. Mike, how much time do you estimate for the technical debt work?

Mike: I'd say about 20% of our engineering capacity. We can't ignore it any longer.

Sarah: That seems reasonable. Can we still deliver all three initiatives with that allocation?

Mike: We'll need to be strategic. I suggest we prioritize the payment system first, as it directly impacts revenue.

Lisa: Agreed. The mobile app can launch with a subset of features if needed.

John: Let's create a detailed timeline. Sarah, can you work with Mike on that?

Sarah: Sure, we'll have a draft by Wednesday.

John: Any other concerns?

Mike: We should also plan for the holiday season. Many team members will be taking time off.

Lisa: Good point. Let's ensure we have coverage for critical systems.

John: I'll send out a calendar for everyone to mark their planned time off. Anything else?

Sarah: Just a reminder that we have the company party on December 15th!

John: Thanks for the reminder. Let's wrap up. Action items:
- Sarah and Mike: Draft Q4 timeline by Wednesday
- John: Send holiday calendar
- Lisa: UI refresh proposal by next week

Meeting adjourned at 3:45 PM.
""",
        
        "readme.txt": """PROJECT README

Welcome to the CodeAnalyzer Project!

OVERVIEW
--------
CodeAnalyzer is a tool for analyzing source code quality and identifying potential improvements.

INSTALLATION
------------
1. Clone the repository
2. Install dependencies: pip install -r requirements.txt
3. Run setup: python setup.py install

USAGE
-----
Basic usage:
    code-analyzer analyze /path/to/code

Advanced options:
    --recursive: Analyze subdirectories
    --output: Specify output format (json, html, csv)
    --rules: Custom ruleset file

CONFIGURATION
-------------
Create a .codeanalyzer.yml file in your project root:

    rules:
      - complexity: 10
      - line-length: 120
      - naming-convention: pep8
      
    exclude:
      - "*.test.py"
      - "vendor/*"

EXAMPLES
--------
Analyze a Python project:
    code-analyzer analyze ~/projects/myapp --output html

Generate a complexity report:
    code-analyzer report complexity ~/projects/myapp

TROUBLESHOOTING
---------------
Q: The analyzer is running slowly
A: Try excluding large directories or binary files

Q: I'm getting permission errors
A: Ensure you have read access to all files being analyzed

CONTRIBUTING
------------
We welcome contributions! Please see CONTRIBUTING.md for guidelines.

LICENSE
-------
This project is licensed under the MIT License. See LICENSE file for details.

CONTACT
-------
- GitHub: https://github.com/example/codeanalyzer
- Email: support@codeanalyzer.io
- Documentation: https://docs.codeanalyzer.io
"""
    }
    
    return samples


def demonstrate_plugin_features():
    """Demonstrate all features of the Plain Text plugin."""
    print("Plain Text Plugin Feature Demonstration")
    print("=" * 60)
    
    # Initialize plugin
    language_config = {
        'name': 'plaintext',
        'code': 'plaintext',
        'extensions': ['.txt', '.text', '.log', '.readme'],
        'file_pattern': r'.*\.(txt|text|log|readme)$'
    }
    
    plugin = PlainTextPlugin(language_config, enable_semantic=False)
    samples = create_sample_documents()
    
    for filename, content in samples.items():
        print(f"\n\n{'='*60}")
        print(f"Processing: {filename}")
        print(f"{'='*60}")
        
        file_path = Path(f"/tmp/{filename}")
        
        # 1. Metadata extraction
        print("\n1. METADATA EXTRACTION")
        print("-" * 20)
        metadata = plugin.extract_metadata(content, file_path)
        print(f"Title: {metadata.title}")
        print(f"Author: {metadata.author}")
        print(f"Date: {metadata.created_date}")
        print(f"Document Type: {metadata.document_type}")
        print(f"Language: {metadata.language}")
        print(f"Tags: {', '.join(metadata.tags[:5])}")
        if metadata.custom:
            print(f"Readability Score: {metadata.custom.get('readability_score', 0):.2f}")
            print(f"Avg Sentence Length: {metadata.custom.get('avg_sentence_length', 0):.1f} words")
        
        # 2. Structure extraction
        print("\n2. STRUCTURE ANALYSIS")
        print("-" * 20)
        structure = plugin.extract_structure(content, file_path)
        print(f"Sections found: {len(structure.sections)}")
        print(f"Headings found: {len(structure.headings)}")
        
        if structure.outline:
            print("\nDocument Outline:")
            print_outline(structure.outline, indent=2)
        
        # 3. NLP Analysis
        print("\n3. NLP ANALYSIS")
        print("-" * 20)
        analysis = plugin.nlp_processor.analyze_text(content)
        print(f"Text Type: {analysis.text_type.value}")
        print(f"Vocabulary Richness: {analysis.vocabulary_richness:.3f}")
        
        print("\nTop Topics:")
        for i, topic in enumerate(analysis.topics[:3], 1):
            print(f"  {i}. {', '.join(topic.keywords[:4])}")
            print(f"     Related: {', '.join(topic.related_terms[:3])}")
        
        print("\nKey Phrases:")
        for phrase in analysis.key_phrases[:5]:
            print(f"  - {phrase}")
        
        # 4. Semantic chunking
        print("\n4. SEMANTIC CHUNKING")
        print("-" * 20)
        chunks = plugin.chunk_document(content, file_path)
        print(f"Created {len(chunks)} semantic chunks")
        
        if chunks:
            print("\nFirst chunk preview:")
            first_chunk = chunks[0]
            print(f"  Size: {len(first_chunk.content)} chars")
            print(f"  Topics: {first_chunk.metadata.get('chunk_topics', [])}")
            print(f"  Content: {first_chunk.content[:150]}...")
        
        # 5. Structured content extraction
        print("\n5. STRUCTURED CONTENT")
        print("-" * 20)
        structured = plugin.nlp_processor.extract_structured_content(content)
        
        for content_type, items in structured.items():
            if items:
                print(f"\n{content_type.title()} ({len(items)}):")
                for item in items[:3]:
                    preview = item[:80] + "..." if len(item) > 80 else item
                    print(f"  - {preview}")
        
        # 6. Search demonstration
        print("\n6. SEARCH CAPABILITIES")
        print("-" * 20)
        
        # Cache chunks for search
        plugin._chunk_cache[str(file_path)] = chunks
        
        # Different search queries based on document type
        if filename == "technical_doc.txt":
            queries = ["API Gateway", "performance metrics", "security"]
        elif filename == "meeting_notes.txt":
            queries = ["Q4 planning", "Mike technical debt", "action items"]
        else:
            queries = ["installation", "usage", "troubleshooting"]
        
        for query in queries:
            results = plugin.search(query, {"semantic": False, "limit": 2})
            print(f"\nSearch: '{query}' -> {len(results)} results")
            for result in results[:1]:
                print(f"  - {result['snippet'][:100]}...")
        
        # 7. Special features based on text type
        print("\n7. TEXT-TYPE SPECIFIC FEATURES")
        print("-" * 20)
        
        if analysis.text_type.name == "TECHNICAL":
            tech_features = plugin._process_technical_text(content, analysis)
            if tech_features.get('technical_terms'):
                print(f"Technical terms: {', '.join(tech_features['technical_terms'][:5])}")
            if tech_features.get('code_snippets'):
                print(f"Code snippets found: {len(tech_features['code_snippets'])}")
                
        elif analysis.text_type.name == "CONVERSATIONAL":
            conv_features = plugin._process_conversational_text(content, analysis)
            if conv_features.get('speakers'):
                print(f"Speakers: {', '.join(conv_features['speakers'])}")
            if conv_features.get('questions'):
                print(f"Questions found: {len(conv_features['questions'])}")
                
        elif analysis.text_type.name == "INSTRUCTIONAL":
            inst_features = plugin._process_instructional_text(content, analysis)
            if inst_features.get('steps'):
                print(f"Instruction steps: {len(inst_features['steps'])}")
            if inst_features.get('tips'):
                print(f"Tips found: {len(inst_features['tips'])}")


def print_outline(outline: List[dict], indent: int = 0):
    """Print document outline recursively."""
    for item in outline:
        print(" " * indent + f"- {item['title']}")
        if item.get('children'):
            print_outline(item['children'], indent + 2)


def test_edge_cases():
    """Test edge cases and special text formats."""
    print("\n\n" + "="*60)
    print("EDGE CASE TESTING")
    print("="*60)
    
    language_config = {
        'name': 'plaintext',
        'code': 'plaintext',
        'extensions': ['.txt'],
        'file_pattern': r'.*\.txt$'
    }
    
    plugin = PlainTextPlugin(language_config, enable_semantic=False)
    
    # Test cases
    test_cases = {
        "Mixed line endings": "Line 1\r\nLine 2\nLine 3\rLine 4",
        "Unicode text": "Hello 世界! Здравствуй мир! 🌍",
        "Abbreviations": "Dr. Smith and Mr. Jones met at 3 P.M. on Jan. 1st.",
        "URLs and emails": "Visit https://example.com or email us at info@example.com",
        "Numbers and prices": "The price is $19.99 (was $29.99). Version 3.14.159.",
        "Empty document": "",
        "Very long line": "x" * 1000,
        "Nested lists": """
1. First item
   a. Sub-item one
   b. Sub-item two
2. Second item
   - Bullet point
   - Another point
""",
        "Code in text": """
Here's how to use it:

    def hello():
        print("Hello, World!")
        
The function above prints a greeting.
"""
    }
    
    for test_name, test_content in test_cases.items():
        print(f"\nTest: {test_name}")
        print("-" * 40)
        
        try:
            # Test sentence splitting
            sentences = plugin.sentence_splitter.split_sentences(test_content)
            print(f"Sentences: {len(sentences)}")
            
            # Test paragraph detection
            paragraphs = plugin.paragraph_detector.detect_paragraphs(test_content)
            print(f"Paragraphs: {len(paragraphs)}")
            
            # Test topic extraction (if content is substantial)
            if len(test_content) > 20:
                keywords = plugin.topic_extractor.extract_keywords(test_content, max_keywords=3)
                if keywords:
                    print(f"Keywords: {', '.join([kw for kw, _ in keywords])}")
            
            print("✓ Passed")
            
        except Exception as e:
            print(f"✗ Failed: {str(e)}")


if __name__ == "__main__":
    demonstrate_plugin_features()
    test_edge_cases()
    
    print("\n\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    print("\nThe Plain Text Plugin successfully demonstrates:")
    print("- Natural language processing for various text types")
    print("- Intelligent document structure extraction")
    print("- Semantic chunking for optimal search")
    print("- Topic modeling and keyword extraction")
    print("- Text-type specific processing")
    print("- Robust handling of edge cases")