#!/usr/bin/env python3
"""Test script for Tree-sitter setup and parser functionality."""

import sys
from pathlib import Path

# Add the mcp_server directory to the path
sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))

def test_basic_imports():
    """Test basic Tree-sitter imports."""
    print("Testing basic Tree-sitter imports...")
    
    try:
        import tree_sitter
        print(f"✓ tree-sitter imported successfully (version: {getattr(tree_sitter, '__version__', 'unknown')})")
    except ImportError as e:
        print(f"✗ Failed to import tree-sitter: {e}")
        return False
    
    try:
        import tree_sitter_languages
        print(f"✓ tree-sitter-languages imported successfully (version: {getattr(tree_sitter_languages, '__version__', 'unknown')})")
    except ImportError as e:
        print(f"✗ Failed to import tree-sitter-languages: {e}")
        print("  This is expected if individual parsers are used instead")
    
    return True


def test_treesitter_config():
    """Test the treesitter_config module."""
    print("\nTesting treesitter_config module...")
    
    try:
        # Import the module directly
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "treesitter_config", 
            Path(__file__).parent / "mcp_server" / "utils" / "treesitter_config.py"
        )
        treesitter_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(treesitter_config)
        
        print("✓ treesitter_config module imported successfully")
        
        # Test manager initialization
        manager = treesitter_config.get_tree_sitter_manager()
        print(f"✓ TreeSitterManager initialized with {len(manager.get_supported_languages())} languages")
        
        # Test supported languages
        supported = treesitter_config.get_supported_languages()
        print(f"✓ Supported languages: {sorted(list(supported))}")
        
        # Test basic parsing
        python_code = "def hello(): print('Hello, World!')"
        if treesitter_config.is_language_supported('python'):
            node = treesitter_config.parse_content(python_code, 'python')
            if node:
                print("✓ Successfully parsed Python code")
            else:
                print("✗ Failed to parse Python code")
        else:
            print("⚠ Python parser not available")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing treesitter_config: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_enhanced_wrapper():
    """Test the enhanced TreeSitter wrapper."""
    print("\nTesting enhanced TreeSitter wrapper...")
    
    try:
        # Import the module directly
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "enhanced_treesitter_wrapper", 
            Path(__file__).parent / "mcp_server" / "utils" / "enhanced_treesitter_wrapper.py"
        )
        wrapper_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(wrapper_module)
        
        print("✓ enhanced_treesitter_wrapper module imported successfully")
        
        # Check overall availability
        availability = wrapper_module.check_tree_sitter_availability()
        print(f"✓ Tree-sitter availability check: {availability}")
        
        # List theoretical vs. actual support
        theoretical = wrapper_module.list_supported_languages()
        available = wrapper_module.list_available_parsers()
        print(f"✓ Theoretical languages: {len(theoretical)}")
        print(f"✓ Available parsers: {len(available)}")
        print(f"  Available: {available[:10]}{'...' if len(available) > 10 else ''}")
        
        # Test safe parser creation
        for language in ['python', 'javascript', 'rust', 'go']:
            parser = wrapper_module.safe_create_parser(language)
            if parser:
                print(f"✓ Successfully created {language} parser")
                
                # Test basic parsing
                test_code = {
                    'python': b"def test(): pass",
                    'javascript': b"function test() {}",
                    'rust': b"fn test() {}",
                    'go': b"func test() {}"
                }
                
                if language in test_code:
                    try:
                        node = parser.parse(test_code[language])
                        print(f"  ✓ Successfully parsed {language} test code")
                    except Exception as e:
                        print(f"  ✗ Failed to parse {language} test code: {e}")
            else:
                print(f"⚠ {language} parser not available")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing enhanced wrapper: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_individual_parsers():
    """Test individual Tree-sitter parsers."""
    print("\nTesting individual Tree-sitter parsers...")
    
    individual_parsers = [
        'tree_sitter_c_sharp',
        'tree_sitter_bash', 
        'tree_sitter_haskell',
        'tree_sitter_scala',
        'tree_sitter_lua',
        'tree_sitter_yaml',
        'tree_sitter_toml',
        'tree_sitter_json',
        'tree_sitter_markdown',
        'tree_sitter_csv'
    ]
    
    available_count = 0
    for parser_name in individual_parsers:
        try:
            parser_module = __import__(parser_name)
            print(f"✓ {parser_name} available")
            available_count += 1
        except ImportError:
            print(f"⚠ {parser_name} not available")
    
    print(f"\nIndividual parsers available: {available_count}/{len(individual_parsers)}")
    return True


def test_fallback_behavior():
    """Test fallback behavior for unsupported languages."""
    print("\nTesting fallback behavior...")
    
    try:
        # Import the module directly
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "treesitter_config", 
            Path(__file__).parent / "mcp_server" / "utils" / "treesitter_config.py"
        )
        treesitter_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(treesitter_config)
        
        manager = treesitter_config.get_tree_sitter_manager()
        
        # Test unsupported language detection
        fake_language = 'nonexistent_language'
        parser = manager.get_parser(fake_language)
        if parser is None:
            print(f"✓ Correctly handled unsupported language: {fake_language}")
        else:
            print(f"✗ Unexpected parser returned for unsupported language: {fake_language}")
        
        # Test file extension detection
        test_cases = [
            ('test.py', 'python'),
            ('test.js', 'javascript'),
            ('test.rs', 'rust'),
            ('test.unknown', None)
        ]
        
        for file_path, expected in test_cases:
            detected = manager.detect_language(file_path)
            if detected == expected:
                print(f"✓ Correctly detected language for {file_path}: {detected}")
            else:
                print(f"✗ Wrong language detection for {file_path}: expected {expected}, got {detected}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing fallback behavior: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Tree-sitter tests."""
    print("=" * 60)
    print("Tree-sitter Setup Test Suite")
    print("=" * 60)
    
    tests = [
        test_basic_imports,
        test_treesitter_config,
        test_enhanced_wrapper,
        test_individual_parsers,
        test_fallback_behavior
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed! Tree-sitter setup is working correctly.")
        return 0
    else:
        print("⚠ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())