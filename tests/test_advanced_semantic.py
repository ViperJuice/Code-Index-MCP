#!/usr/bin/env python3
"""Advanced semantic retrieval demonstration with real-world queries."""

import os
import sys
import numpy as np
from pathlib import Path
import logging
from typing import List, Dict, Any, Tuple
import json

sys.path.insert(0, str(Path(__file__).parent))

# Import our plugins to get real code
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.plugins.js_plugin.plugin import Plugin as JSPlugin
from mcp_server.plugins.jvm_plugin.plugin import Plugin as JVMPlugin
from mcp_server.plugins.go_plugin.plugin import Plugin as GoPlugin

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class AdvancedSemanticRetriever:
    """Advanced semantic retrieval with conceptual understanding."""
    
    def __init__(self):
        self.code_database = []
        self.concept_embeddings = self._initialize_concepts()
    
    def _initialize_concepts(self) -> Dict[str, np.ndarray]:
        """Initialize concept embeddings for better semantic understanding."""
        # Define key programming concepts and their relationships
        concepts = {
            # Core concepts
            'function': np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            'class': np.array([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            'variable': np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            
            # Patterns
            'api': np.array([0.7, 0.0, 0.0, 0.8, 0.5, 0.0, 0.0, 0.3]),
            'database': np.array([0.3, 0.4, 0.2, 0.0, 0.0, 0.9, 0.0, 0.0]),
            'auth': np.array([0.5, 0.3, 0.0, 0.6, 0.8, 0.0, 0.0, 0.7]),
            'validation': np.array([0.6, 0.2, 0.3, 0.0, 0.0, 0.0, 0.9, 0.4]),
            'error': np.array([0.4, 0.2, 0.0, 0.0, 0.0, 0.0, 0.7, 0.8]),
            
            # Actions
            'create': np.array([0.8, 0.5, 0.6, 0.3, 0.0, 0.7, 0.0, 0.0]),
            'read': np.array([0.7, 0.0, 0.4, 0.5, 0.0, 0.8, 0.0, 0.0]),
            'update': np.array([0.7, 0.0, 0.5, 0.3, 0.0, 0.8, 0.0, 0.0]),
            'delete': np.array([0.6, 0.0, 0.3, 0.2, 0.0, 0.7, 0.0, 0.3]),
            
            # Web concepts
            'request': np.array([0.5, 0.0, 0.2, 0.9, 0.3, 0.0, 0.0, 0.0]),
            'response': np.array([0.5, 0.0, 0.2, 0.9, 0.0, 0.0, 0.0, 0.3]),
            'route': np.array([0.8, 0.0, 0.0, 0.9, 0.7, 0.0, 0.0, 0.0]),
            'middleware': np.array([0.7, 0.3, 0.0, 0.8, 0.6, 0.0, 0.3, 0.0]),
        }
        
        # Normalize all concept vectors
        for key in concepts:
            concepts[key] = concepts[key] / (np.linalg.norm(concepts[key]) + 1e-10)
        
        return concepts
    
    def _compute_embedding(self, text: str, metadata: Dict[str, Any]) -> np.ndarray:
        """Compute semantic embedding for code."""
        # Start with zero vector
        embedding = np.zeros(8)
        
        text_lower = text.lower()
        
        # Add concept contributions
        for concept, concept_vec in self.concept_embeddings.items():
            if concept in text_lower:
                # Weight by frequency
                frequency = text_lower.count(concept) / len(text_lower.split())
                embedding += concept_vec * min(frequency * 10, 1.0)
        
        # Add language-specific weights
        lang_weights = {
            'python': np.array([0.2, 0.3, 0.1, 0.0, 0.0, 0.0, 0.2, 0.2]),
            'javascript': np.array([0.3, 0.1, 0.2, 0.3, 0.0, 0.0, 0.1, 0.0]),
            'java': np.array([0.1, 0.4, 0.1, 0.1, 0.0, 0.0, 0.2, 0.1]),
            'go': np.array([0.3, 0.0, 0.1, 0.2, 0.0, 0.2, 0.1, 0.1])
        }
        
        if metadata.get('language') in lang_weights:
            embedding += lang_weights[metadata['language']] * 0.3
        
        # Add symbol type weights
        symbol_weights = {
            'function': np.array([0.8, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.1]),
            'class': np.array([0.0, 0.9, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0]),
            'method': np.array([0.7, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1]),
            'route': np.array([0.5, 0.0, 0.0, 0.8, 0.4, 0.0, 0.0, 0.0])
        }
        
        kind = metadata.get('kind', '').lower()
        if kind in symbol_weights:
            embedding += symbol_weights[kind] * 0.4
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def index_repositories(self):
        """Index real code from test repositories."""
        logger.info("Indexing real code from repositories...\n")
        
        # Initialize plugins
        plugins = {
            "python": PythonPlugin(None),
            "javascript": JSPlugin(None),
            "java": JVMPlugin(None),
            "go": GoPlugin(None),
        }
        
        # Selected files that demonstrate different patterns
        test_files = [
            ("test_repos/flask-app/app/__init__.py", "python"),
            ("test_repos/express-api/src/index.js", "javascript"),
            ("test_repos/spring-boot/complete/src/main/java/com/example/springboot/HelloController.java", "java"),
            ("test_repos/go-examples/hello/hello.go", "go"),
            ("test_repos/flask-app/app/models.py", "python"),
            ("test_repos/express-api/src/api/index.js", "javascript"),
        ]
        
        total_indexed = 0
        
        for file_path, lang in test_files:
            path = Path(file_path)
            if not path.exists():
                continue
            
            plugin = plugins.get(lang)
            if not plugin:
                continue
            
            try:
                content = path.read_text(encoding='utf-8')
                result = plugin.indexFile(str(path), content)
                
                if result and "symbols" in result:
                    for symbol in result["symbols"]:
                        # Extract context
                        lines = content.split('\n')
                        line_num = symbol['line'] - 1
                        context_start = max(0, line_num - 2)
                        context_end = min(len(lines), line_num + 3)
                        context = '\n'.join(lines[context_start:context_end])
                        
                        # Create searchable text
                        searchable_text = f"{symbol['symbol']} {symbol.get('kind', '')} {context}"
                        
                        # Compute embedding
                        metadata = {
                            'language': lang,
                            'kind': symbol.get('kind', 'unknown')
                        }
                        embedding = self._compute_embedding(searchable_text, metadata)
                        
                        # Store in database
                        self.code_database.append({
                            'file': str(path),
                            'symbol': symbol['symbol'],
                            'kind': symbol.get('kind', 'unknown'),
                            'line': symbol['line'],
                            'language': lang,
                            'context': context,
                            'embedding': embedding
                        })
                        total_indexed += 1
                        
            except Exception as e:
                logger.error(f"Error indexing {path}: {e}")
        
        logger.info(f"✓ Indexed {total_indexed} code elements\n")
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """Semantic search for code."""
        # Compute query embedding
        query_embedding = self._compute_embedding(query, {'language': 'query'})
        
        # Add query intent understanding
        query_lower = query.lower()
        
        # Boost certain concepts based on query patterns
        if any(word in query_lower for word in ['create', 'new', 'add', 'insert']):
            query_embedding += self.concept_embeddings['create'] * 0.3
        if any(word in query_lower for word in ['validate', 'check', 'verify']):
            query_embedding += self.concept_embeddings['validation'] * 0.3
        if any(word in query_lower for word in ['api', 'endpoint', 'route']):
            query_embedding += self.concept_embeddings['api'] * 0.3
        if any(word in query_lower for word in ['auth', 'login', 'user']):
            query_embedding += self.concept_embeddings['auth'] * 0.3
        if any(word in query_lower for word in ['error', 'exception', 'handle']):
            query_embedding += self.concept_embeddings['error'] * 0.3
        
        # Re-normalize
        query_embedding = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
        
        # Calculate similarities
        results = []
        for item in self.code_database:
            similarity = np.dot(query_embedding, item['embedding'])
            
            # Apply contextual boosts
            if 'http' in query_lower and item['kind'] in ['route', 'function', 'method']:
                if any(word in item['context'].lower() for word in ['request', 'response', 'router']):
                    similarity *= 1.2
            
            if 'database' in query_lower and any(word in item['context'].lower() for word in ['query', 'db', 'sql']):
                similarity *= 1.2
            
            results.append((item, similarity))
        
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

def demonstrate_advanced_semantic_search():
    """Demonstrate advanced semantic search capabilities."""
    logger.info("="*70)
    logger.info("ADVANCED SEMANTIC CODE SEARCH DEMONSTRATION")
    logger.info("="*70)
    
    retriever = AdvancedSemanticRetriever()
    retriever.index_repositories()
    
    # Natural language queries that require understanding
    queries = [
        {
            "query": "How do I handle user authentication?",
            "intent": "Find authentication-related code"
        },
        {
            "query": "Show me API endpoints that return data",
            "intent": "Find REST API route handlers"
        },
        {
            "query": "Where is error handling implemented?",
            "intent": "Find error handling patterns"
        },
        {
            "query": "Functions that validate or check input",
            "intent": "Find validation logic"
        },
        {
            "query": "Database models and schema definitions",
            "intent": "Find data model definitions"
        },
        {
            "query": "Entry point or main function of the application",
            "intent": "Find main/startup code"
        }
    ]
    
    for query_info in queries:
        query = query_info["query"]
        intent = query_info["intent"]
        
        logger.info(f"\n{'='*70}")
        logger.info(f"Query: \"{query}\"")
        logger.info(f"Intent: {intent}")
        logger.info("-"*70)
        
        results = retriever.search(query, top_k=4)
        
        if results:
            for i, (item, score) in enumerate(results, 1):
                logger.info(f"\n[{i}] Relevance Score: {score:.3f}")
                logger.info(f"    Symbol: {item['symbol']} ({item['kind']})")
                logger.info(f"    Language: {item['language']}")
                logger.info(f"    File: {Path(item['file']).name}:{item['line']}")
                logger.info(f"    Context Preview:")
                
                # Show context with highlighting
                context_lines = item['context'].split('\n')
                for line in context_lines[:3]:
                    if line.strip():
                        logger.info(f"      {line[:80]}...")
        else:
            logger.info("No relevant results found")
    
    # Show concept space visualization
    logger.info(f"\n{'='*70}")
    logger.info("SEMANTIC UNDERSTANDING DEMONSTRATION")
    logger.info("="*70)
    
    logger.info("\nQuery Concept Analysis:")
    test_query = "create a new user with validation"
    logger.info(f"Query: \"{test_query}\"")
    
    # Show which concepts are activated
    query_vec = retriever._compute_embedding(test_query, {'language': 'query'})
    concepts_activated = []
    
    for concept, vec in retriever.concept_embeddings.items():
        activation = np.dot(query_vec, vec)
        if activation > 0.1:
            concepts_activated.append((concept, activation))
    
    concepts_activated.sort(key=lambda x: x[1], reverse=True)
    logger.info("\nActivated Concepts:")
    for concept, activation in concepts_activated:
        bar = "█" * int(activation * 20)
        logger.info(f"  {concept:12} {bar} {activation:.2f}")

if __name__ == "__main__":
    demonstrate_advanced_semantic_search()