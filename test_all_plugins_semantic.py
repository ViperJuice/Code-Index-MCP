#!/usr/bin/env python3
"""Test semantic search for ALL language plugins."""

import os
import sys
import tempfile
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Force semantic search
os.environ["SEMANTIC_SEARCH_ENABLED"] = "true"
os.environ["QDRANT_HOST"] = ":memory:"

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.storage.sqlite_store import SQLiteStore


def test_python_plugin():
    """Test Python plugin semantic search."""
    print("\n=== Testing Python Plugin ===")
    
    from mcp_server.plugins.python_plugin import Plugin
    
    store = SQLiteStore(":memory:")
    plugin = Plugin(sqlite_store=store)
    
    # Check if semantic is enabled
    print(f"Plugin type: {plugin.__class__.__name__}")
    print(f"Has semantic features: {hasattr(plugin, '_enable_semantic')}")
    if hasattr(plugin, '_enable_semantic'):
        print(f"Semantic enabled: {plugin._enable_semantic}")
    
    # Create test file
    test_code = '''
def calculate_prime(n):
    """Check if number is prime."""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

class MathUtils:
    """Utilities for mathematical operations."""
    
    def factorial(self, n):
        """Calculate factorial recursively."""
        if n <= 1:
            return 1
        return n * self.factorial(n - 1)
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_code)
        test_file = f.name
    
    try:
        # Index the file
        shard = plugin.indexFile(test_file, test_code)
        print(f"Indexed {len(shard['symbols'])} symbols")
        
        # Test semantic search
        queries = [
            "function to check if a number is prime",
            "recursive mathematical calculation",
            "class for math utilities"
        ]
        
        for query in queries:
            print(f"\nQuery: '{query}'")
            results = list(plugin.search(query, {"semantic": True, "limit": 2}))
            print(f"  Results: {len(results)}")
            for r in results:
                print(f"    - Line {r['line']}: {r['snippet'].strip()[:50]}...")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.unlink(test_file)


def test_javascript_plugin():
    """Test JavaScript plugin semantic search."""
    print("\n=== Testing JavaScript Plugin ===")
    
    try:
        from mcp_server.plugins.js_plugin import Plugin
        
        store = SQLiteStore(":memory:")
        plugin = Plugin(sqlite_store=store)
        
        print(f"Plugin type: {plugin.__class__.__name__}")
        print(f"Has semantic features: {hasattr(plugin, '_enable_semantic')}")
        if hasattr(plugin, '_enable_semantic'):
            print(f"Semantic enabled: {plugin._enable_semantic}")
        
        # Create test file
        test_code = '''
async function fetchUserData(userId) {
    /**
     * Fetch user data from API
     * @param {string} userId - The user ID
     * @returns {Promise<User>} User object
     */
    const response = await fetch(`/api/users/${userId}`);
    return response.json();
}

class DataProcessor {
    constructor() {
        this.cache = new Map();
    }
    
    processData(data) {
        // Transform and validate data
        return data.map(item => ({
            ...item,
            processed: true,
            timestamp: Date.now()
        }));
    }
}

const calculateSum = (numbers) => {
    return numbers.reduce((acc, num) => acc + num, 0);
};
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(test_code)
            test_file = f.name
        
        try:
            # Index the file
            shard = plugin.indexFile(test_file, test_code)
            print(f"Indexed {len(shard['symbols'])} symbols")
            
            # Test semantic search
            queries = [
                "async function to fetch data from API",
                "class for data transformation",
                "function to calculate sum of array"
            ]
            
            for query in queries:
                print(f"\nQuery: '{query}'")
                results = list(plugin.search(query, {"semantic": True, "limit": 2}))
                print(f"  Results: {len(results)}")
                for r in results:
                    print(f"    - Line {r['line']}: {r['snippet'].strip()[:50]}...")
            
            return True
        finally:
            os.unlink(test_file)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_c_plugin():
    """Test C plugin semantic search."""
    print("\n=== Testing C Plugin ===")
    
    try:
        from mcp_server.plugins.c_plugin import Plugin
        
        store = SQLiteStore(":memory:")
        plugin = Plugin(sqlite_store=store)
        
        print(f"Plugin type: {plugin.__class__.__name__}")
        print(f"Has semantic features: {hasattr(plugin, '_enable_semantic')}")
        if hasattr(plugin, '_enable_semantic'):
            print(f"Semantic enabled: {plugin._enable_semantic}")
        
        # Create test file
        test_code = '''
#include <stdio.h>
#include <stdlib.h>

// Structure to represent a linked list node
typedef struct Node {
    int data;
    struct Node* next;
} Node;

// Function to create a new node
Node* createNode(int data) {
    Node* newNode = (Node*)malloc(sizeof(Node));
    if (newNode == NULL) {
        return NULL;
    }
    newNode->data = data;
    newNode->next = NULL;
    return newNode;
}

// Function to insert at the beginning
void insertAtBeginning(Node** head, int data) {
    Node* newNode = createNode(data);
    newNode->next = *head;
    *head = newNode;
}

// Function to print the linked list
void printList(Node* head) {
    Node* current = head;
    while (current != NULL) {
        printf("%d -> ", current->data);
        current = current->next;
    }
    printf("NULL\\n");
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(test_code)
            test_file = f.name
        
        try:
            # Index the file
            shard = plugin.indexFile(test_file, test_code)
            print(f"Indexed {len(shard['symbols'])} symbols")
            
            # Test semantic search
            queries = [
                "function to create a new node for linked list",
                "data structure for linked list",
                "function to print list contents"
            ]
            
            for query in queries:
                print(f"\nQuery: '{query}'")
                results = list(plugin.search(query, {"semantic": True, "limit": 2}))
                print(f"  Results: {len(results)}")
                for r in results:
                    print(f"    - Line {r['line']}: {r['snippet'].strip()[:50]}...")
            
            return True
        finally:
            os.unlink(test_file)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cpp_plugin():
    """Test C++ plugin semantic search."""
    print("\n=== Testing C++ Plugin ===")
    
    try:
        from mcp_server.plugins.cpp_plugin import Plugin
        
        store = SQLiteStore(":memory:")
        plugin = Plugin(sqlite_store=store)
        
        print(f"Plugin type: {plugin.__class__.__name__}")
        print(f"Has semantic features: {hasattr(plugin, '_enable_semantic')}")
        if hasattr(plugin, '_enable_semantic'):
            print(f"Semantic enabled: {plugin._enable_semantic}")
        
        # Create test file
        test_code = '''
#include <iostream>
#include <vector>
#include <algorithm>

template<typename T>
class SortedContainer {
private:
    std::vector<T> data;
    
public:
    void insert(const T& value) {
        data.push_back(value);
        std::sort(data.begin(), data.end());
    }
    
    bool contains(const T& value) const {
        return std::binary_search(data.begin(), data.end(), value);
    }
    
    size_t size() const {
        return data.size();
    }
};

class Rectangle {
private:
    double width;
    double height;
    
public:
    Rectangle(double w, double h) : width(w), height(h) {}
    
    double area() const {
        return width * height;
    }
    
    double perimeter() const {
        return 2 * (width + height);
    }
};
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
            f.write(test_code)
            test_file = f.name
        
        try:
            # Index the file
            shard = plugin.indexFile(test_file, test_code)
            print(f"Indexed {len(shard['symbols'])} symbols")
            
            # Test semantic search
            queries = [
                "template class for sorted data container",
                "class to calculate rectangle area",
                "method to check if value exists in container"
            ]
            
            for query in queries:
                print(f"\nQuery: '{query}'")
                results = list(plugin.search(query, {"semantic": True, "limit": 2}))
                print(f"  Results: {len(results)}")
                for r in results:
                    print(f"    - Line {r['line']}: {r['snippet'].strip()[:50]}...")
            
            return True
        finally:
            os.unlink(test_file)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dart_plugin():
    """Test Dart plugin semantic search."""
    print("\n=== Testing Dart Plugin ===")
    
    try:
        from mcp_server.plugins.dart_plugin import Plugin
        
        store = SQLiteStore(":memory:")
        plugin = Plugin(sqlite_store=store)
        
        print(f"Plugin type: {plugin.__class__.__name__}")
        print(f"Has semantic features: {hasattr(plugin, '_enable_semantic')}")
        if hasattr(plugin, '_enable_semantic'):
            print(f"Semantic enabled: {plugin._enable_semantic}")
        
        # Create test file
        test_code = '''
import 'dart:async';

class UserService {
  final String baseUrl;
  
  UserService(this.baseUrl);
  
  Future<User> fetchUser(String userId) async {
    // Simulate API call
    await Future.delayed(Duration(seconds: 1));
    return User(id: userId, name: 'John Doe');
  }
  
  Stream<User> watchUser(String userId) {
    return Stream.periodic(Duration(seconds: 5), (i) {
      return User(id: userId, name: 'User $i');
    });
  }
}

class User {
  final String id;
  final String name;
  
  User({required this.id, required this.name});
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
    };
  }
}

void processNumbers(List<int> numbers) {
  final sum = numbers.reduce((a, b) => a + b);
  final average = sum / numbers.length;
  print('Sum: $sum, Average: $average');
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dart', delete=False) as f:
            f.write(test_code)
            test_file = f.name
        
        try:
            # Index the file
            shard = plugin.indexFile(test_file, test_code)
            print(f"Indexed {len(shard['symbols'])} symbols")
            
            # Test semantic search
            queries = [
                "async function to fetch user from API",
                "class to represent user data",
                "function to calculate sum and average"
            ]
            
            for query in queries:
                print(f"\nQuery: '{query}'")
                results = list(plugin.search(query, {"semantic": True, "limit": 2}))
                print(f"  Results: {len(results)}")
                for r in results:
                    print(f"    - Line {r['line']}: {r['snippet'].strip()[:50]}...")
            
            return True
        finally:
            os.unlink(test_file)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_html_css_plugin():
    """Test HTML/CSS plugin semantic search."""
    print("\n=== Testing HTML/CSS Plugin ===")
    
    try:
        from mcp_server.plugins.html_css_plugin import Plugin
        
        store = SQLiteStore(":memory:")
        plugin = Plugin(sqlite_store=store)
        
        print(f"Plugin type: {plugin.__class__.__name__}")
        print(f"Has semantic features: {hasattr(plugin, '_enable_semantic')}")
        if hasattr(plugin, '_enable_semantic'):
            print(f"Semantic enabled: {plugin._enable_semantic}")
        
        # Create test HTML file
        test_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Test Page</title>
</head>
<body>
    <header id="main-header" class="header-container">
        <h1 class="site-title">Welcome</h1>
        <nav class="main-nav">
            <ul>
                <li><a href="#home">Home</a></li>
                <li><a href="#about">About</a></li>
            </ul>
        </nav>
    </header>
    
    <main id="content" class="content-wrapper">
        <section class="hero-section">
            <h2>Hero Title</h2>
            <p>Hero description</p>
        </section>
    </main>
</body>
</html>
'''
        
        # Create test CSS file
        test_css = '''
/* Main header styles */
#main-header {
    background-color: #333;
    color: white;
    padding: 1rem;
}

.header-container {
    max-width: 1200px;
    margin: 0 auto;
}

.site-title {
    font-size: 2rem;
    margin: 0;
}

/* Navigation styles */
.main-nav ul {
    list-style: none;
    display: flex;
    gap: 1rem;
}

/* Content styles */
.content-wrapper {
    padding: 2rem;
}

.hero-section {
    background: linear-gradient(to right, #667eea, #764ba2);
    padding: 3rem;
    border-radius: 8px;
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(test_html)
            html_file = f.name
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.css', delete=False) as f:
            f.write(test_css)
            css_file = f.name
        
        try:
            # Index the files
            html_shard = plugin.indexFile(html_file, test_html)
            css_shard = plugin.indexFile(css_file, test_css)
            
            print(f"Indexed HTML: {len(html_shard['symbols'])} symbols")
            print(f"Indexed CSS: {len(css_shard['symbols'])} symbols")
            
            # Test semantic search
            queries = [
                "header navigation styles",
                "hero section with gradient background",
                "main content wrapper element"
            ]
            
            for query in queries:
                print(f"\nQuery: '{query}'")
                results = list(plugin.search(query, {"semantic": True, "limit": 2}))
                print(f"  Results: {len(results)}")
                for r in results:
                    print(f"    - Line {r['line']}: {r['snippet'].strip()[:50]}...")
            
            return True
        finally:
            os.unlink(html_file)
            os.unlink(css_file)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run tests for all language plugins."""
    print("=== Testing Semantic Search for ALL Language Plugins ===")
    print(f"SEMANTIC_SEARCH_ENABLED: {os.getenv('SEMANTIC_SEARCH_ENABLED')}")
    print(f"VOYAGE_API_KEY present: {'VOYAGE_API_KEY' in os.environ}")
    print(f"QDRANT_HOST: {os.getenv('QDRANT_HOST')}")
    
    results = {
        "Python": test_python_plugin(),
        "JavaScript": test_javascript_plugin(),
        "C": test_c_plugin(),
        "C++": test_cpp_plugin(),
        "Dart": test_dart_plugin(),
        "HTML/CSS": test_html_css_plugin()
    }
    
    print("\n=== Summary ===")
    for lang, success in results.items():
        status = "✓ Working" if success else "✗ Failed"
        print(f"{lang}: {status}")
    
    implemented = sum(1 for s in results.values() if s)
    print(f"\nSemantic search working for {implemented}/{len(results)} language plugins")
    
    if implemented == len(results):
        print("\n✅ SUCCESS: All language plugins support semantic search!")
    else:
        print("\n❌ FAILURE: Some plugins still need fixes")
        print("\nDebug tips:")
        print("- Check if plugin inherits from PluginWithSemanticSearch")
        print("- Verify _enable_semantic is set to True")
        print("- Ensure index_with_embeddings is called during indexFile")
        print("- Check SemanticIndexer initialization")


if __name__ == "__main__":
    main()