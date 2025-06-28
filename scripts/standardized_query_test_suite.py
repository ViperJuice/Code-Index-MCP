#!/usr/bin/env python3
"""
Standardized Query Test Suite for MCP vs Native Performance Comparison

This module defines a comprehensive set of test queries across different categories
to ensure consistent and thorough testing of both MCP and native retrieval methods.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class QueryCategory(Enum):
    """Categories of test queries"""
    SYMBOL = "symbol"
    CONTENT = "content"
    NAVIGATION = "navigation"
    REFACTORING = "refactoring"
    UNDERSTANDING = "understanding"


@dataclass
class TestQuery:
    """A single test query with metadata"""
    query: str
    category: QueryCategory
    language_specific: bool = False
    languages: List[str] = None
    expected_result_type: str = "location"  # location, list, explanation
    complexity: str = "simple"  # simple, medium, complex


class StandardizedQueryTestSuite:
    """Comprehensive test suite with queries for all categories"""
    
    def __init__(self):
        self.queries = self._initialize_queries()
        self.language_mappings = self._initialize_language_mappings()
    
    def _initialize_queries(self) -> Dict[QueryCategory, List[TestQuery]]:
        """Initialize all test queries"""
        return {
            QueryCategory.SYMBOL: self._get_symbol_queries(),
            QueryCategory.CONTENT: self._get_content_queries(),
            QueryCategory.NAVIGATION: self._get_navigation_queries(),
            QueryCategory.REFACTORING: self._get_refactoring_queries(),
            QueryCategory.UNDERSTANDING: self._get_understanding_queries()
        }
    
    def _get_symbol_queries(self) -> List[TestQuery]:
        """Symbol search queries"""
        return [
            # Generic symbol queries
            TestQuery(
                "Find the definition of class {main_class}",
                QueryCategory.SYMBOL,
                expected_result_type="location"
            ),
            TestQuery(
                "Where is function {main_function} implemented?",
                QueryCategory.SYMBOL,
                expected_result_type="location"
            ),
            TestQuery(
                "Locate the {config_variable} variable declaration",
                QueryCategory.SYMBOL,
                expected_result_type="location"
            ),
            TestQuery(
                "Find all methods in class {main_class}",
                QueryCategory.SYMBOL,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Show me the constructor for {main_class}",
                QueryCategory.SYMBOL,
                expected_result_type="location"
            ),
            
            # Language-specific symbol queries
            TestQuery(
                "Find interface {main_interface}",
                QueryCategory.SYMBOL,
                language_specific=True,
                languages=["java", "typescript", "go", "csharp"],
                expected_result_type="location"
            ),
            TestQuery(
                "Locate trait {main_trait}",
                QueryCategory.SYMBOL,
                language_specific=True,
                languages=["rust"],
                expected_result_type="location"
            ),
            TestQuery(
                "Find protocol {main_protocol}",
                QueryCategory.SYMBOL,
                language_specific=True,
                languages=["swift"],
                expected_result_type="location"
            ),
            TestQuery(
                "Where is module {main_module} defined?",
                QueryCategory.SYMBOL,
                language_specific=True,
                languages=["python", "ruby", "elixir"],
                expected_result_type="location"
            ),
            TestQuery(
                "Find namespace {main_namespace}",
                QueryCategory.SYMBOL,
                language_specific=True,
                languages=["csharp", "cpp"],
                expected_result_type="location"
            ),
            
            # Complex symbol queries
            TestQuery(
                "Find all classes that inherit from {base_class}",
                QueryCategory.SYMBOL,
                expected_result_type="list",
                complexity="complex"
            ),
            TestQuery(
                "Show all functions that return {return_type}",
                QueryCategory.SYMBOL,
                expected_result_type="list",
                complexity="complex"
            ),
            TestQuery(
                "Find all constants starting with {prefix}",
                QueryCategory.SYMBOL,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Locate all async functions",
                QueryCategory.SYMBOL,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Find all exported symbols from {module_name}",
                QueryCategory.SYMBOL,
                expected_result_type="list",
                complexity="complex"
            ),
            
            # Edge cases
            TestQuery(
                "Find symbol with special characters: {special_symbol}",
                QueryCategory.SYMBOL,
                expected_result_type="location"
            ),
            TestQuery(
                "Locate overloaded function {overloaded_function}",
                QueryCategory.SYMBOL,
                expected_result_type="list"
            ),
            TestQuery(
                "Find generic class {generic_class}<T>",
                QueryCategory.SYMBOL,
                language_specific=True,
                languages=["java", "csharp", "typescript", "cpp"],
                expected_result_type="location"
            ),
            TestQuery(
                "Show decorator {decorator_name}",
                QueryCategory.SYMBOL,
                language_specific=True,
                languages=["python"],
                expected_result_type="location"
            ),
            TestQuery(
                "Find macro {macro_name}",
                QueryCategory.SYMBOL,
                language_specific=True,
                languages=["rust", "c", "cpp"],
                expected_result_type="location"
            )
        ]
    
    def _get_content_queries(self) -> List[TestQuery]:
        """Content search queries"""
        return [
            # Pattern searches
            TestQuery(
                "Search for TODO comments",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            TestQuery(
                "Find all FIXME or BUG comments",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            TestQuery(
                "Search for deprecated code",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            TestQuery(
                "Find error handling patterns",
                QueryCategory.CONTENT,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Search for database queries",
                QueryCategory.CONTENT,
                expected_result_type="list",
                complexity="medium"
            ),
            
            # API/endpoint searches
            TestQuery(
                "Find all API endpoints",
                QueryCategory.CONTENT,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Search for HTTP routes",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            TestQuery(
                "Find GraphQL queries",
                QueryCategory.CONTENT,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Locate REST API definitions",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            TestQuery(
                "Find webhook handlers",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            
            # Configuration searches
            TestQuery(
                "Search for configuration loading",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            TestQuery(
                "Find environment variable usage",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            TestQuery(
                "Locate feature flags",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            TestQuery(
                "Search for hardcoded values",
                QueryCategory.CONTENT,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Find connection strings",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            
            # Security-related searches
            TestQuery(
                "Find authentication code",
                QueryCategory.CONTENT,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Search for password handling",
                QueryCategory.CONTENT,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Find encryption usage",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            TestQuery(
                "Locate API key references",
                QueryCategory.CONTENT,
                expected_result_type="list"
            ),
            TestQuery(
                "Search for SQL injection vulnerabilities",
                QueryCategory.CONTENT,
                expected_result_type="list",
                complexity="complex"
            )
        ]
    
    def _get_navigation_queries(self) -> List[TestQuery]:
        """Navigation and exploration queries"""
        return [
            # Import/dependency navigation
            TestQuery(
                "Find all files importing {main_module}",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Show files that depend on {library_name}",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "List all external dependencies",
                QueryCategory.NAVIGATION,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Find circular dependencies",
                QueryCategory.NAVIGATION,
                expected_result_type="list",
                complexity="complex"
            ),
            TestQuery(
                "Show import hierarchy for {module_name}",
                QueryCategory.NAVIGATION,
                expected_result_type="list",
                complexity="complex"
            ),
            
            # Test file navigation
            TestQuery(
                "Find test files for {component_name}",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Show all unit tests",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Find integration tests",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Locate test fixtures",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Find mock implementations",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            
            # Documentation navigation
            TestQuery(
                "Find all markdown documentation",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Show API documentation files",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Find README files",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Locate architecture diagrams",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Find changelog or release notes",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            
            # Project structure navigation
            TestQuery(
                "List all configuration files",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Find build scripts",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Show all {language} files in {directory}",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "Find entry points",
                QueryCategory.NAVIGATION,
                expected_result_type="list"
            ),
            TestQuery(
                "List all interfaces or protocols",
                QueryCategory.NAVIGATION,
                expected_result_type="list",
                complexity="medium"
            )
        ]
    
    def _get_refactoring_queries(self) -> List[TestQuery]:
        """Refactoring analysis queries"""
        return [
            # Usage analysis
            TestQuery(
                "Find all usages of {symbol_name}",
                QueryCategory.REFACTORING,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Show all references to {class_name}",
                QueryCategory.REFACTORING,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Find all calls to {method_name}",
                QueryCategory.REFACTORING,
                expected_result_type="list"
            ),
            TestQuery(
                "List all instantiations of {class_name}",
                QueryCategory.REFACTORING,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Show impact of removing {function_name}",
                QueryCategory.REFACTORING,
                expected_result_type="list",
                complexity="complex"
            ),
            
            # Inheritance analysis
            TestQuery(
                "Find all subclasses of {base_class}",
                QueryCategory.REFACTORING,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "Show inheritance hierarchy for {class_name}",
                QueryCategory.REFACTORING,
                expected_result_type="list",
                complexity="complex"
            ),
            TestQuery(
                "Find all implementations of {interface_name}",
                QueryCategory.REFACTORING,
                expected_result_type="list",
                complexity="medium"
            ),
            TestQuery(
                "List overridden methods in {class_name}",
                QueryCategory.REFACTORING,
                expected_result_type="list"
            ),
            TestQuery(
                "Find unused inheritance",
                QueryCategory.REFACTORING,
                expected_result_type="list",
                complexity="complex"
            )
        ]
    
    def _get_understanding_queries(self) -> List[TestQuery]:
        """Code understanding queries"""
        return [
            # Functionality understanding
            TestQuery(
                "Explain how {feature_name} works",
                QueryCategory.UNDERSTANDING,
                expected_result_type="explanation",
                complexity="complex"
            ),
            TestQuery(
                "Show the flow of {process_name}",
                QueryCategory.UNDERSTANDING,
                expected_result_type="explanation",
                complexity="complex"
            ),
            TestQuery(
                "Find the entry point for {command_name}",
                QueryCategory.UNDERSTANDING,
                expected_result_type="location",
                complexity="medium"
            ),
            TestQuery(
                "Explain the purpose of {class_name}",
                QueryCategory.UNDERSTANDING,
                expected_result_type="explanation",
                complexity="medium"
            ),
            TestQuery(
                "Show how {module_name} is initialized",
                QueryCategory.UNDERSTANDING,
                expected_result_type="explanation",
                complexity="medium"
            ),
            
            # Architecture understanding
            TestQuery(
                "Explain the architecture of {component_name}",
                QueryCategory.UNDERSTANDING,
                expected_result_type="explanation",
                complexity="complex"
            ),
            TestQuery(
                "Show data flow for {feature_name}",
                QueryCategory.UNDERSTANDING,
                expected_result_type="explanation",
                complexity="complex"
            ),
            TestQuery(
                "Find the main components of the system",
                QueryCategory.UNDERSTANDING,
                expected_result_type="list",
                complexity="complex"
            ),
            TestQuery(
                "Explain the plugin system",
                QueryCategory.UNDERSTANDING,
                expected_result_type="explanation",
                complexity="complex"
            ),
            TestQuery(
                "Show how errors are handled in {module_name}",
                QueryCategory.UNDERSTANDING,
                expected_result_type="explanation",
                complexity="medium"
            )
        ]
    
    def _initialize_language_mappings(self) -> Dict[str, Dict[str, str]]:
        """Initialize language-specific placeholder mappings"""
        return {
            "python": {
                "main_class": "BaseHandler",
                "main_function": "process_request",
                "config_variable": "CONFIG",
                "main_module": "core",
                "main_interface": "Protocol",
                "base_class": "BaseModel",
                "return_type": "Dict",
                "prefix": "DEFAULT_",
                "module_name": "utils",
                "special_symbol": "__special__",
                "overloaded_function": "process",
                "decorator_name": "cached_property",
                "component_name": "auth",
                "library_name": "requests",
                "language": "python",
                "directory": "src",
                "symbol_name": "Handler",
                "class_name": "RequestHandler",
                "method_name": "handle",
                "interface_name": "HandlerProtocol",
                "feature_name": "authentication",
                "process_name": "request_handling",
                "command_name": "serve"
            },
            "javascript": {
                "main_class": "Component",
                "main_function": "render",
                "config_variable": "config",
                "main_module": "app",
                "base_class": "BaseComponent",
                "return_type": "Promise",
                "prefix": "REACT_APP_",
                "module_name": "components",
                "special_symbol": "$element",
                "overloaded_function": "handle",
                "component_name": "Button",
                "library_name": "react",
                "language": "javascript",
                "directory": "components",
                "symbol_name": "App",
                "class_name": "AppComponent",
                "method_name": "onClick",
                "feature_name": "state_management",
                "process_name": "rendering",
                "command_name": "start"
            },
            "typescript": {
                "main_class": "Service",
                "main_function": "execute",
                "config_variable": "configuration",
                "main_module": "services",
                "main_interface": "IService",
                "base_class": "BaseService",
                "return_type": "Observable",
                "prefix": "I",
                "module_name": "core",
                "special_symbol": "Symbol.iterator",
                "overloaded_function": "process",
                "generic_class": "Container",
                "component_name": "UserService",
                "library_name": "rxjs",
                "language": "typescript",
                "directory": "src",
                "symbol_name": "Controller",
                "class_name": "ApiController",
                "method_name": "handleRequest",
                "interface_name": "IController",
                "feature_name": "dependency_injection",
                "process_name": "request_pipeline",
                "command_name": "build"
            },
            "go": {
                "main_class": "Server",
                "main_function": "HandleRequest",
                "config_variable": "Config",
                "main_module": "server",
                "main_interface": "Handler",
                "base_class": "BaseHandler",
                "return_type": "error",
                "prefix": "Default",
                "module_name": "pkg",
                "special_symbol": "init",
                "overloaded_function": "Handle",
                "component_name": "middleware",
                "library_name": "gin",
                "language": "go",
                "directory": "internal",
                "symbol_name": "Router",
                "class_name": "HTTPServer",
                "method_name": "ServeHTTP",
                "interface_name": "Handler",
                "feature_name": "routing",
                "process_name": "request_handling",
                "command_name": "serve"
            },
            "java": {
                "main_class": "Application",
                "main_function": "main",
                "config_variable": "configuration",
                "main_module": "app",
                "main_interface": "Service",
                "base_class": "AbstractService",
                "return_type": "CompletableFuture",
                "prefix": "DEFAULT_",
                "module_name": "service",
                "special_symbol": "@Component",
                "overloaded_function": "process",
                "generic_class": "Repository",
                "component_name": "UserService",
                "library_name": "spring",
                "language": "java",
                "directory": "src/main/java",
                "symbol_name": "Controller",
                "class_name": "RestController",
                "method_name": "handleRequest",
                "interface_name": "Service",
                "feature_name": "dependency_injection",
                "process_name": "request_processing",
                "command_name": "run"
            },
            "rust": {
                "main_class": "Server",
                "main_function": "run",
                "config_variable": "CONFIG",
                "main_module": "server",
                "main_trait": "Handler",
                "base_class": "BaseHandler",
                "return_type": "Result",
                "prefix": "DEFAULT_",
                "module_name": "handlers",
                "special_symbol": "r#type",
                "overloaded_function": "handle",
                "macro_name": "derive",
                "component_name": "router",
                "library_name": "tokio",
                "language": "rust",
                "directory": "src",
                "symbol_name": "App",
                "class_name": "Application",
                "method_name": "process",
                "interface_name": "Handler",
                "feature_name": "async_runtime",
                "process_name": "message_handling",
                "command_name": "serve"
            },
            "csharp": {
                "main_class": "Program",
                "main_function": "Main",
                "config_variable": "Configuration",
                "main_module": "Application",
                "main_interface": "IService",
                "main_namespace": "MyApp",
                "base_class": "ServiceBase",
                "return_type": "Task",
                "prefix": "Default",
                "module_name": "Services",
                "special_symbol": "nameof",
                "overloaded_function": "Process",
                "generic_class": "Repository",
                "component_name": "UserService",
                "library_name": "AspNetCore",
                "language": "csharp",
                "directory": "Services",
                "symbol_name": "Controller",
                "class_name": "ApiController",
                "method_name": "HandleAsync",
                "interface_name": "IService",
                "feature_name": "dependency_injection",
                "process_name": "request_pipeline",
                "command_name": "run"
            },
            "swift": {
                "main_class": "ViewController",
                "main_function": "viewDidLoad",
                "config_variable": "configuration",
                "main_module": "App",
                "main_protocol": "Delegate",
                "base_class": "UIViewController",
                "return_type": "Optional",
                "prefix": "k",
                "module_name": "Core",
                "special_symbol": "@objc",
                "overloaded_function": "handle",
                "component_name": "NetworkManager",
                "library_name": "Alamofire",
                "language": "swift",
                "directory": "Sources",
                "symbol_name": "Manager",
                "class_name": "DataManager",
                "method_name": "fetchData",
                "interface_name": "DataSource",
                "feature_name": "networking",
                "process_name": "data_fetching",
                "command_name": "run"
            },
            "ruby": {
                "main_class": "ApplicationController",
                "main_function": "index",
                "config_variable": "config",
                "main_module": "app",
                "base_class": "ActiveRecord::Base",
                "return_type": "Hash",
                "prefix": "DEFAULT_",
                "module_name": "helpers",
                "special_symbol": "@@class_var",
                "overloaded_function": "process",
                "component_name": "user",
                "library_name": "rails",
                "language": "ruby",
                "directory": "app",
                "symbol_name": "Model",
                "class_name": "User",
                "method_name": "save",
                "feature_name": "authentication",
                "process_name": "request_handling",
                "command_name": "server"
            },
            "c": {
                "main_class": "server",
                "main_function": "main",
                "config_variable": "config",
                "main_module": "server",
                "base_class": "base_handler",
                "return_type": "int",
                "prefix": "DEFAULT_",
                "module_name": "utils",
                "special_symbol": "__attribute__",
                "overloaded_function": "handle",
                "macro_name": "DEBUG",
                "component_name": "handler",
                "library_name": "pthread",
                "language": "c",
                "directory": "src",
                "symbol_name": "handler_t",
                "class_name": "request_handler",
                "method_name": "process_request",
                "feature_name": "memory_management",
                "process_name": "request_processing",
                "command_name": "server"
            },
            "cpp": {
                "main_class": "Application",
                "main_function": "run",
                "config_variable": "config",
                "main_module": "app",
                "main_namespace": "app",
                "base_class": "BaseApplication",
                "return_type": "std::optional",
                "prefix": "k",
                "module_name": "core",
                "special_symbol": "operator<<",
                "overloaded_function": "process",
                "generic_class": "Container",
                "macro_name": "ASSERT",
                "component_name": "Engine",
                "library_name": "boost",
                "language": "cpp",
                "directory": "src",
                "symbol_name": "Manager",
                "class_name": "ResourceManager",
                "method_name": "allocate",
                "interface_name": "IManager",
                "feature_name": "memory_management",
                "process_name": "resource_allocation",
                "command_name": "run"
            }
        }
    
    def get_queries_for_repository(self, repo_name: str, language: str, 
                                  query_counts: Dict[str, int]) -> List[Tuple[str, str]]:
        """Get queries customized for a specific repository"""
        # Get language-specific placeholders
        placeholders = self.language_mappings.get(language, self.language_mappings["python"])
        
        # Add repository-specific placeholders
        placeholders["repository"] = repo_name
        
        queries = []
        
        for category in QueryCategory:
            count = query_counts.get(category.value, 0)
            category_queries = self.queries.get(category, [])
            
            # Select queries for this category
            selected_queries = []
            
            # First, add non-language-specific queries
            for q in category_queries:
                if not q.language_specific:
                    selected_queries.append(q)
                    if len(selected_queries) >= count:
                        break
            
            # Then add language-specific queries if needed
            if len(selected_queries) < count:
                for q in category_queries:
                    if q.language_specific and (not q.languages or language in q.languages):
                        selected_queries.append(q)
                        if len(selected_queries) >= count:
                            break
            
            # Fill remaining slots with any queries
            if len(selected_queries) < count:
                for q in category_queries:
                    if q not in selected_queries:
                        selected_queries.append(q)
                        if len(selected_queries) >= count:
                            break
            
            # Format queries with placeholders
            for query in selected_queries[:count]:
                formatted_query = self._format_query(query.query, placeholders)
                queries.append((formatted_query, category.value))
        
        return queries
    
    def _format_query(self, query_template: str, placeholders: Dict[str, str]) -> str:
        """Format a query template with placeholders"""
        query = query_template
        for key, value in placeholders.items():
            query = query.replace(f"{{{key}}}", value)
        return query
    
    def save_test_suite(self, output_path: Path):
        """Save the test suite to a JSON file"""
        suite_data = {
            "categories": {
                cat.value: [
                    {
                        "query": q.query,
                        "language_specific": q.language_specific,
                        "languages": q.languages,
                        "expected_result_type": q.expected_result_type,
                        "complexity": q.complexity
                    }
                    for q in queries
                ]
                for cat, queries in self.queries.items()
            },
            "language_mappings": self.language_mappings,
            "total_queries": sum(len(queries) for queries in self.queries.values())
        }
        
        with open(output_path, 'w') as f:
            json.dump(suite_data, f, indent=2)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the test suite"""
        stats = {
            "total_queries": sum(len(queries) for queries in self.queries.values()),
            "by_category": {
                cat.value: len(queries) for cat, queries in self.queries.items()
            },
            "by_complexity": {
                "simple": 0,
                "medium": 0,
                "complex": 0
            },
            "language_specific": 0,
            "languages_covered": len(self.language_mappings)
        }
        
        for queries in self.queries.values():
            for q in queries:
                stats["by_complexity"][q.complexity] += 1
                if q.language_specific:
                    stats["language_specific"] += 1
        
        return stats


def main():
    """Generate and save the standardized test suite"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate standardized query test suite')
    parser.add_argument('--output', type=Path, 
                       default=Path('test_queries.json'),
                       help='Output file for test suite')
    parser.add_argument('--stats', action='store_true',
                       help='Show statistics about the test suite')
    
    args = parser.parse_args()
    
    # Create test suite
    suite = StandardizedQueryTestSuite()
    
    if args.stats:
        stats = suite.get_statistics()
        print("\n=== Test Suite Statistics ===")
        print(f"Total queries: {stats['total_queries']}")
        print("\nBy category:")
        for cat, count in stats['by_category'].items():
            print(f"  {cat}: {count}")
        print("\nBy complexity:")
        for complexity, count in stats['by_complexity'].items():
            print(f"  {complexity}: {count}")
        print(f"\nLanguage-specific queries: {stats['language_specific']}")
        print(f"Languages covered: {stats['languages_covered']}")
    
    # Save test suite
    suite.save_test_suite(args.output)
    print(f"\nTest suite saved to: {args.output}")
    
    # Example usage
    print("\n=== Example Usage ===")
    example_queries = suite.get_queries_for_repository(
        "django", "python", 
        {"symbol": 5, "content": 5, "navigation": 5, "refactoring": 3, "understanding": 2}
    )
    
    print(f"\nExample queries for Django (Python):")
    for i, (query, category) in enumerate(example_queries[:5], 1):
        print(f"{i}. [{category}] {query}")


if __name__ == '__main__':
    main()