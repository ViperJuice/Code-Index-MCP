#!/usr/bin/env python3
"""Simple performance test comparing indexed vs direct search."""

import os
import sys
import time
import json
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_test_files(base_dir):
    """Create test files for searching."""
    files = {
        "user_service.py": """
class UserService:
    def __init__(self, db_connection):
        self.db = db_connection
        self.logger = get_logger(__name__)
    
    def get_user_by_id(self, user_id: int):
        self.logger.info(f"Fetching user {user_id}")
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
    
    def create_user(self, username: str, email: str):
        self.logger.info(f"Creating user {username}")
        return self.db.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            (username, email)
        )
    
    def update_user_email(self, user_id: int, new_email: str):
        self.logger.info(f"Updating email for user {user_id}")
        return self.db.execute(
            "UPDATE users SET email = ? WHERE id = ?",
            (new_email, user_id)
        )
""",
        "auth_handler.py": """
import jwt
from datetime import datetime, timedelta

class AuthHandler:
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.algorithm = 'HS256'
    
    def generate_token(self, user_id: int) -> str:
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
""",
        "database.py": """
import sqlite3
from contextlib import contextmanager

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def execute(self, query: str, params=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.lastrowid
    
    def query(self, query: str, params=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
""",
        "api_routes.py": """
from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        try:
            auth_handler.verify_token(token)
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/users/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    user = user_service.get_user_by_id(user_id)
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/users', methods=['POST'])
@require_auth
def create_user():
    data = request.json
    user_id = user_service.create_user(data['username'], data['email'])
    return jsonify({'id': user_id}), 201
"""
    }
    
    # Create files
    for filename, content in files.items():
        filepath = base_dir / filename
        filepath.write_text(content)
    
    return list(files.keys())

def test_direct_search(base_dir, queries):
    """Test direct file search (grep/ripgrep)."""
    results = {}
    
    # Check if ripgrep is available
    has_rg = subprocess.run(["which", "rg"], capture_output=True).returncode == 0
    tool = "rg" if has_rg else "grep"
    
    print(f"\nTesting direct search with {tool}:")
    
    for query in queries:
        start = time.time()
        
        if has_rg:
            cmd = ["rg", "-c", query, str(base_dir)]
        else:
            cmd = ["grep", "-r", "-c", query, str(base_dir)]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = time.time() - start
            
            # Parse results
            matches = 0
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        count = line.split(':')[-1]
                        try:
                            matches += int(count)
                        except ValueError:
                            pass
            
            results[query] = {
                "time": duration,
                "matches": matches,
                "tool": tool
            }
            
            print(f"  '{query}': {matches} matches in {duration:.4f}s")
            
        except Exception as e:
            print(f"  '{query}': Error - {e}")
            results[query] = {"time": 0, "matches": 0, "error": str(e)}
    
    return results

def test_indexed_search(base_dir, queries):
    """Test search using pre-built index (simulate MCP)."""
    # For this test, we'll simulate an indexed search by pre-processing files
    print("\nTesting indexed search (simulated):")
    
    # Build a simple in-memory index
    print("  Building index...")
    start = time.time()
    
    index = {}
    for filepath in base_dir.glob("*.py"):
        with open(filepath, 'r') as f:
            content = f.read()
            # Simple word-based index
            words = set(content.split())
            for word in words:
                if word not in index:
                    index[word] = []
                index[word].append(filepath.name)
    
    index_time = time.time() - start
    print(f"  Index built in {index_time:.4f}s")
    
    # Search using index
    results = {}
    for query in queries:
        start = time.time()
        
        # Simple search in index
        matches = 0
        if query in index:
            matches = len(index[query])
        
        # Also check substrings (simplified)
        for word in index:
            if query.lower() in word.lower() and word != query:
                matches += len(index[word])
        
        duration = time.time() - start
        
        results[query] = {
            "time": duration,
            "matches": matches,
            "index_time": index_time
        }
        
        print(f"  '{query}': {matches} matches in {duration:.4f}s")
    
    return results, index_time

def main():
    """Run the performance comparison."""
    print("Simple Search Performance Test")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        # Create test files
        print("Creating test files...")
        files = create_test_files(base_dir)
        print(f"  Created {len(files)} files")
        
        # Define search queries
        queries = [
            "UserService",      # Class name
            "get_user_by_id",   # Method name
            "logger",           # Common term
            "SELECT",           # SQL keyword
            "jwt",              # Import
            "def",              # Python keyword
            "@app.route",       # Decorator
            "user_id",          # Variable
        ]
        
        # Run tests
        direct_results = test_direct_search(base_dir, queries)
        indexed_results, index_time = test_indexed_search(base_dir, queries)
        
        # Compare results
        print("\n" + "=" * 50)
        print("Performance Comparison:")
        print(f"{'Query':<20} {'Direct Time':<15} {'Indexed Time':<15} {'Speedup':<10}")
        print("-" * 60)
        
        total_direct = 0
        total_indexed = 0
        
        for query in queries:
            direct = direct_results.get(query, {})
            indexed = indexed_results.get(query, {})
            
            d_time = direct.get('time', 0)
            i_time = indexed.get('time', 0)
            
            total_direct += d_time
            total_indexed += i_time
            
            speedup = d_time / i_time if i_time > 0 else 0
            
            print(f"{query:<20} {d_time:<15.4f} {i_time:<15.4f} {speedup:<10.2f}x")
        
        print("-" * 60)
        print(f"{'Total':<20} {total_direct:<15.4f} {total_indexed:<15.4f}")
        
        print(f"\nIndex build time: {index_time:.4f}s")
        print(f"Break-even queries: {index_time / (total_direct - total_indexed):.1f}" 
              if total_direct > total_indexed else "Direct is faster")
        
        # Efficiency analysis
        print("\nEfficiency Analysis:")
        print(f"  Direct search tool: {direct_results[queries[0]].get('tool', 'unknown')}")
        print(f"  Average direct time: {total_direct/len(queries):.4f}s")
        print(f"  Average indexed time: {total_indexed/len(queries):.4f}s")
        print(f"  Indexed speedup: {total_direct/total_indexed:.2f}x" if total_indexed > 0 else "N/A")

if __name__ == "__main__":
    main()