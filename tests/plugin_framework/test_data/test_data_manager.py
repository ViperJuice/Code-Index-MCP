"""
Test data manager for language plugin testing.

This module provides comprehensive test data generation and management
for testing language plugins across different scenarios and languages.
"""

import json
import random
import string
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .language_templates import LanguageTemplates


@dataclass
class SymbolTestCase:
    """Test case for symbol extraction accuracy testing."""
    name: str
    kind: str
    line: int
    signature: Optional[str] = None
    docstring: Optional[str] = None


@dataclass
class FileTestCase:
    """Test case containing file content and expected symbols."""
    file: str
    content: str
    expected_symbols: List[SymbolTestCase]
    target_symbols: List[str]
    description: str


class TestDataManager:
    """
    Manages test data for language plugin testing.
    
    Provides:
    - Sample code generation for different scenarios
    - Language-specific test cases
    - Performance test data generation
    - Accuracy validation data
    - Error case generation
    """
    
    def __init__(self, language: str):
        """Initialize test data manager for specific language."""
        self.language = language
        self.templates = LanguageTemplates(language)
        
        # Cache for generated content
        self._content_cache = {}
        
    # ===== Basic Test Data =====
    
    def get_simple_content(self) -> str:
        """Get simple, valid code content for basic testing."""
        cache_key = "simple_content"
        if cache_key not in self._content_cache:
            self._content_cache[cache_key] = self.templates.get_simple_template()
        return self._content_cache[cache_key]
    
    def get_basic_test_files(self) -> Dict[str, str]:
        """Get basic test files for fundamental functionality testing."""
        ext = self.templates.get_file_extension()
        
        return {
            f"basic{ext}": self.get_simple_content(),
            f"empty{ext}": "",
            f"minimal{ext}": self.templates.get_minimal_template(),
            f"comments{ext}": self.templates.get_comments_template()
        }
    
    # ===== Symbol-Specific Test Data =====
    
    def get_function_test_files(self) -> Dict[str, str]:
        """Get test files focused on function/method extraction."""
        ext = self.templates.get_file_extension()
        
        return {
            f"functions{ext}": self.templates.get_functions_template(),
            f"methods{ext}": self.templates.get_methods_template(),
            f"complex_functions{ext}": self.templates.get_complex_functions_template()
        }
    
    def get_class_test_files(self) -> Dict[str, str]:
        """Get test files focused on class/type extraction.""" 
        ext = self.templates.get_file_extension()
        
        return {
            f"classes{ext}": self.templates.get_classes_template(),
            f"inheritance{ext}": self.templates.get_inheritance_template(),
            f"nested_classes{ext}": self.templates.get_nested_classes_template()
        }
    
    def get_nested_test_files(self) -> Dict[str, str]:
        """Get test files with nested symbols."""
        ext = self.templates.get_file_extension()
        
        return {
            f"nested{ext}": self.templates.get_nested_template(),
            f"complex_nesting{ext}": self.templates.get_complex_nesting_template()
        }
    
    # ===== Accuracy Testing Data =====
    
    def get_accuracy_test_files(self) -> List[FileTestCase]:
        """Get test files with known expected symbols for accuracy testing."""
        ext = self.templates.get_file_extension()
        
        test_cases = []
        
        # Simple function test case
        simple_content = self.templates.get_simple_functions_for_accuracy()
        simple_symbols = self.templates.get_expected_simple_symbols()
        
        test_cases.append(FileTestCase(
            file=f"accuracy_simple{ext}",
            content=simple_content,
            expected_symbols=simple_symbols,
            target_symbols=[s.name for s in simple_symbols],
            description="Simple functions accuracy test"
        ))
        
        # Class test case
        class_content = self.templates.get_simple_classes_for_accuracy()
        class_symbols = self.templates.get_expected_class_symbols()
        
        test_cases.append(FileTestCase(
            file=f"accuracy_classes{ext}",
            content=class_content,
            expected_symbols=class_symbols,
            target_symbols=[s.name for s in class_symbols],
            description="Simple classes accuracy test"
        ))
        
        return test_cases
    
    def get_definition_test_files(self) -> List[Dict[str, Any]]:
        """Get test files for definition lookup testing."""
        ext = self.templates.get_file_extension()
        
        return [
            {
                "file": f"definitions{ext}",
                "content": self.templates.get_definition_template(),
                "target_symbols": self.templates.get_definition_target_symbols()
            }
        ]
    
    def get_reference_test_files(self) -> List[Dict[str, Any]]:
        """Get test files for reference finding testing."""
        ext = self.templates.get_file_extension()
        
        return [
            {
                "file": f"references{ext}",
                "content": self.templates.get_reference_template(),
                "target_symbols": self.templates.get_reference_target_symbols()
            }
        ]
    
    # ===== Search Testing Data =====
    
    def get_search_test_content(self) -> str:
        """Get content designed for search functionality testing."""
        return self.templates.get_search_template()
    
    # ===== Error Case Data =====
    
    def get_invalid_syntax_files(self) -> Dict[str, str]:
        """Get files with invalid syntax for error handling testing."""
        ext = self.templates.get_file_extension()
        
        return {
            f"syntax_error_1{ext}": self.templates.get_syntax_error_template_1(),
            f"syntax_error_2{ext}": self.templates.get_syntax_error_template_2(),
            f"incomplete{ext}": self.templates.get_incomplete_template()
        }
    
    def get_unicode_test_files(self) -> Dict[str, str]:
        """Get files with Unicode content for encoding testing."""
        ext = self.templates.get_file_extension()
        
        return {
            f"unicode{ext}": self.templates.get_unicode_template(),
            f"emoji{ext}": self.templates.get_emoji_template(),
            f"multilingual{ext}": self.templates.get_multilingual_template()
        }
    
    # ===== Performance Testing Data =====
    
    def generate_small_file(self, symbol_count: int = 5) -> str:
        """Generate small file with specified number of symbols."""
        return self.templates.generate_file_with_symbols(symbol_count, "small")
    
    def generate_medium_file(self, symbol_count: int = 50) -> str:
        """Generate medium file with specified number of symbols."""
        return self.templates.generate_file_with_symbols(symbol_count, "medium")
    
    def generate_large_file(self, symbol_count: int = 500) -> str:
        """Generate large file with specified number of symbols."""
        return self.templates.generate_file_with_symbols(symbol_count, "large")
    
    def generate_massive_file(self, symbol_count: int = 5000) -> str:
        """Generate massive file for stress testing."""
        return self.templates.generate_file_with_symbols(symbol_count, "massive")
    
    # ===== Code Complexity Variations =====
    
    def get_complex_patterns(self) -> Dict[str, str]:
        """Get files with complex language patterns."""
        ext = self.templates.get_file_extension()
        
        return {
            f"generics{ext}": self.templates.get_generics_template(),
            f"annotations{ext}": self.templates.get_annotations_template(),
            f"metaprogramming{ext}": self.templates.get_metaprogramming_template(),
            f"async{ext}": self.templates.get_async_template()
        }
    
    def get_edge_cases(self) -> Dict[str, str]:
        """Get files with edge case patterns."""
        ext = self.templates.get_file_extension()
        
        return {
            f"edge_symbols{ext}": self.templates.get_edge_symbols_template(),
            f"special_chars{ext}": self.templates.get_special_chars_template(),
            f"long_lines{ext}": self.templates.get_long_lines_template()
        }
    
    # ===== Benchmark Data Generation =====
    
    def generate_benchmark_suite(self, sizes: List[int] = None) -> Dict[str, str]:
        """Generate a suite of files for benchmarking."""
        if sizes is None:
            sizes = [10, 25, 50, 100, 200, 500, 1000]
        
        ext = self.templates.get_file_extension()
        suite = {}
        
        for size in sizes:
            content = self.generate_medium_file(size)
            suite[f"benchmark_{size}{ext}"] = content
        
        return suite
    
    def generate_stress_test_files(self, count: int = 100) -> List[Tuple[str, str]]:
        """Generate many files for stress testing."""
        ext = self.templates.get_file_extension()
        files = []
        
        for i in range(count):
            # Vary file size randomly
            symbol_count = random.randint(5, 100)
            content = self.generate_medium_file(symbol_count)
            filename = f"stress_test_{i:03d}{ext}"
            files.append((filename, content))
        
        return files
    
    # ===== Cross-Language Data =====
    
    def get_multi_language_project(self) -> Dict[str, str]:
        """Get files for multi-language project testing."""
        # This would include files from multiple languages
        # For now, focus on our target language
        files = self.get_basic_test_files()
        files.update(self.get_function_test_files())
        return files
    
    # ===== Real-World Patterns =====
    
    def get_real_world_patterns(self) -> Dict[str, str]:
        """Get files with real-world code patterns."""
        ext = self.templates.get_file_extension()
        
        return {
            f"api_client{ext}": self.templates.get_api_client_template(),
            f"data_model{ext}": self.templates.get_data_model_template(),
            f"utility_functions{ext}": self.templates.get_utility_functions_template(),
            f"test_file{ext}": self.templates.get_test_file_template()
        }
    
    def get_framework_patterns(self) -> Dict[str, str]:
        """Get files using common framework patterns."""
        ext = self.templates.get_file_extension()
        
        return {
            f"framework_controller{ext}": self.templates.get_framework_controller_template(),
            f"framework_model{ext}": self.templates.get_framework_model_template(),
            f"framework_service{ext}": self.templates.get_framework_service_template()
        }
    
    # ===== Validation and Utilities =====
    
    def validate_test_data(self) -> Dict[str, bool]:
        """Validate that test data is properly formatted."""
        validation_results = {}
        
        # Test basic templates
        try:
            simple = self.get_simple_content()
            validation_results["simple_content"] = len(simple) > 0
        except Exception:
            validation_results["simple_content"] = False
        
        # Test generation functions
        try:
            small = self.generate_small_file(5)
            validation_results["small_file_generation"] = len(small) > 0
        except Exception:
            validation_results["small_file_generation"] = False
        
        # Test accuracy data
        try:
            accuracy_files = self.get_accuracy_test_files()
            validation_results["accuracy_test_files"] = len(accuracy_files) > 0
        except Exception:
            validation_results["accuracy_test_files"] = False
        
        return validation_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about available test data."""
        stats = {
            "language": self.language,
            "basic_files": len(self.get_basic_test_files()),
            "function_files": len(self.get_function_test_files()),
            "class_files": len(self.get_class_test_files()),
            "accuracy_cases": len(self.get_accuracy_test_files()),
            "error_cases": len(self.get_invalid_syntax_files()),
            "unicode_cases": len(self.get_unicode_test_files()),
            "complex_patterns": len(self.get_complex_patterns()),
            "edge_cases": len(self.get_edge_cases())
        }
        
        return stats
    
    # ===== Export and Import =====
    
    def export_test_data(self, output_dir: Path):
        """Export all test data to files for external use."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export basic files
        basic_files = self.get_basic_test_files()
        for filename, content in basic_files.items():
            (output_dir / filename).write_text(content)
        
        # Export accuracy test cases as JSON
        accuracy_cases = self.get_accuracy_test_files()
        accuracy_data = []
        
        for case in accuracy_cases:
            case_data = {
                "file": case.file,
                "content": case.content,
                "expected_symbols": [
                    {
                        "name": s.name,
                        "kind": s.kind,
                        "line": s.line,
                        "signature": s.signature,
                        "docstring": s.docstring
                    }
                    for s in case.expected_symbols
                ],
                "target_symbols": case.target_symbols,
                "description": case.description
            }
            accuracy_data.append(case_data)
        
        (output_dir / "accuracy_test_cases.json").write_text(
            json.dumps(accuracy_data, indent=2)
        )
        
        # Export metadata
        metadata = {
            "language": self.language,
            "generated_at": str(Path.cwd()),
            "statistics": self.get_statistics(),
            "validation": self.validate_test_data()
        }
        
        (output_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2)
        )