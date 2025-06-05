#!/usr/bin/env python3
"""Basic Tree-sitter parsing test."""

def test_basic_tree_sitter():
    """Test basic Tree-sitter functionality with tree-sitter-languages."""
    print("Testing basic Tree-sitter functionality...")
    
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_languages as tsl
        
        # Test Python parsing - tree-sitter-languages returns Language objects directly
        python_lang = tsl.get_language('python')
        parser = Parser()
        parser.set_language(python_lang)
        
        # Parse a simple Python function
        source_code = b'''
def hello_world(name):
    print(f"Hello, {name}!")
    return True
'''
        
        tree = parser.parse(source_code)
        root_node = tree.root_node
        
        print(f"✓ Successfully parsed Python code")
        print(f"  Root node type: {root_node.type}")
        print(f"  Number of children: {root_node.child_count}")
        
        # Print first few children
        for i, child in enumerate(root_node.children):
            if i < 3:  # Only first 3
                print(f"  Child {i}: {child.type}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_languages():
    """Test multiple language parsers."""
    print("\nTesting multiple language parsers...")
    
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_languages as tsl
        
        test_cases = [
            ('python', b'def test(): pass'),
            ('javascript', b'function test() { return true; }'),
            ('rust', b'fn test() -> bool { true }'),
            ('go', b'func test() bool { return true }'),
        ]
        
        success_count = 0
        for lang_name, code in test_cases:
            try:
                language = tsl.get_language(lang_name)
                parser = Parser()
                parser.set_language(language)
                
                tree = parser.parse(code)
                root_node = tree.root_node
                
                print(f"✓ {lang_name}: parsed successfully ({root_node.type})")
                success_count += 1
            except Exception as e:
                print(f"✗ {lang_name}: failed ({e})")
        
        print(f"\nSuccessfully parsed {success_count}/{len(test_cases)} languages")
        return success_count > 0
        
    except Exception as e:
        print(f"✗ Failed to test multiple languages: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Basic Tree-sitter Parsing Test")
    print("=" * 50)
    
    tests = [test_basic_tree_sitter, test_multiple_languages]
    passed = sum(1 for test in tests if test())
    
    print(f"\nResults: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 Basic Tree-sitter parsing is working!")
    else:
        print("⚠ Some basic parsing tests failed.")