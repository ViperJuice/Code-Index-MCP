"""Test cases for natural language query processing."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.document_processing.semantic_chunker import SemanticChunker
from tests.base_test import BaseDocumentTest


class TestNaturalLanguageQueries(BaseDocumentTest):
    """Test natural language query parsing, intent detection, expansion, and ranking."""

    def test_query_parsing_basic(self):
        """Test basic query parsing and tokenization."""
        queries = [
            "find all Python functions",
            "show me the main class",
            "search for error handling code",
            "what does the calculate_total function do?",
            "where is user authentication implemented?",
        ]

        for query in queries:
            # Parse query
            result = self.dispatcher.parse_query(query)

            assert result is not None
            assert "tokens" in result
            assert "intent" in result
            assert "entities" in result
            assert len(result["tokens"]) > 0

            # Check for expected entities
            if "function" in query.lower():
                assert any(e["type"] == "symbol_type" for e in result["entities"])
            if "class" in query.lower():
                assert any(e["type"] == "symbol_type" for e in result["entities"])

    def test_intent_detection_types(self):
        """Test different query intent detection."""
        test_cases = [
            # (query, expected_intent)
            ("find all functions", "symbol_search"),
            ("show me the documentation", "documentation_search"),
            ("what does this function do?", "explanation"),
            ("where is X implemented?", "location_search"),
            ("how to use this API?", "usage_search"),
            ("list all classes in module", "listing"),
            ("search for error handling", "concept_search"),
            ("show relationships between classes", "relationship_search"),
        ]

        for query, expected_intent in test_cases:
            result = self.dispatcher.detect_intent(query)

            assert result is not None
            assert "intent" in result
            assert "confidence" in result
            assert result["intent"] == expected_intent
            assert 0 <= result["confidence"] <= 1

    def test_query_expansion_synonyms(self):
        """Test query expansion with synonyms and related terms."""
        test_queries = {
            "function": ["function", "method", "def", "procedure", "func"],
            "class": ["class", "type", "object", "struct", "interface"],
            "error": ["error", "exception", "failure", "bug", "issue"],
            "test": ["test", "unittest", "pytest", "spec", "testcase"],
            "config": ["config", "configuration", "settings", "options", "preferences"],
        }

        for base_query, expected_terms in test_queries.items():
            expanded = self.dispatcher.expand_query(base_query)

            assert expanded is not None
            assert "original" in expanded
            assert "expanded_terms" in expanded
            assert "synonyms" in expanded
            assert expanded["original"] == base_query

            # Check that at least some expected terms are included
            all_terms = expanded["expanded_terms"] + expanded["synonyms"]
            matching_terms = [term for term in expected_terms if term in all_terms]
            assert len(matching_terms) >= 2

    def test_contextual_query_understanding(self):
        """Test understanding queries in context."""
        # Create test files with context
        self.create_test_file(
            "user_auth.py",
            '''
class UserAuthenticator:
    """Handles user authentication and authorization."""
    
    def login(self, username: str, password: str) -> bool:
        """Authenticate user with credentials."""
        # Check credentials
        return self._verify_credentials(username, password)
    
    def logout(self, session_id: str) -> None:
        """Logout user and invalidate session."""
        self._invalidate_session(session_id)
    
    def check_permission(self, user_id: str, resource: str) -> bool:
        """Check if user has permission to access resource."""
        return self._has_access(user_id, resource)
''',
        )

        # Index the file
        self.dispatcher.index_file(self.workspace / "user_auth.py")

        # Test contextual queries
        queries = [
            ("how does user login work?", ["login", "authenticate", "credentials"]),
            ("what handles authentication?", ["UserAuthenticator", "authentication"]),
            ("check user permissions", ["check_permission", "has_access", "resource"]),
            ("logout functionality", ["logout", "invalidate", "session"]),
        ]

        for query, expected_context in queries:
            result = self.dispatcher.search_with_context(query, self.workspace)

            assert result is not None
            assert "matches" in result
            assert len(result["matches"]) > 0

            # Check that context is understood
            found_context = any(
                any(ctx in str(match) for ctx in expected_context) for match in result["matches"]
            )
            assert found_context

    def test_fuzzy_matching_tolerance(self):
        """Test fuzzy matching for misspellings and variations."""
        # Create test content
        self.create_test_file(
            "math_utils.py",
            '''
def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    return sum(numbers) / len(numbers)

def compute_standard_deviation(values):
    """Compute standard deviation of values."""
    avg = calculate_average(values)
    variance = sum((x - avg) ** 2 for x in values) / len(values)
    return variance ** 0.5

class StatisticsCalculator:
    """Calculator for statistical operations."""
    
    def calculate_median(self, data):
        """Calculate median value."""
        sorted_data = sorted(data)
        n = len(sorted_data)
        if n % 2 == 0:
            return (sorted_data[n//2-1] + sorted_data[n//2]) / 2
        return sorted_data[n//2]
''',
        )

        self.dispatcher.index_file(self.workspace / "math_utils.py")

        # Test fuzzy queries with typos and variations
        fuzzy_queries = [
            ("calculat average", "calculate_average"),  # Missing 'e'
            ("compute standrd deviation", "compute_standard_deviation"),  # Typo
            ("statistcs calculator", "StatisticsCalculator"),  # Missing 'i'
            ("calc median", "calculate_median"),  # Abbreviation
            ("std deviation", "standard_deviation"),  # Common abbreviation
        ]

        for fuzzy_query, expected_match in fuzzy_queries:
            results = self.dispatcher.fuzzy_search(fuzzy_query, tolerance=0.8)

            assert results is not None
            assert len(results) > 0

            # Check that expected match is found despite typos
            found = any(expected_match.lower() in str(r).lower() for r in results)
            assert found

    def test_semantic_query_matching(self):
        """Test semantic understanding of queries."""
        # Create semantically rich content
        self.create_test_file(
            "data_processor.py",
            '''
class DataProcessor:
    """Processes and transforms data for analysis."""
    
    def clean_data(self, raw_data):
        """Remove invalid entries and normalize data."""
        # Data cleansing logic
        cleaned = []
        for item in raw_data:
            if self._is_valid(item):
                cleaned.append(self._normalize(item))
        return cleaned
    
    def aggregate_results(self, data_sets):
        """Combine multiple data sets into summary."""
        # Aggregation logic
        summary = {}
        for data in data_sets:
            self._merge_into_summary(summary, data)
        return summary
    
    def export_to_csv(self, data, filename):
        """Save processed data as CSV file."""
        import csv
        with open(filename, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
''',
        )

        self.dispatcher.index_file(self.workspace / "data_processor.py")

        # Test semantic queries
        semantic_queries = [
            ("remove bad data", ["clean_data", "invalid", "normalize"]),
            ("combine datasets", ["aggregate_results", "merge", "summary"]),
            ("save to file", ["export_to_csv", "save", "csv"]),
            ("data validation", ["is_valid", "clean", "invalid"]),
            ("merge information", ["aggregate", "combine", "merge_into_summary"]),
        ]

        with patch.object(self.dispatcher, "semantic_search") as mock_semantic:
            mock_semantic.return_value = [
                {"content": "clean_data", "score": 0.9},
                {"content": "aggregate_results", "score": 0.85},
            ]

            for query, expected_concepts in semantic_queries:
                results = self.dispatcher.search_semantic(query)

                assert results is not None
                assert len(results) > 0

                # Verify semantic understanding
                found_concepts = [
                    concept
                    for concept in expected_concepts
                    if any(concept.lower() in str(r).lower() for r in results)
                ]
                assert len(found_concepts) > 0

    def test_ranking_algorithm_accuracy(self):
        """Test result ranking based on relevance."""
        # Create files with varying relevance
        self.create_test_file(
            "auth_main.py",
            '''
# Main authentication module
class AuthenticationManager:
    """Primary authentication system."""
    
    def authenticate_user(self, username, password):
        """Main user authentication method."""
        # Core authentication logic
        return True
''',
        )

        self.create_test_file(
            "auth_helper.py",
            '''
# Helper functions for authentication
def validate_password(password):
    """Check password strength."""
    return len(password) >= 8

def hash_password(password):
    """Hash password for storage."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
''',
        )

        self.create_test_file(
            "unrelated.py",
            '''
# Unrelated utility functions
def format_date(date):
    """Format date for display."""
    return date.strftime("%Y-%m-%d")

def calculate_age(birthdate):
    """Calculate age from birthdate."""
    from datetime import date
    today = date.today()
    return today.year - birthdate.year
''',
        )

        # Index all files
        for filename in ["auth_main.py", "auth_helper.py", "unrelated.py"]:
            self.dispatcher.index_file(self.workspace / filename)

        # Search for authentication-related content
        results = self.dispatcher.ranked_search(
            "user authentication system",
            ranking_factors={
                "name_match": 0.3,
                "content_match": 0.3,
                "semantic_similarity": 0.2,
                "file_relevance": 0.2,
            },
        )

        assert results is not None
        assert len(results) >= 2

        # Check ranking order - most relevant should be first
        result_files = [r.get("file", "") for r in results[:3]]

        # auth_main.py should rank highest
        assert "auth_main.py" in result_files[0]

        # auth_helper.py should rank second
        assert "auth_helper.py" in result_files[1] if len(result_files) > 1 else True

        # unrelated.py should rank lowest or not appear
        if len(result_files) > 2 and "unrelated.py" in result_files[2]:
            # If it appears, it should be last
            assert result_files.index("unrelated.py") == 2

    def test_multi_language_query_support(self):
        """Test queries that span multiple programming languages."""
        # Create files in different languages
        self.create_test_file(
            "backend.py",
            '''
class APIServer:
    def handle_request(self, request):
        """Process incoming API request."""
        return {"status": "success"}
''',
        )

        self.create_test_file(
            "frontend.js",
            """
class APIClient {
    async sendRequest(endpoint, data) {
        // Send request to backend API
        const response = await fetch(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
        return response.json();
    }
}
""",
        )

        self.create_test_file(
            "styles.css",
            """
/* API status indicator styles */
.api-status {
    color: green;
}
.api-error {
    color: red;
}
""",
        )

        # Index files
        for filename in ["backend.py", "frontend.js", "styles.css"]:
            self.dispatcher.index_file(self.workspace / filename)

        # Test cross-language queries
        results = self.dispatcher.search_cross_language("API request handling")

        assert results is not None
        assert len(results) >= 2

        # Should find matches in both Python and JavaScript
        languages = set(r.get("language", "") for r in results)
        assert "python" in languages
        assert "javascript" in languages
