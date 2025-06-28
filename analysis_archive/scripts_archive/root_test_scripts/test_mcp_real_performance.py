#!/usr/bin/env python3
"""Test real MCP server performance vs direct search."""

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

def create_realistic_codebase(base_dir):
    """Create a more realistic codebase structure."""
    repo_dir = base_dir / "myproject"
    repo_dir.mkdir()
    
    # Create Python package structure
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "__init__.py").write_text("")
    
    (repo_dir / "src" / "models.py").write_text("""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False)
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
""")
    
    (repo_dir / "src" / "services.py").write_text("""
import logging
from typing import List, Optional
from datetime import datetime
from .models import User, Post

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db_session):
        self.db = db_session
        
    def create_user(self, username: str, email: str) -> User:
        logger.info(f"Creating user: {username}")
        user = User(username=username, email=email, created_at=datetime.utcnow())
        self.db.add(user)
        self.db.commit()
        return user
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        logger.debug(f"Fetching user by username: {username}")
        return self.db.query(User).filter_by(username=username).first()
    
    def get_all_users(self) -> List[User]:
        logger.debug("Fetching all users")
        return self.db.query(User).all()

class PostService:
    def __init__(self, db_session):
        self.db = db_session
        
    def create_post(self, title: str, content: str, user_id: int) -> Post:
        logger.info(f"Creating post: {title}")
        post = Post(
            title=title,
            content=content,
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        self.db.add(post)
        self.db.commit()
        return post
    
    def get_posts_by_user(self, user_id: int) -> List[Post]:
        logger.debug(f"Fetching posts for user: {user_id}")
        return self.db.query(Post).filter_by(user_id=user_id).all()
""")
    
    (repo_dir / "src" / "api.py").write_text("""
from flask import Flask, request, jsonify
from flask_cors import CORS
from .services import UserService, PostService

app = Flask(__name__)
CORS(app)

@app.route('/api/users', methods=['GET'])
def get_users():
    '''Get all users.'''
    users = user_service.get_all_users()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email
    } for u in users])

@app.route('/api/users', methods=['POST'])
def create_user():
    '''Create a new user.'''
    data = request.json
    user = user_service.create_user(
        username=data['username'],
        email=data['email']
    )
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email
    }), 201

@app.route('/api/users/<username>', methods=['GET'])
def get_user(username):
    '''Get user by username.'''
    user = user_service.get_user_by_username(username)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email
    })

@app.route('/api/posts', methods=['POST'])
def create_post():
    '''Create a new post.'''
    data = request.json
    post = post_service.create_post(
        title=data['title'],
        content=data['content'],
        user_id=data['user_id']
    )
    return jsonify({
        'id': post.id,
        'title': post.title,
        'user_id': post.user_id
    }), 201
""")
    
    # Create tests
    (repo_dir / "tests").mkdir()
    (repo_dir / "tests" / "__init__.py").write_text("")
    
    (repo_dir / "tests" / "test_services.py").write_text("""
import pytest
from datetime import datetime
from src.services import UserService, PostService

def test_create_user(db_session):
    service = UserService(db_session)
    user = service.create_user("testuser", "test@example.com")
    
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.created_at is not None

def test_get_user_by_username(db_session):
    service = UserService(db_session)
    service.create_user("findme", "find@example.com")
    
    user = service.get_user_by_username("findme")
    assert user is not None
    assert user.username == "findme"
    
    missing = service.get_user_by_username("notexist")
    assert missing is None

def test_create_post(db_session):
    user_service = UserService(db_session)
    post_service = PostService(db_session)
    
    user = user_service.create_user("author", "author@example.com")
    post = post_service.create_post("Test Post", "Content here", user.id)
    
    assert post.title == "Test Post"
    assert post.content == "Content here"
    assert post.user_id == user.id
""")
    
    # Create JavaScript files
    (repo_dir / "frontend").mkdir()
    (repo_dir / "frontend" / "app.js").write_text("""
import { UserAPI } from './api/user-api.js';
import { PostAPI } from './api/post-api.js';

class Application {
    constructor() {
        this.userAPI = new UserAPI();
        this.postAPI = new PostAPI();
    }
    
    async loadUsers() {
        try {
            const users = await this.userAPI.getAllUsers();
            console.log('Loaded users:', users);
            return users;
        } catch (error) {
            console.error('Error loading users:', error);
        }
    }
    
    async createUser(username, email) {
        try {
            const user = await this.userAPI.createUser({ username, email });
            console.log('Created user:', user);
            return user;
        } catch (error) {
            console.error('Error creating user:', error);
        }
    }
}

const app = new Application();
export default app;
""")
    
    return repo_dir

def run_mcp_server_search(repo_path, queries):
    """Run searches using MCP server subprocess."""
    print("\n=== Testing MCP Server Search ===")
    
    # First, index the repository
    print("Indexing with MCP...")
    start = time.time()
    
    # Run mcp_cli.py to index
    cmd = [sys.executable, "scripts/cli/mcp_cli.py", "index", "create", str(repo_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error indexing: {result.stderr}")
        # Try alternative approach
        cmd = [sys.executable, "-m", "mcp_server.cli", "index", "create", str(repo_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
    
    index_time = time.time() - start
    print(f"Indexing completed in {index_time:.3f}s")
    
    # Now run searches
    results = {}
    for query in queries:
        start = time.time()
        
        # Use mcp_cli.py to search
        cmd = [sys.executable, "scripts/cli/mcp_cli.py", "search", query, "--limit", "20"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        search_time = time.time() - start
        
        # Count results (simple line count)
        result_lines = result.stdout.strip().split('\n') if result.stdout else []
        match_count = len([l for l in result_lines if l and not l.startswith('Searching')])
        
        results[query] = {
            "time": search_time,
            "matches": match_count
        }
        
        print(f"  '{query}': {match_count} matches in {search_time:.3f}s")
    
    return results, index_time

def run_direct_search(repo_path, queries):
    """Run direct searches using grep/ripgrep."""
    print("\n=== Testing Direct Search ===")
    
    # Check for ripgrep
    has_rg = subprocess.run(["which", "rg"], capture_output=True).returncode == 0
    
    results = {}
    for query in queries:
        start = time.time()
        
        if has_rg:
            cmd = ["rg", "-n", query, str(repo_path)]
        else:
            cmd = ["grep", "-rn", query, str(repo_path)]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        search_time = time.time() - start
        
        # Count matches
        match_count = len(result.stdout.strip().split('\n')) if result.stdout else 0
        
        results[query] = {
            "time": search_time,
            "matches": match_count,
            "tool": "ripgrep" if has_rg else "grep"
        }
        
        print(f"  '{query}': {match_count} matches in {search_time:.3f}s")
    
    return results

def main():
    """Run the performance comparison."""
    print("MCP Server vs Direct Search Performance Test")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        # Create test codebase
        print("Creating test codebase...")
        repo_path = create_realistic_codebase(base_dir)
        
        # Count files
        py_files = list(repo_path.rglob("*.py"))
        js_files = list(repo_path.rglob("*.js"))
        print(f"  Created {len(py_files)} Python files and {len(js_files)} JavaScript files")
        
        # Define realistic queries
        queries = [
            "UserService",           # Class name
            "create_user",          # Method name
            "logger.info",          # Logger usage
            "Column",               # SQLAlchemy
            "async",                # JavaScript async
            "test_",                # Test functions
            "@app.route",           # Flask decorator
            "import",               # Import statements
        ]
        
        # Run tests
        direct_results = run_direct_search(repo_path, queries)
        
        # Try MCP if available
        try:
            mcp_results, index_time = run_mcp_server_search(repo_path, queries)
            has_mcp = True
        except Exception as e:
            print(f"\nMCP server not available: {e}")
            has_mcp = False
            mcp_results = {}
            index_time = 0
        
        # Display results
        print("\n" + "=" * 60)
        print("Performance Results:")
        print(f"{'Query':<20} {'Direct':<15} {'MCP':<15} {'Direct Matches':<15} {'MCP Matches':<15}")
        print("-" * 80)
        
        total_direct = 0
        total_mcp = 0
        
        for query in queries:
            direct = direct_results.get(query, {})
            mcp = mcp_results.get(query, {}) if has_mcp else {}
            
            d_time = direct.get('time', 0)
            m_time = mcp.get('time', 0)
            d_matches = direct.get('matches', 0)
            m_matches = mcp.get('matches', 0)
            
            total_direct += d_time
            total_mcp += m_time
            
            if has_mcp:
                print(f"{query:<20} {d_time:<15.3f} {m_time:<15.3f} {d_matches:<15} {m_matches:<15}")
            else:
                print(f"{query:<20} {d_time:<15.3f} {'N/A':<15} {d_matches:<15} {'N/A':<15}")
        
        print("-" * 80)
        if has_mcp:
            print(f"{'Total Query Time':<20} {total_direct:<15.3f} {total_mcp:<15.3f}")
        else:
            print(f"{'Total Query Time':<20} {total_direct:<15.3f} {'N/A':<15}")
        
        if has_mcp:
            print(f"\nMCP Index Time: {index_time:.3f}s")
            print(f"Break-even: ~{int(index_time / (total_direct - total_mcp))} queries" 
                  if total_direct > total_mcp else "Direct is faster overall")
        
        print(f"\nDirect search tool: {direct_results[queries[0]].get('tool', 'unknown')}")

if __name__ == "__main__":
    main()