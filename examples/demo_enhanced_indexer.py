#!/usr/bin/env python3
"""Demo of enhanced semantic indexer capabilities."""

from pathlib import Path
from mcp_server.utils.semantic_indexer import SemanticIndexer


def demo_enhanced_features():
    """Demonstrate the enhanced indexer features."""
    
    print("=" * 60)
    print("ENHANCED SEMANTIC INDEXER DEMONSTRATION")
    print("=" * 60)
    
    print("\n1. DOCUMENT TYPE WEIGHTS")
    print("-" * 40)
    indexer = SemanticIndexer.__new__(SemanticIndexer)  # Create without API initialization
    
    for doc_type, weight in indexer.DOCUMENT_TYPE_WEIGHTS.items():
        print(f"   {doc_type:12} -> {weight:4.2f}x weight")
    
    print("\n2. DOCUMENT SECTION STRUCTURE")
    print("-" * 40)
    
    # Demo markdown content
    demo_content = """# API Documentation

This is the main API documentation.

## Authentication

All requests require authentication.

### JWT Tokens

Use JWT tokens for authentication.

#### Token Format

Tokens should be in the format: Bearer <token>

### API Keys

Alternative authentication using API keys.

## Endpoints

Available API endpoints.

### Search

Search for code and documentation.

#### Basic Search

Simple text search functionality.

#### Advanced Search

Complex search with filters.

### Index

Index new content.
"""
    
    sections = indexer._parse_markdown_sections(demo_content, "api.md")
    
    def print_section_tree(sections, level=0):
        """Print sections in a tree structure."""
        for section in sections:
            if section.parent_section is None and level == 0:
                indent = "  " * level
                print(f"{indent}📄 {section.title} (Level {section.level})")
                print_subsections(section, sections, level + 1)
            elif level > 0 and section.parent_section and level == 1:
                # This is handled by print_subsections
                pass
    
    def print_subsections(parent, all_sections, level):
        """Print subsections recursively."""
        for section in all_sections:
            if section.parent_section == parent.title:
                indent = "  " * level
                icon = "📁" if section.subsections else "📄"
                print(f"{indent}{icon} {section.title} (Level {section.level})")
                if section.subsections:
                    print_subsections(section, all_sections, level + 1)
    
    # Build hierarchy display
    print("Document hierarchy:")
    root_sections = [s for s in sections if s.parent_section is None]
    
    def print_hierarchy(sections, parent_title=None, level=0):
        """Print document hierarchy."""
        for section in sections:
            if section.parent_section == parent_title:
                indent = "  " * level
                icon = "📁" if section.subsections else "📄"
                print(f"{indent}{icon} {section.title}")
                print_hierarchy(sections, section.title, level + 1)
    
    print_hierarchy(sections)
    
    print("\n3. CONTEXT-AWARE EMBEDDING PREPARATION")
    print("-" * 40)
    
    # Show how embeddings would be enriched
    sample_section = sections[3] if len(sections) > 3 else sections[0]  # JWT Tokens section
    
    print(f"Original section content:")
    print(f"   Title: {sample_section.title}")
    print(f"   Content: {sample_section.content.strip()}")
    
    print(f"\nContext-enriched embedding text:")
    
    # Build context path
    context_path = []
    current_section = sample_section
    
    # Find parent chain
    parent_chain = []
    temp_section = sample_section
    while temp_section.parent_section:
        parent_chain.append(temp_section.parent_section)
        # Find the parent section object
        for s in sections:
            if s.title == temp_section.parent_section:
                temp_section = s
                break
        else:
            break
    
    # Reverse to get root-to-leaf order
    parent_chain.reverse()
    context_str = " > ".join(parent_chain + [sample_section.title])
    
    print(f"   Document: API Documentation")
    print(f"   Section: {context_str}")
    print(f"   Content: {sample_section.content.strip()}")
    
    print(f"\nFull embedding text would be:")
    embedding_text = f"""Document: API Documentation

Section: {context_str}

{sample_section.content.strip()}"""
    
    print("   " + embedding_text.replace("\n", "\n   "))
    
    print("\n4. NATURAL LANGUAGE QUERY TYPES")
    print("-" * 40)
    
    query_examples = [
        ("How do I authenticate API requests?", ["markdown", "api"], "Authentication guidance"),
        ("What are the available search endpoints?", ["api", "markdown"], "API endpoint documentation"),
        ("Show me JWT token examples", ["markdown", "tutorial"], "Code examples and tutorials"),
        ("Getting started with the API", ["readme", "tutorial"], "Introductory content"),
    ]
    
    for query, doc_types, purpose in query_examples:
        print(f"\nQuery: '{query}'")
        print(f"   Target doc types: {doc_types}")
        print(f"   Purpose: {purpose}")
        
        # Show which weights would apply
        weights = [indexer.DOCUMENT_TYPE_WEIGHTS.get(dt, 1.0) for dt in doc_types]
        print(f"   Weights: {[f'{dt}={w:.2f}' for dt, w in zip(doc_types, weights)]}")
    
    print("\n5. SECTION-AWARE SEARCH BENEFITS")
    print("-" * 40)
    
    benefits = [
        "🎯 Context preservation: Section titles and hierarchy inform embeddings",
        "📚 Document type weighting: Documentation gets priority for doc searches",
        "🔍 Natural language queries: Optimized for human-readable questions",
        "🌳 Hierarchical structure: Parent-child relationships maintained",
        "🏷️  Metadata enrichment: Tags, summaries, and context included",
        "📊 Weighted scoring: Different content types have appropriate relevance",
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")
    
    print("\n6. USAGE PATTERNS")
    print("-" * 40)
    
    usage_patterns = [
        ("Documentation Search", "query_natural_language()", ["markdown", "readme"]),
        ("API Reference Lookup", "query_natural_language()", ["api"]),
        ("Tutorial Content", "query_natural_language()", ["tutorial", "guide"]),
        ("Code + Docs Combined", "query_natural_language()", None),
        ("Pure Code Search", "search() or query()", ["code"]),
    ]
    
    for pattern, method, doc_types in usage_patterns:
        print(f"\n   {pattern}:")
        print(f"     Method: {method}")
        if doc_types:
            print(f"     Doc types: {doc_types}")
        else:
            print(f"     Doc types: All types included")
    
    print("\n" + "=" * 60)
    print("The enhanced indexer provides sophisticated document")
    print("understanding while maintaining efficient code search.")
    print("=" * 60)


if __name__ == "__main__":
    demo_enhanced_features()