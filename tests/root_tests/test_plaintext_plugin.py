#!/usr/bin/env python3
"""Test the Plain Text plugin implementation."""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.plaintext_plugin import PlainTextPlugin


def test_plaintext_plugin():
    """Test the Plain Text plugin with sample content."""

    # Initialize plugin
    language_config = {
        "name": "plaintext",
        "code": "plaintext",  # Required by the base class
        "extensions": [".txt", ".text", ".md"],
        "file_pattern": r".*\.(txt|text|md|markdown|rst|log|readme)$",
    }

    plugin = PlainTextPlugin(language_config, enable_semantic=False)

    # Test content with various structures
    test_content = """# Technical Documentation

Author: John Doe
Date: 2024-01-15
Version: 1.0

## Introduction

This is a technical document that demonstrates various features of plain text processing.
It includes multiple paragraphs, headings, and different types of content.

The document processor should be able to identify structure, extract metadata, and
create semantic chunks for efficient searching.

## Features

### Natural Language Processing

The plugin includes several NLP capabilities:

- Sentence boundary detection
- Paragraph identification
- Topic extraction
- Keyword analysis

### Code Examples

Here's a simple Python example:

    def hello_world():
        print("Hello, World!")
        return True

### Lists and Instructions

1. First, install the required dependencies
2. Configure the system settings
3. Run the initialization script
4. Verify the installation

WARNING: Make sure to backup your data before proceeding.

## Technical Details

The system uses advanced algorithms for text processing. The formula for
calculating relevance is: relevance = keyword_matches * proximity_score.

### Performance Metrics

- Processing speed: 1000 documents/minute
- Memory usage: < 500MB
- Accuracy: 95% for structure detection

## Conclusion

This document demonstrates the capabilities of the plain text plugin.
It can handle various document structures and extract meaningful information.

Questions? Contact support@example.com

## Appendix

Additional resources and references can be found at:
https://example.com/documentation
"""

    # Test file path
    test_file = Path("/tmp/test_document.txt")

    print("Testing Plain Text Plugin")
    print("=" * 50)

    # Test supports method
    print(f"\nSupports .txt files: {plugin.supports(test_file)}")

    # Test metadata extraction
    print("\nExtracting metadata...")
    metadata = plugin.extract_metadata(test_content, test_file)
    print(f"Title: {metadata.title}")
    print(f"Author: {metadata.author}")
    print(f"Date: {metadata.created_date}")
    print(f"Document Type: {metadata.document_type}")
    print(f"Tags: {metadata.tags[:5]}")

    # Test structure extraction
    print("\nExtracting structure...")
    structure = plugin.extract_structure(test_content, test_file)
    print(f"Found {len(structure.sections)} sections")
    print(f"Found {len(structure.headings)} headings")

    print("\nSection titles:")
    for section in structure.sections[:5]:
        print(f"  - {section['title']} (Level {section['level']})")

    # Test chunking
    print("\nChunking document...")
    chunks = plugin.chunk_document(test_content, test_file)
    print(f"Created {len(chunks)} chunks")

    print("\nFirst 3 chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i + 1}:")
        print(f"  Position: {chunk.start_pos}-{chunk.end_pos}")
        print(f"  Metadata: {chunk.metadata}")
        print(f"  Content preview: {chunk.content[:100]}...")

    # Test NLP analysis
    print("\nTesting NLP analysis...")
    analysis = plugin.nlp_processor.analyze_text(test_content)
    print(f"Text type: {analysis.text_type.value}")
    print(f"Readability score: {analysis.readability_score:.2f}")
    print(f"Average sentence length: {analysis.avg_sentence_length:.2f} words")
    print(f"Vocabulary richness: {analysis.vocabulary_richness:.2f}")

    print("\nTop topics:")
    for topic in analysis.topics[:3]:
        print(f"  - Keywords: {', '.join(topic.keywords[:3])}")
        print(f"    Score: {topic.score:.3f}")

    # Test search (without semantic indexing)
    print("\nTesting search...")
    search_results = plugin.search("NLP capabilities", {"semantic": False, "limit": 5})
    print(f"Found {len(search_results)} results")

    for i, result in enumerate(search_results):
        print(f"\nResult {i + 1}:")
        print(f"  File: {result['file']}")
        print(f"  Snippet: {result['snippet']}")
        if "relevance" in result:
            print(f"  Relevance: {result['relevance']}")

    # Test sentence splitting
    print("\nTesting sentence splitter...")
    test_text = "Dr. Smith said: 'Hello.' This is a test. Visit https://example.com for more info. The price is $3.50."
    sentences = plugin.sentence_splitter.split_sentences(test_text)
    print(f"Split into {len(sentences)} sentences:")
    for i, sent in enumerate(sentences):
        print(f"  {i + 1}. {sent}")

    # Test topic extraction
    print("\nTesting topic extractor...")
    keywords = plugin.topic_extractor.extract_keywords(test_content, max_keywords=10)
    print("Top keywords:")
    for keyword, score in keywords[:5]:
        print(f"  - {keyword}: {score:.3f}")

    print("\n" + "=" * 50)
    print("All tests completed successfully!")


if __name__ == "__main__":
    test_plaintext_plugin()
