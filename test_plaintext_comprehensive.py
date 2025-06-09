"""
Comprehensive tests for plain text document processing features.

This test suite covers:
- Natural language processing features
- Paragraph detection and sentence splitting  
- Topic extraction and keyword analysis
- Various text formats and edge cases
- Integration with search capabilities
"""

import pytest
import tempfile
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from unittest.mock import Mock, patch
from dataclasses import dataclass

# Import the PlainText plugin and related classes
import sys
sys.path.insert(0, '/app')

from mcp_server.plugins.plaintext_plugin.plugin import PlainTextPlugin
from mcp_server.plugins.plaintext_plugin.nlp_processor import NLPProcessor, TextAnalysis, TextType
from mcp_server.plugins.plaintext_plugin.paragraph_detector import ParagraphDetector, Paragraph
from mcp_server.plugins.plaintext_plugin.sentence_splitter import SentenceSplitter
from mcp_server.plugins.plaintext_plugin.topic_extractor import TopicExtractor
from mcp_server.document_processing import DocumentStructure, DocumentMetadata, DocumentChunk
from mcp_server.storage.sqlite_store import SQLiteStore


class TestNLPProcessor:
    """Test natural language processing functionality."""
    
    @pytest.fixture
    def processor(self):
        """Create an NLPProcessor instance."""
        return NLPProcessor()
    
    def test_text_type_detection(self, processor):
        """Test automatic text type detection."""
        # Technical text
        technical_text = """
        This document describes the implementation of a REST API using Python Flask.
        The authentication mechanism uses JWT tokens for secure access.
        Database operations are performed using SQLAlchemy ORM.
        Error handling follows HTTP status code conventions.
        """
        
        analysis = processor.analyze_text(technical_text)
        assert analysis.text_type in [TextType.TECHNICAL, TextType.INSTRUCTIONAL]
        
        # Narrative text
        narrative_text = """
        Once upon a time, in a small village nestled between rolling hills,
        there lived a young woman named Elena. She had always dreamed of adventure
        beyond the confines of her quiet hometown. Every morning, she would
        gaze at the distant mountains and wonder what mysteries lay beyond.
        """
        
        analysis = processor.analyze_text(narrative_text)
        assert analysis.text_type == TextType.NARRATIVE
        
        # Instructional text
        instructional_text = """
        To install the software, follow these steps:
        
        1. Download the installer from the official website
        2. Run the installer as administrator
        3. Accept the license agreement
        4. Choose the installation directory
        5. Click 'Install' to begin the process
        6. Restart your computer when prompted
        
        Warning: Make sure to backup your data before installation.
        """
        
        analysis = processor.analyze_text(instructional_text)
        assert analysis.text_type == TextType.INSTRUCTIONAL
    
    def test_readability_analysis(self, processor):
        """Test readability score calculation."""
        # Simple text
        simple_text = "This is easy to read. Short sentences. Simple words."
        analysis = processor.analyze_text(simple_text)
        assert analysis.readability_score > 80  # Should be high readability
        
        # Complex text
        complex_text = """
        The implementation of sophisticated machine learning algorithms necessitates
        comprehensive understanding of mathematical foundations, statistical principles,
        and computational complexity considerations that significantly impact performance
        optimization strategies in distributed computing environments.
        """
        analysis = processor.analyze_text(complex_text)
        assert analysis.readability_score < 50  # Should be lower readability
    
    def test_sentence_statistics(self, processor):
        """Test sentence-level statistics calculation."""
        text = """
        This is the first sentence. This is a longer sentence with more words
        to test the average calculation. Short one. Another sentence of moderate
        length for testing purposes.
        """
        
        analysis = processor.analyze_text(text)
        
        assert analysis.sentence_count == 4
        assert analysis.avg_sentence_length > 0
        assert 5 <= analysis.avg_sentence_length <= 15  # Reasonable range
    
    def test_vocabulary_analysis(self, processor):
        """Test vocabulary richness calculation."""
        # Repetitive text
        repetitive_text = "The cat sat on the mat. The cat was on the mat. The mat had the cat."
        analysis = processor.analyze_text(repetitive_text)
        assert analysis.vocabulary_richness < 0.7  # Lower vocabulary richness
        
        # Diverse text
        diverse_text = """
        The magnificent elephant wandered through the pristine forest.
        Crystalline waterfalls cascaded down granite cliffs while
        exotic birds performed aerial ballet above emerald canopies.
        """
        analysis = processor.analyze_text(diverse_text)
        assert analysis.vocabulary_richness > 0.8  # Higher vocabulary richness
    
    def test_topic_extraction(self, processor):
        """Test topic extraction from text."""
        text = """
        Python is a powerful programming language used for web development,
        data science, and machine learning. Django and Flask are popular
        web frameworks for Python. NumPy and Pandas are essential libraries
        for data analysis. Scikit-learn provides machine learning algorithms.
        """
        
        analysis = processor.analyze_text(text)
        
        assert len(analysis.topics) > 0
        
        # Check if relevant topics are identified
        topic_keywords = [kw for topic in analysis.topics for kw in topic.keywords]
        expected_keywords = ['python', 'programming', 'web', 'data', 'machine learning']
        
        found_keywords = sum(1 for kw in expected_keywords 
                           if any(kw.lower() in keyword.lower() for keyword in topic_keywords))
        assert found_keywords >= 2  # Should find at least 2 relevant keywords
    
    def test_key_phrases_extraction(self, processor):
        """Test key phrase extraction."""
        text = """
        Artificial intelligence and machine learning are transforming industries.
        Natural language processing enables computers to understand human language.
        Deep learning networks can process vast amounts of data efficiently.
        """
        
        analysis = processor.analyze_text(text)
        
        assert len(analysis.key_phrases) > 0
        
        # Check for multi-word phrases
        multi_word_phrases = [phrase for phrase in analysis.key_phrases if ' ' in phrase]
        assert len(multi_word_phrases) > 0
    
    def test_semantic_chunking(self, processor):
        """Test semantic-aware text chunking."""
        text = """
        Introduction to Machine Learning
        
        Machine learning is a subset of artificial intelligence that enables
        computers to learn and improve from experience without being explicitly
        programmed. It focuses on developing algorithms that can access data
        and use it to learn for themselves.
        
        Types of Machine Learning
        
        There are three main types of machine learning: supervised learning,
        unsupervised learning, and reinforcement learning. Each type has its
        own characteristics and applications.
        
        Supervised Learning
        
        Supervised learning uses labeled training data to learn a mapping
        function from input variables to output variables. Common algorithms
        include linear regression, decision trees, and neural networks.
        """
        
        chunks = processor.extract_semantic_chunks(text, target_size=200)
        
        assert len(chunks) > 1
        
        # Verify chunks are meaningful
        for chunk in chunks:
            assert len(chunk.strip()) > 50  # Not too small
            assert len(chunk.strip()) < 500  # Not too large
            
        # Verify semantic coherence (chunks should end at natural boundaries)
        for chunk in chunks[:-1]:  # All but last chunk
            assert chunk.strip().endswith(('.', '!', '?', ':')) or '\n\n' in chunk
    
    def test_structured_content_extraction(self, processor):
        """Test extraction of structured content elements."""
        text = """
        Project Setup Instructions
        
        Prerequisites:
        - Python 3.8 or higher
        - Git version control
        - Text editor or IDE
        
        Installation Steps:
        1. Clone the repository
        2. Create virtual environment
        3. Install dependencies
        4. Configure settings
        
        Common Issues:
        • Permission denied errors
        • Missing dependencies
        • Configuration problems
        
        Tips for Success:
        ✓ Always backup your work
        ✓ Read documentation carefully
        ✓ Test in development environment first
        """
        
        structured = processor.extract_structured_content(text)
        
        assert 'lists' in structured
        assert len(structured['lists']) >= 3
        
        # Check for different list types
        list_types = [lst['type'] for lst in structured['lists']]
        assert 'bulleted' in list_types or 'hyphenated' in list_types
        assert 'numbered' in list_types


class TestParagraphDetector:
    """Test paragraph detection functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create a ParagraphDetector instance."""
        return ParagraphDetector()
    
    def test_basic_paragraph_detection(self, detector):
        """Test basic paragraph detection."""
        text = """This is the first paragraph.
It contains multiple sentences on different lines.

This is the second paragraph.

This is the third paragraph with a single line."""
        
        paragraphs = detector.detect_paragraphs(text)
        
        assert len(paragraphs) == 3
        
        # Check first paragraph
        assert "first paragraph" in paragraphs[0].text
        assert "multiple sentences" in paragraphs[0].text
        
        # Check line numbers
        assert paragraphs[0].start_line == 0
        assert paragraphs[1].start_line > paragraphs[0].end_line
        assert paragraphs[2].start_line > paragraphs[1].end_line
    
    def test_code_block_detection(self, detector):
        """Test detection of code blocks as special paragraphs."""
        text = """This is regular text.

    # This is an indented code block
    def function():
        return "code"

Back to regular text.

```python
# This is a fenced code block
print("Hello, World!")
```

More regular text."""
        
        paragraphs = detector.detect_paragraphs(text)
        
        # Find code paragraphs
        code_paragraphs = [p for p in paragraphs if p.is_code_block]
        assert len(code_paragraphs) >= 1
        
        # Verify code content
        indented_code = next((p for p in code_paragraphs if "def function" in p.text), None)
        if indented_code:
            assert indented_code.is_code_block
    
    def test_list_detection(self, detector):
        """Test detection of list items."""
        text = """Regular paragraph before list.

- First bullet item
- Second bullet item
  - Nested item
- Third bullet item

1. First numbered item
2. Second numbered item
   a. Nested letter item
   b. Another nested item

Regular paragraph after list."""
        
        paragraphs = detector.detect_paragraphs(text)
        
        # Find list paragraphs
        list_paragraphs = [p for p in paragraphs if p.is_list_item]
        assert len(list_paragraphs) >= 6  # Should detect most list items
        
        # Check list types
        bullet_items = [p for p in list_paragraphs if p.text.strip().startswith('-')]
        numbered_items = [p for p in list_paragraphs if re.match(r'^\d+\.', p.text.strip())]
        
        assert len(bullet_items) >= 3
        assert len(numbered_items) >= 2
    
    def test_heading_detection(self, detector):
        """Test detection of headings in plain text."""
        text = """MAIN TITLE

This is content under the main title.

Subtitle in Title Case

More content here.

Another Section
===============

Content with underline heading.

Yet Another Section
-------------------

Content with another underline style."""
        
        paragraphs = detector.detect_paragraphs(text)
        
        # Check for potential headings
        potential_headings = []
        for p in paragraphs:
            if (len(p.text.split()) <= 5 and 
                not p.text.endswith('.') and
                (p.text.isupper() or p.text.istitle())):
                potential_headings.append(p)
        
        assert len(potential_headings) >= 2
    
    def test_empty_line_handling(self, detector):
        """Test handling of multiple empty lines."""
        text = """First paragraph.



Second paragraph after multiple empty lines.


Third paragraph."""
        
        paragraphs = detector.detect_paragraphs(text)
        
        assert len(paragraphs) == 3
        assert "First paragraph" in paragraphs[0].text
        assert "Second paragraph" in paragraphs[1].text
        assert "Third paragraph" in paragraphs[2].text
    
    def test_mixed_content_detection(self, detector):
        """Test detection in mixed content with various elements."""
        text = """# Markdown-style heading

Regular paragraph with **markdown** formatting.

- List item one
- List item two

    Code block here
    with multiple lines

> Blockquote text
> spanning multiple lines

Regular paragraph at the end."""
        
        paragraphs = detector.detect_paragraphs(text)
        
        assert len(paragraphs) >= 5
        
        # Should handle mixed content gracefully
        content_types = []
        for p in paragraphs:
            if p.is_code_block:
                content_types.append('code')
            elif p.is_list_item:
                content_types.append('list')
            elif p.text.startswith('#'):
                content_types.append('heading')
            elif p.text.startswith('>'):
                content_types.append('quote')
            else:
                content_types.append('text')
        
        assert 'text' in content_types
        assert len(set(content_types)) >= 2  # Should detect multiple types


class TestSentenceSplitter:
    """Test sentence splitting functionality."""
    
    @pytest.fixture
    def splitter(self):
        """Create a SentenceSplitter instance."""
        return SentenceSplitter()
    
    def test_basic_sentence_splitting(self, splitter):
        """Test basic sentence splitting."""
        text = "This is the first sentence. This is the second sentence! Is this a question?"
        
        sentences = splitter.split_sentences(text)
        
        assert len(sentences) == 3
        assert sentences[0].strip() == "This is the first sentence."
        assert sentences[1].strip() == "This is the second sentence!"
        assert sentences[2].strip() == "Is this a question?"
    
    def test_abbreviation_handling(self, splitter):
        """Test handling of abbreviations and acronyms."""
        text = "Dr. Smith works at NASA. The U.S. government funds research. Mr. Jones disagrees."
        
        sentences = splitter.split_sentences(text)
        
        # Should not split at abbreviations
        assert len(sentences) == 3
        assert "Dr. Smith works at NASA" in sentences[0]
        assert "U.S. government" in sentences[1]
        assert "Mr. Jones" in sentences[2]
    
    def test_decimal_number_handling(self, splitter):
        """Test handling of decimal numbers."""
        text = "The price is $19.99 for the item. Version 2.0 was released. It costs 3.14 dollars."
        
        sentences = splitter.split_sentences(text)
        
        # Should not split at decimal points
        assert len(sentences) == 3
        assert "$19.99" in sentences[0]
        assert "Version 2.0" in sentences[1]
        assert "3.14 dollars" in sentences[2]
    
    def test_quotation_handling(self, splitter):
        """Test handling of sentences with quotations."""
        text = 'He said, "This is important." She replied, "I agree completely!" They nodded.'
        
        sentences = splitter.split_sentences(text)
        
        assert len(sentences) == 3
        assert 'He said, "This is important."' in sentences[0]
        assert 'She replied, "I agree completely!"' in sentences[1]
        assert "They nodded" in sentences[2]
    
    def test_complex_punctuation(self, splitter):
        """Test handling of complex punctuation patterns."""
        text = "What?! You can't be serious... Well, I suppose it's possible. (But unlikely.)"
        
        sentences = splitter.split_sentences(text)
        
        # Should handle complex punctuation
        assert len(sentences) >= 2
        assert "What?!" in sentences[0]
        assert "serious..." in sentences[0] or "serious" in sentences[0]
    
    def test_code_and_urls(self, splitter):
        """Test handling of code snippets and URLs."""
        text = "Visit www.example.com for info. Use object.method() in code. The file is config.json format."
        
        sentences = splitter.split_sentences(text)
        
        # Should not split at dots in URLs or code
        assert len(sentences) == 3
        assert "www.example.com" in sentences[0]
        assert "object.method()" in sentences[1]
        assert "config.json" in sentences[2]


class TestTopicExtractor:
    """Test topic and keyword extraction functionality."""
    
    @pytest.fixture
    def extractor(self):
        """Create a TopicExtractor instance."""
        return TopicExtractor()
    
    def test_keyword_extraction(self, extractor):
        """Test basic keyword extraction."""
        text = """
        Python programming is essential for data science and machine learning.
        Libraries like NumPy, Pandas, and Scikit-learn are fundamental tools.
        Statistical analysis and algorithmic thinking are crucial skills.
        """
        
        keywords = extractor.extract_keywords(text, max_keywords=10)
        
        assert len(keywords) > 0
        assert len(keywords) <= 10
        
        # Verify format (keyword, score)
        for keyword, score in keywords:
            assert isinstance(keyword, str)
            assert isinstance(score, (int, float))
            assert len(keyword) > 0
        
        # Check for relevant keywords
        keyword_list = [kw.lower() for kw, _ in keywords]
        expected = ['python', 'programming', 'data', 'machine', 'learning']
        found = sum(1 for exp in expected if any(exp in kw for kw in keyword_list))
        assert found >= 2
    
    def test_phrase_extraction(self, extractor):
        """Test extraction of multi-word phrases."""
        text = """
        Natural language processing enables advanced text analysis.
        Machine learning algorithms can identify semantic patterns.
        Deep neural networks process complex linguistic structures.
        """
        
        phrases = extractor.extract_phrases(text, max_phrases=8)
        
        assert len(phrases) > 0
        
        # Check for multi-word phrases
        multi_word = [phrase for phrase, _ in phrases if ' ' in phrase]
        assert len(multi_word) > 0
        
        # Check for relevant technical phrases
        phrase_list = [phrase.lower() for phrase, _ in phrases]
        expected_phrases = ['natural language', 'machine learning', 'neural networks']
        found_phrases = sum(1 for exp in expected_phrases 
                          if any(exp in phrase for phrase in phrase_list))
        assert found_phrases >= 1
    
    def test_technical_term_extraction(self, extractor):
        """Test extraction of technical terms."""
        text = """
        REST API endpoints use HTTP methods like GET, POST, PUT, DELETE.
        JSON serialization handles data transfer between client and server.
        Authentication mechanisms include JWT tokens and OAuth2 flows.
        Database transactions ensure ACID compliance in PostgreSQL.
        """
        
        technical_terms = extractor.extract_technical_terms(text)
        
        assert len(technical_terms) > 0
        
        # Check for technical terms
        terms_lower = [term.lower() for term in technical_terms]
        expected_terms = ['api', 'http', 'json', 'jwt', 'oauth', 'database', 'postgresql']
        found_terms = sum(1 for exp in expected_terms if any(exp in term for term in terms_lower))
        assert found_terms >= 3
    
    def test_topic_clustering(self, extractor):
        """Test clustering of related keywords into topics."""
        text = """
        Web development involves HTML, CSS, and JavaScript programming.
        Frontend frameworks like React and Vue.js create interactive interfaces.
        Backend services use Node.js, Python Flask, or Django frameworks.
        Database systems like MongoDB and PostgreSQL store application data.
        DevOps practices include Docker containerization and AWS deployment.
        """
        
        topics = extractor.extract_topics(text, num_topics=3)
        
        assert len(topics) > 0
        assert len(topics) <= 3
        
        # Check topic structure
        for topic in topics:
            assert hasattr(topic, 'keywords')
            assert hasattr(topic, 'score')
            assert len(topic.keywords) > 0
            assert isinstance(topic.score, (int, float))
        
        # Verify topic coherence
        all_keywords = [kw for topic in topics for kw in topic.keywords]
        web_related = ['web', 'html', 'css', 'javascript', 'frontend', 'backend']
        found_web = sum(1 for kw in all_keywords if any(web in kw.lower() for web in web_related))
        assert found_web >= 2
    
    def test_named_entity_extraction(self, extractor):
        """Test extraction of named entities."""
        text = """
        Microsoft Azure and Amazon Web Services are major cloud providers.
        Google Cloud Platform competes with these services globally.
        IBM Watson provides artificial intelligence capabilities.
        Tesla uses machine learning for autonomous vehicle development.
        """
        
        entities = extractor.extract_named_entities(text)
        
        assert len(entities) > 0
        
        # Check for company names
        entity_list = [entity.lower() for entity in entities]
        companies = ['microsoft', 'amazon', 'google', 'ibm', 'tesla']
        found_companies = sum(1 for comp in companies if any(comp in ent for ent in entity_list))
        assert found_companies >= 2
    
    def test_sentiment_analysis(self, extractor):
        """Test basic sentiment analysis."""
        positive_text = "This is an excellent product with amazing features and outstanding performance."
        negative_text = "This is a terrible product with awful quality and horrible user experience."
        neutral_text = "This product has standard features and average performance characteristics."
        
        pos_sentiment = extractor.analyze_sentiment(positive_text)
        neg_sentiment = extractor.analyze_sentiment(negative_text)
        neu_sentiment = extractor.analyze_sentiment(neutral_text)
        
        # Verify sentiment scores
        assert pos_sentiment > neu_sentiment
        assert neg_sentiment < neu_sentiment
        assert -1 <= pos_sentiment <= 1
        assert -1 <= neg_sentiment <= 1
        assert -1 <= neu_sentiment <= 1


class TestPlainTextPlugin:
    """Test the complete PlainText plugin functionality."""
    
    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database."""
        db_path = tmp_path / "test.db"
        return SQLiteStore(str(db_path))
    
    @pytest.fixture
    def plugin(self, temp_db):
        """Create a PlainTextPlugin instance."""
        language_config = {
            "name": "plaintext",
            "code": "txt",
            "extensions": [".txt", ".text", ".md", ".rst", ".log"],
            "language": "plaintext"
        }
        return PlainTextPlugin(language_config, sqlite_store=temp_db, enable_semantic=False)
    
    @pytest.fixture
    def sample_text_file(self, tmp_path):
        """Create a sample text file."""
        content = """Project Documentation

Introduction

This document provides comprehensive information about our software project.
The project aims to create a robust and scalable application using modern
development practices and technologies.

Technical Architecture

The system follows a microservices architecture pattern with the following components:

- API Gateway for request routing
- Authentication service for user management  
- Business logic services for core functionality
- Database layer for data persistence
- Monitoring and logging infrastructure

Implementation Details

Backend Development:
The backend is implemented using Python with FastAPI framework.
Database operations use SQLAlchemy ORM for data modeling.
Redis is used for caching and session management.
Celery handles asynchronous task processing.

Frontend Development:
The user interface is built with React and TypeScript.
State management uses Redux toolkit for predictable updates.
Material-UI provides consistent design components.
Webpack bundles the application for production deployment.

Deployment Strategy

The application is containerized using Docker containers.
Kubernetes orchestrates the container deployment and scaling.
CI/CD pipelines automate testing and deployment processes.
AWS cloud infrastructure provides hosting and scalability.

Performance Considerations

Load balancing distributes traffic across multiple instances.
Database indexing optimizes query performance.
Caching strategies reduce response times significantly.
CDN delivers static assets with minimal latency.

Security Measures

Authentication uses JWT tokens with refresh mechanisms.
API endpoints implement rate limiting and validation.
HTTPS encryption protects data transmission.
Regular security audits identify potential vulnerabilities.

Conclusion

This architecture provides a solid foundation for scalable application development.
The chosen technologies and patterns support maintainability and performance.
Future enhancements can be implemented without major architectural changes.
"""
        
        file_path = tmp_path / "project_docs.txt"
        file_path.write_text(content)
        return file_path, content
    
    def test_file_support(self, plugin):
        """Test file extension support."""
        assert plugin.supports("document.txt")
        assert plugin.supports("readme.text")
        assert plugin.supports("notes.md")
        assert plugin.supports("guide.rst")
        assert plugin.supports("application.log")
        assert not plugin.supports("script.py")
        assert not plugin.supports("data.json")
    
    def test_metadata_extraction(self, plugin, sample_text_file):
        """Test metadata extraction from plain text."""
        file_path, content = sample_text_file
        
        metadata = plugin.extract_metadata(content, file_path)
        
        # Verify basic metadata
        assert metadata.title == "Project Documentation"  # First heading
        assert metadata.document_type in ['technical', 'instructional', 'mixed']
        assert metadata.language == 'en'
        assert len(metadata.tags) > 0
        
        # Verify NLP-derived metadata
        assert 'readability_score' in metadata.custom
        assert 'avg_sentence_length' in metadata.custom
        assert 'vocabulary_richness' in metadata.custom
        assert 'topics' in metadata.custom
    
    def test_structure_extraction(self, plugin, sample_text_file):
        """Test document structure extraction."""
        file_path, content = sample_text_file
        
        structure = plugin.extract_structure(content, file_path)
        
        # Verify structure components
        assert len(structure.sections) >= 5
        assert len(structure.headings) >= 5
        assert structure.outline is not None
        
        # Check for main sections
        section_titles = [s.get('title', '') for s in structure.sections]
        expected_sections = ['Introduction', 'Technical Architecture', 'Implementation Details']
        found_sections = sum(1 for exp in expected_sections if any(exp in title for title in section_titles))
        assert found_sections >= 2
        
        # Verify heading hierarchy
        heading_levels = [h['level'] for h in structure.headings]
        assert min(heading_levels) == 1  # Should have top-level headings
        assert len(set(heading_levels)) >= 2  # Should have multiple levels
    
    def test_content_parsing(self, plugin, sample_text_file):
        """Test content parsing and cleaning."""
        file_path, content = sample_text_file
        
        parsed_content = plugin.parse_content(content, file_path)
        
        # Verify content cleaning
        assert len(parsed_content) > 0
        assert "Project Documentation" in parsed_content
        assert "microservices architecture" in parsed_content
        
        # Verify encoding fixes and normalization
        assert '\r\n' not in parsed_content  # Should normalize line endings
        assert '\n\n\n' not in parsed_content  # Should remove excessive blank lines
    
    def test_intelligent_chunking(self, plugin, sample_text_file):
        """Test NLP-aware intelligent chunking."""
        file_path, content = sample_text_file
        
        # Extract structure first
        structure = plugin.extract_structure(content, file_path)
        
        # Perform intelligent chunking
        chunks = plugin._intelligent_chunk(content, structure)
        
        # Verify chunks
        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        
        # Verify chunk content
        for chunk in chunks:
            assert len(chunk.content) > 50  # Meaningful content
            assert chunk.chunk_index >= 0
            assert chunk.metadata is not None
        
        # Verify semantic coherence
        total_content = "".join(chunk.content for chunk in chunks)
        assert "Project Documentation" in total_content
        assert "microservices" in total_content
    
    def test_search_functionality(self, plugin, sample_text_file):
        """Test enhanced search with NLP understanding."""
        file_path, content = sample_text_file
        
        # Index the content first
        plugin.indexFile(file_path, content)
        
        # Test search queries
        queries = [
            "microservices architecture",
            "Python FastAPI",
            "Docker containers",
            "security measures"
        ]
        
        for query in queries:
            results = plugin.search(query, opts={'limit': 5})
            
            # Should return relevant results
            assert isinstance(results, list)
            
            # If results found, verify relevance
            if results:
                for result in results:
                    assert 'file' in result
                    assert 'snippet' in result
                    assert 'relevance' in result
                    assert result['relevance'] > 0
    
    def test_technical_text_processing(self, plugin, tmp_path):
        """Test processing of technical documentation."""
        technical_content = """API Reference Guide

Authentication

All API requests require authentication using Bearer tokens.
Include the token in the Authorization header:

Authorization: Bearer YOUR_TOKEN_HERE

Rate limiting applies to all endpoints (100 requests per minute).

Endpoints

GET /api/users
Retrieves a list of all users in the system.

Parameters:
- limit (integer): Maximum number of results (default: 20)
- offset (integer): Number of results to skip (default: 0)
- filter (string): Filter expression for results

Response:
Returns JSON array of user objects with following fields:
- id (integer): Unique user identifier
- username (string): User login name
- email (string): User email address
- created_at (timestamp): Account creation date

Error Codes:
- 400: Bad Request - Invalid parameters
- 401: Unauthorized - Missing or invalid token
- 429: Too Many Requests - Rate limit exceeded
- 500: Internal Server Error - Server processing error

POST /api/users
Creates a new user account.

Request Body:
{
  "username": "string",
  "email": "string", 
  "password": "string"
}
"""
        
        file_path = tmp_path / "api_guide.txt"
        file_path.write_text(technical_content)
        
        # Test technical text processing
        metadata = plugin.extract_metadata(technical_content, file_path)
        assert metadata.document_type == 'technical'
        
        # Should extract technical terms
        assert any('api' in tag.lower() for tag in metadata.tags)
        
        structure = plugin.extract_structure(technical_content, file_path)
        assert len(structure.sections) >= 3  # Should identify main sections
    
    def test_narrative_text_processing(self, plugin, tmp_path):
        """Test processing of narrative text."""
        narrative_content = """The Journey Home

Chapter 1: Departure

Sarah stood at the train station platform, clutching her worn leather suitcase
with both hands. The morning mist swirled around her ankles as the old steam
engine approached with a thunderous roar. She had been planning this journey
for months, saving every penny to buy the ticket that would take her back
to the small town where she grew up.

The conductor, a kindly old man with silver whiskers, helped her aboard
and found her a window seat in the nearly empty car. As the train pulled
away from the station, Sarah watched the city skyline fade into the distance.
Buildings gave way to rolling hills dotted with farmhouses and red barns.

Chapter 2: Memories

During the long ride, Sarah's mind wandered to her childhood memories.
She remembered running through fields of sunflowers with her sister Emma,
building forts in the old oak tree behind their house, and the smell of
her grandmother's apple pie cooling on the kitchen windowsill.

Those were simpler times, when her biggest worry was whether it would rain
on the day of the annual summer fair. Now, at thirty-five, she carried
the weight of failed relationships, career disappointments, and the recent
loss of her father. The journey home felt like both an escape and a return
to something she had lost along the way.
"""
        
        file_path = tmp_path / "story.txt"
        file_path.write_text(narrative_content)
        
        # Test narrative text processing
        metadata = plugin.extract_metadata(narrative_content, file_path)
        assert metadata.document_type == 'narrative'
        
        # Should have reasonable readability for narrative
        assert metadata.custom['readability_score'] > 60
        
        structure = plugin.extract_structure(narrative_content, file_path)
        chapter_sections = [s for s in structure.sections if 'chapter' in s.get('title', '').lower()]
        assert len(chapter_sections) >= 2
    
    def test_instructional_text_processing(self, plugin, tmp_path):
        """Test processing of instructional text."""
        instructional_content = """How to Install Python on Your Computer

Prerequisites

Before installing Python, make sure you have:
- Administrator access to your computer
- At least 100 MB of free disk space
- Internet connection for downloading

Step-by-Step Installation

Windows Installation:

1. Go to the official Python website (python.org)
2. Click on the "Downloads" tab
3. Select the latest version for Windows
4. Run the downloaded installer
5. Check "Add Python to PATH" during installation
6. Click "Install Now" to begin the process
7. Wait for the installation to complete
8. Click "Close" when finished

macOS Installation:

1. Download the macOS installer from python.org
2. Double-click the downloaded .pkg file
3. Follow the installation wizard prompts
4. Enter your password when requested
5. Complete the installation process

Linux Installation:

Most Linux distributions include Python by default.
To install the latest version:

1. Open terminal
2. Update package manager: sudo apt update
3. Install Python: sudo apt install python3
4. Verify installation: python3 --version

Verification Steps

To verify Python is installed correctly:

1. Open command prompt or terminal
2. Type: python --version
3. You should see the version number displayed
4. Type: python to start the Python interpreter
5. Try: print("Hello, World!")
6. Type: exit() to quit the interpreter

Troubleshooting

Common Issues:

Problem: "Python is not recognized as an internal or external command"
Solution: Add Python to your system PATH environment variable

Problem: Permission denied errors during installation
Solution: Run installer as administrator

Problem: Installation fails with error messages
Solution: Temporarily disable antivirus software during installation

Warning: Always download Python from the official website to avoid malware.

Tip: Consider using a virtual environment for your Python projects.
"""
        
        file_path = tmp_path / "python_install.txt"
        file_path.write_text(instructional_content)
        
        # Test instructional text processing
        metadata = plugin.extract_metadata(instructional_content, file_path)
        assert metadata.document_type == 'instructional'
        
        structure = plugin.extract_structure(instructional_content, file_path)
        
        # Should identify step-by-step structure
        section_titles = [s.get('title', '') for s in structure.sections]
        expected_sections = ['Prerequisites', 'Installation', 'Verification', 'Troubleshooting']
        found = sum(1 for exp in expected_sections if any(exp.lower() in title.lower() for title in section_titles))
        assert found >= 2
    
    def test_mixed_content_processing(self, plugin, tmp_path):
        """Test processing of mixed content types."""
        mixed_content = """Product Requirements Document

Executive Summary

This document outlines the requirements for the new mobile application.
The app will provide users with real-time weather information and alerts.

User Stories

As a user, I want to:
- View current weather conditions for my location
- Receive severe weather alerts and notifications
- Check hourly and weekly weather forecasts
- Save multiple locations for quick access
- Share weather information with friends

Technical Specifications

The application will be developed using React Native framework.
Backend services will use Node.js with MongoDB database.
Real-time data will be sourced from OpenWeatherMap API.

API Integration:

```
GET /weather/current?lat={latitude}&lon={longitude}
Response: {
  "temperature": 72,
  "humidity": 65,
  "conditions": "partly cloudy"
}
```

Performance Requirements:
- App startup time: < 3 seconds
- API response time: < 500ms
- Battery usage: minimal impact

Installation Guide

Development Setup:

1. Install Node.js (version 14 or higher)
2. Install React Native CLI
3. Clone the repository
4. Run npm install
5. Configure API keys
6. Start the development server

Warning: Never commit API keys to version control.

Once upon a time, there was a weather app that changed everything...
Just kidding! This is a technical document, not a fairy tale.

Conclusion

The weather application will provide valuable functionality to users
while maintaining high performance and reliability standards.
"""
        
        file_path = tmp_path / "mixed_doc.txt"
        file_path.write_text(mixed_content)
        
        # Test mixed content processing
        metadata = plugin.extract_metadata(mixed_content, file_path)
        assert metadata.document_type in ['mixed', 'technical', 'instructional']
        
        structure = plugin.extract_structure(mixed_content, file_path)
        assert len(structure.sections) >= 4
        
        # Should handle various content types
        chunks = plugin._intelligent_chunk(mixed_content, structure)
        assert len(chunks) > 1
    
    def test_large_document_handling(self, plugin, tmp_path):
        """Test handling of large plain text documents."""
        # Generate large content
        sections = []
        for i in range(100):
            section = f"""Section {i}

This is section number {i} of the large document. """ + ("Lorem ipsum dolor sit amet. " * 10)
            sections.append(section)
        
        large_content = "Large Document\n\n" + "\n\n".join(sections)
        
        file_path = tmp_path / "large_doc.txt"
        file_path.write_text(large_content)
        
        # Test processing
        import time
        start_time = time.time()
        
        metadata = plugin.extract_metadata(large_content, file_path)
        structure = plugin.extract_structure(large_content, file_path)
        chunks = plugin._intelligent_chunk(large_content, structure)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Should complete in reasonable time
        assert elapsed < 30.0, f"Processing took too long: {elapsed:.2f}s"
        
        # Verify results
        assert metadata is not None
        assert len(structure.sections) > 50
        assert len(chunks) > 10
    
    def test_encoding_edge_cases(self, plugin, tmp_path):
        """Test handling of various text encodings and edge cases."""
        edge_case_content = """Special Characters Test

This document contains various special characters and encodings:

Unicode characters: café, naïve, résumé, Björk, 北京
Punctuation: "smart quotes", 'apostrophes', em—dashes, ellipses…
Symbols: ©2024, ®trademark, ™symbol, §section, ¶paragraph
Mathematics: α + β = γ, ∑, ∫, √, ≈, ≠, ≤, ≥
Currency: $100, €50, £25, ¥1000, ₹500

URLs and Emails:
- https://www.example.com/path?param=value
- user@domain.co.uk
- ftp://files.example.org/resource

Code snippets:
```
function test() {
    return "Hello, World!";
}
```

File paths:
- C:\\Users\\Name\\Documents\\file.txt
- /home/user/documents/file.txt
- ~/Desktop/project/

Weird spacing     and      tabs	mixed	with spaces.

Empty lines:



Multiple empty lines should be handled gracefully.

The end."""
        
        file_path = tmp_path / "edge_cases.txt"
        file_path.write_text(edge_case_content, encoding='utf-8')
        
        # Test processing with edge cases
        try:
            metadata = plugin.extract_metadata(edge_case_content, file_path)
            structure = plugin.extract_structure(edge_case_content, file_path)
            parsed_content = plugin.parse_content(edge_case_content, file_path)
            
            # Should handle gracefully
            assert metadata is not None
            assert structure is not None
            assert len(parsed_content) > 0
            
            # Should preserve important content
            assert "Special Characters" in parsed_content
            assert "Unicode characters" in parsed_content
            assert "example.com" in parsed_content
            
        except Exception as e:
            pytest.fail(f"Should handle edge cases gracefully: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])