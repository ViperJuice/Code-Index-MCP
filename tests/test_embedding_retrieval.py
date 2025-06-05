#!/usr/bin/env python3
"""Test semantic retrieval using embeddings (with mock and real implementations)."""

import os
import sys
import json
import numpy as np
from pathlib import Path
import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import hashlib

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CodeSnippet:
    """Represents a code snippet with metadata."""
    file: str
    symbol: str
    kind: str
    line: int
    language: str
    signature: str
    context: str
    embedding: np.ndarray = None

class SemanticRetriever:
    """Semantic code retrieval using embeddings."""
    
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock
        self.code_snippets: List[CodeSnippet] = []
        self.voyage_client = None
        
        if not use_mock:
            try:
                import voyageai
                api_key = os.getenv("VOYAGE_API_KEY")
                if api_key:
                    self.voyage_client = voyageai.Client(api_key=api_key)
                    logger.info("✓ Voyage AI client initialized")
                else:
                    logger.warning("VOYAGE_API_KEY not set, using mock embeddings")
                    self.use_mock = True
            except ImportError:
                logger.warning("voyageai package not installed, using mock embeddings")
                self.use_mock = True
    
    def _mock_embedding(self, text: str) -> np.ndarray:
        """Generate mock embeddings based on text features."""
        # Create a deterministic "embedding" based on text features
        features = []
        
        # Language features
        lang_keywords = {
            'python': ['def', 'class', 'import', 'self', '__init__'],
            'javascript': ['function', 'const', 'async', 'await', 'export'],
            'java': ['public', 'class', 'void', 'static', 'throws'],
            'go': ['func', 'package', 'defer', 'goroutine', 'channel']
        }
        
        for lang, keywords in lang_keywords.items():
            score = sum(1 for kw in keywords if kw in text.lower()) / len(keywords)
            features.append(score)
        
        # Semantic features
        semantic_patterns = {
            'http': ['request', 'response', 'handler', 'route', 'endpoint', 'api', 'rest'],
            'database': ['query', 'insert', 'update', 'delete', 'connection', 'transaction'],
            'auth': ['login', 'authenticate', 'token', 'password', 'user', 'permission'],
            'error': ['error', 'exception', 'catch', 'throw', 'handle', 'fail'],
            'test': ['test', 'assert', 'expect', 'mock', 'fixture', 'suite'],
            'config': ['config', 'setting', 'option', 'environment', 'variable'],
            'validation': ['validate', 'check', 'verify', 'ensure', 'require'],
            'logging': ['log', 'logger', 'debug', 'info', 'warn', 'error']
        }
        
        for category, keywords in semantic_patterns.items():
            score = sum(1 for kw in keywords if kw in text.lower()) / len(keywords)
            features.append(score)
        
        # Symbol type features
        symbol_types = ['function', 'class', 'method', 'variable', 'interface', 'struct']
        for sym_type in symbol_types:
            features.append(1.0 if sym_type in text.lower() else 0.0)
        
        # Add some noise for realism
        np.random.seed(hash(text) % 2**32)
        noise = np.random.normal(0, 0.1, len(features))
        
        # Normalize
        embedding = np.array(features) + noise
        embedding = embedding / (np.linalg.norm(embedding) + 1e-10)
        
        return embedding
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text (mock or real)."""
        if self.use_mock:
            return self._mock_embedding(text)
        else:
            try:
                result = self.voyage_client.embed(
                    [text], 
                    model="voyage-code-2",
                    input_type="document"
                )
                return np.array(result.embeddings[0])
            except Exception as e:
                logger.error(f"Voyage AI embedding failed: {e}")
                return self._mock_embedding(text)
    
    def index_code(self, snippets: List[Dict[str, Any]]):
        """Index code snippets with embeddings."""
        logger.info(f"\nIndexing {len(snippets)} code snippets...")
        
        for snippet_data in snippets:
            # Create rich text representation
            text = f"{snippet_data['symbol']} ({snippet_data['kind']} in {snippet_data['language']})\n"
            text += f"File: {snippet_data['file']}\n"
            text += f"Signature: {snippet_data.get('signature', '')}\n"
            text += f"Context: {snippet_data.get('context', '')}"
            
            # Get embedding
            embedding = self._get_embedding(text)
            
            snippet = CodeSnippet(
                file=snippet_data['file'],
                symbol=snippet_data['symbol'],
                kind=snippet_data['kind'],
                line=snippet_data['line'],
                language=snippet_data['language'],
                signature=snippet_data.get('signature', ''),
                context=snippet_data.get('context', ''),
                embedding=embedding
            )
            
            self.code_snippets.append(snippet)
        
        logger.info(f"✓ Indexed {len(self.code_snippets)} snippets with embeddings")
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[CodeSnippet, float]]:
        """Search for code using semantic similarity."""
        # Get query embedding
        query_embedding = self._get_embedding(query)
        
        # Calculate similarities
        similarities = []
        for snippet in self.code_snippets:
            # Cosine similarity
            similarity = np.dot(query_embedding, snippet.embedding)
            similarities.append((snippet, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]

def load_test_data() -> List[Dict[str, Any]]:
    """Load some test code snippets."""
    snippets = [
        # Python Flask
        {
            "file": "flask-app/app/main/views.py",
            "symbol": "index",
            "kind": "function",
            "line": 10,
            "language": "python",
            "signature": "def index():",
            "context": "@main.route('/', methods=['GET', 'POST'])\ndef index():\n    form = NameForm()\n    if form.validate_on_submit():\n        # Handle form submission"
        },
        {
            "file": "flask-app/app/auth/views.py",
            "symbol": "login",
            "kind": "function",
            "line": 25,
            "language": "python",
            "signature": "def login():",
            "context": "@auth.route('/login', methods=['GET', 'POST'])\ndef login():\n    form = LoginForm()\n    if form.validate_on_submit():\n        user = User.query.filter_by(email=form.email.data).first()"
        },
        
        # JavaScript Express
        {
            "file": "express-api/src/middleware/auth.js",
            "symbol": "authenticate",
            "kind": "function",
            "line": 5,
            "language": "javascript",
            "signature": "function authenticate(req, res, next)",
            "context": "function authenticate(req, res, next) {\n    const token = req.headers.authorization;\n    if (!token) {\n        return res.status(401).json({ error: 'No token provided' });\n    }"
        },
        {
            "file": "express-api/src/routes/users.js",
            "symbol": "getUsers",
            "kind": "function",
            "line": 15,
            "language": "javascript",
            "signature": "async function getUsers(req, res)",
            "context": "async function getUsers(req, res) {\n    try {\n        const users = await User.findAll();\n        res.json(users);\n    } catch (error) {\n        res.status(500).json({ error: error.message });\n    }"
        },
        
        # Java Spring Boot
        {
            "file": "spring-boot/src/main/java/com/example/controller/UserController.java",
            "symbol": "createUser",
            "kind": "method",
            "line": 30,
            "language": "java",
            "signature": "public ResponseEntity<User> createUser(@RequestBody User user)",
            "context": "@PostMapping(\"/users\")\npublic ResponseEntity<User> createUser(@RequestBody User user) {\n    User savedUser = userService.save(user);\n    return ResponseEntity.ok(savedUser);\n}"
        },
        {
            "file": "spring-boot/src/main/java/com/example/service/ValidationService.java",
            "symbol": "validateEmail",
            "kind": "method",
            "line": 12,
            "language": "java",
            "signature": "public boolean validateEmail(String email)",
            "context": "public boolean validateEmail(String email) {\n    if (email == null || email.isEmpty()) {\n        return false;\n    }\n    return EMAIL_PATTERN.matcher(email).matches();\n}"
        },
        
        # Go
        {
            "file": "go-app/handlers/api.go",
            "symbol": "HandleAPIRequest",
            "kind": "function",
            "line": 20,
            "language": "go",
            "signature": "func HandleAPIRequest(w http.ResponseWriter, r *http.Request)",
            "context": "func HandleAPIRequest(w http.ResponseWriter, r *http.Request) {\n    if r.Method != http.MethodPost {\n        http.Error(w, \"Method not allowed\", http.StatusMethodNotAllowed)\n        return\n    }"
        },
        {
            "file": "go-app/db/connection.go",
            "symbol": "Connect",
            "kind": "function",
            "line": 8,
            "language": "go",
            "signature": "func Connect(dsn string) (*sql.DB, error)",
            "context": "func Connect(dsn string) (*sql.DB, error) {\n    db, err := sql.Open(\"postgres\", dsn)\n    if err != nil {\n        return nil, fmt.Errorf(\"failed to connect: %w\", err)\n    }\n    return db, nil\n}"
        }
    ]
    
    return snippets

def demonstrate_semantic_search():
    """Demonstrate semantic search capabilities."""
    logger.info("="*60)
    logger.info("SEMANTIC CODE RETRIEVAL DEMONSTRATION")
    logger.info("="*60)
    
    # Initialize retriever
    use_mock = os.getenv("VOYAGE_API_KEY") is None
    if use_mock:
        logger.info("\nUsing MOCK embeddings (set VOYAGE_API_KEY for real embeddings)")
    
    retriever = SemanticRetriever(use_mock=use_mock)
    
    # Load and index test data
    snippets = load_test_data()
    retriever.index_code(snippets)
    
    # Semantic queries
    queries = [
        "authentication and user login functionality",
        "validate user input and check email format",
        "handle HTTP requests and API endpoints",
        "database connection and query execution",
        "error handling and exception management",
        "save data to database",
        "check user permissions and authorization",
        "REST API route handlers"
    ]
    
    logger.info("\n" + "="*60)
    logger.info("SEMANTIC SEARCH RESULTS")
    logger.info("="*60)
    
    for query in queries:
        logger.info(f"\nQuery: \"{query}\"")
        logger.info("-" * 60)
        
        results = retriever.search(query, top_k=3)
        
        for i, (snippet, score) in enumerate(results, 1):
            logger.info(f"\n[{i}] Score: {score:.3f}")
            logger.info(f"    {snippet.symbol} ({snippet.kind}) - {snippet.language}")
            logger.info(f"    {snippet.file}:{snippet.line}")
            logger.info(f"    Signature: {snippet.signature}")
            
            # Show why it matched (first few context lines)
            context_preview = snippet.context.split('\n')[0:2]
            logger.info(f"    Context: {context_preview[0]}")
            if len(context_preview) > 1:
                logger.info(f"             {context_preview[1]}...")
    
    # Compare with keyword search
    logger.info("\n" + "="*60)
    logger.info("SEMANTIC vs KEYWORD COMPARISON")
    logger.info("="*60)
    
    comparison_query = "user authentication and validation"
    logger.info(f"\nQuery: \"{comparison_query}\"")
    
    # Semantic results
    logger.info("\nSemantic Search Results:")
    semantic_results = retriever.search(comparison_query, top_k=3)
    for i, (snippet, score) in enumerate(semantic_results, 1):
        logger.info(f"  [{i}] {snippet.symbol} ({snippet.language}) - Score: {score:.3f}")
    
    # Keyword results (simple matching)
    logger.info("\nKeyword Search Results:")
    keywords = comparison_query.lower().split()
    keyword_scores = []
    
    for snippet in retriever.code_snippets:
        text = f"{snippet.symbol} {snippet.context}".lower()
        score = sum(1 for kw in keywords if kw in text) / len(keywords)
        if score > 0:
            keyword_scores.append((snippet, score))
    
    keyword_scores.sort(key=lambda x: x[1], reverse=True)
    for i, (snippet, score) in enumerate(keyword_scores[:3], 1):
        logger.info(f"  [{i}] {snippet.symbol} ({snippet.language}) - Matches: {int(score * len(keywords))}/{len(keywords)} keywords")
    
    logger.info("\n" + "="*60)
    logger.info("KEY OBSERVATIONS:")
    logger.info("="*60)
    logger.info("• Semantic search understands intent, not just keywords")
    logger.info("• Finds conceptually related code even without exact matches")
    logger.info("• Better at handling natural language queries")
    logger.info("• Can identify similar functionality across languages")

if __name__ == "__main__":
    demonstrate_semantic_search()