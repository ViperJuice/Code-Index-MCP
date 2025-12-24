"""Test utilities for git-integrated repository tracking tests."""

import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Language file templates for creating diverse test repositories
TEST_FILE_TEMPLATES = {
    "python": {
        "main.py": """#!/usr/bin/env python3
'''Main application entry point.'''

import os
import sys
from typing import List, Optional
from src.models import User, Post
from src.services import UserService, PostService

def main(args: List[str]) -> int:
    '''Main function.'''
    service = UserService()
    users = service.get_all_users()
    print(f"Found {len(users)} users")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
""",
        "src/models.py": """'''Data models for the application.'''

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    '''User model.'''
    id: int
    username: str
    email: str
    created_at: datetime = field(default_factory=datetime.now)
    
    def __repr__(self) -> str:
        return f"User({self.username})"

@dataclass
class Post:
    '''Post model.'''
    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime = field(default_factory=datetime.now)
""",
        "src/services.py": """'''Business logic services.'''

import logging
from typing import List, Optional
from .models import User, Post

logger = logging.getLogger(__name__)

class UserService:
    '''Service for user operations.'''
    
    def __init__(self):
        self.users: List[User] = []
        
    def create_user(self, username: str, email: str) -> User:
        '''Create a new user.'''
        user = User(
            id=len(self.users) + 1,
            username=username,
            email=email
        )
        self.users.append(user)
        logger.info(f"Created user: {username}")
        return user
        
    def get_all_users(self) -> List[User]:
        '''Get all users.'''
        return self.users.copy()

class PostService:
    '''Service for post operations.'''
    
    def __init__(self):
        self.posts: List[Post] = []
        
    def create_post(self, title: str, content: str, author_id: int) -> Post:
        '''Create a new post.'''
        post = Post(
            id=len(self.posts) + 1,
            title=title,
            content=content,
            author_id=author_id
        )
        self.posts.append(post)
        return post
""",
        "tests/test_services.py": """'''Tests for services.'''

import pytest
from src.services import UserService, PostService

def test_create_user():
    '''Test user creation.'''
    service = UserService()
    user = service.create_user("testuser", "test@example.com")
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.id == 1

def test_create_post():
    '''Test post creation.'''
    service = PostService()
    post = service.create_post("Test Post", "Content", 1)
    assert post.title == "Test Post"
    assert post.author_id == 1
""",
    },
    "javascript": {
        "index.js": """// Main application entry point
import express from 'express';
import { UserController } from './controllers/UserController.js';
import { PostController } from './controllers/PostController.js';
import { Database } from './db/Database.js';

const app = express();
const db = new Database();

// Middleware
app.use(express.json());

// Controllers
const userController = new UserController(db);
const postController = new PostController(db);

// Routes
app.get('/api/users', (req, res) => userController.getAllUsers(req, res));
app.post('/api/users', (req, res) => userController.createUser(req, res));
app.get('/api/posts', (req, res) => postController.getAllPosts(req, res));
app.post('/api/posts', (req, res) => postController.createPost(req, res));

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
""",
        "controllers/UserController.js": """// User controller
export class UserController {
    constructor(database) {
        this.db = database;
    }
    
    async getAllUsers(req, res) {
        try {
            const users = await this.db.getUsers();
            res.json(users);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }
    
    async createUser(req, res) {
        try {
            const { username, email } = req.body;
            const user = await this.db.createUser(username, email);
            res.status(201).json(user);
        } catch (error) {
            res.status(400).json({ error: error.message });
        }
    }
}
""",
        "db/Database.js": """// Database abstraction
export class Database {
    constructor() {
        this.users = [];
        this.posts = [];
    }
    
    async getUsers() {
        return this.users;
    }
    
    async createUser(username, email) {
        const user = {
            id: this.users.length + 1,
            username,
            email,
            createdAt: new Date()
        };
        this.users.push(user);
        return user;
    }
    
    async getPosts() {
        return this.posts;
    }
    
    async createPost(title, content, authorId) {
        const post = {
            id: this.posts.length + 1,
            title,
            content,
            authorId,
            createdAt: new Date()
        };
        this.posts.push(post);
        return post;
    }
}
""",
    },
    "go": {
        "main.go": """package main

import (
    "fmt"
    "log"
    "net/http"
    
    "github.com/example/myapp/internal/handlers"
    "github.com/example/myapp/internal/services"
)

func main() {
    // Initialize services
    userService := services.NewUserService()
    postService := services.NewPostService()
    
    // Initialize handlers
    userHandler := handlers.NewUserHandler(userService)
    postHandler := handlers.NewPostHandler(postService)
    
    // Setup routes
    http.HandleFunc("/api/users", userHandler.HandleUsers)
    http.HandleFunc("/api/posts", postHandler.HandlePosts)
    
    // Start server
    fmt.Println("Server starting on :8080...")
    log.Fatal(http.ListenAndServe(":8080", nil))
}
""",
        "internal/models/user.go": """package models

import "time"

// User represents a user in the system
type User struct {
    ID        int       `json:"id"`
    Username  string    `json:"username"`
    Email     string    `json:"email"`
    CreatedAt time.Time `json:"created_at"`
}

// NewUser creates a new user instance
func NewUser(username, email string) *User {
    return &User{
        Username:  username,
        Email:     email,
        CreatedAt: time.Now(),
    }
}
""",
        "internal/services/user_service.go": """package services

import (
    "sync"
    
    "github.com/example/myapp/internal/models"
)

// UserService handles user operations
type UserService struct {
    mu    sync.RWMutex
    users []*models.User
}

// NewUserService creates a new user service
func NewUserService() *UserService {
    return &UserService{
        users: make([]*models.User, 0),
    }
}

// CreateUser creates a new user
func (s *UserService) CreateUser(username, email string) *models.User {
    s.mu.Lock()
    defer s.mu.Unlock()
    
    user := models.NewUser(username, email)
    user.ID = len(s.users) + 1
    s.users = append(s.users, user)
    
    return user
}

// GetAllUsers returns all users
func (s *UserService) GetAllUsers() []*models.User {
    s.mu.RLock()
    defer s.mu.RUnlock()
    
    result := make([]*models.User, len(s.users))
    copy(result, s.users)
    return result
}
""",
    },
}


@dataclass
class GitCommit:
    """Represents a git commit."""

    message: str
    files: Dict[str, str]  # filename -> action (add, modify, delete)


@dataclass
class TestRepository:
    """Test repository information."""

    path: Path
    name: str
    language: str
    commit_history: List[str] = field(default_factory=list)
    remote_url: Optional[str] = None


class TestRepositoryBuilder:
    """Builder for creating test repositories with git history."""

    @staticmethod
    def run_git_command(cmd: str, cwd: Path) -> Tuple[int, str, str]:
        """Run a git command and return (returncode, stdout, stderr)."""
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    @classmethod
    def create_repository(
        cls,
        base_dir: Path,
        name: str,
        language: str = "python",
        init_git: bool = True,
        commits: Optional[List[GitCommit]] = None,
    ) -> TestRepository:
        """Create a test repository with optional git history."""
        repo_path = base_dir / name
        repo_path.mkdir(parents=True, exist_ok=True)

        repo = TestRepository(path=repo_path, name=name, language=language)

        if init_git:
            # Initialize git
            cls.run_git_command("git init", repo_path)
            cls.run_git_command("git config user.name 'Test User'", repo_path)
            cls.run_git_command("git config user.email 'test@example.com'", repo_path)

        # Create initial files based on language
        if language in TEST_FILE_TEMPLATES:
            for file_path, content in TEST_FILE_TEMPLATES[language].items():
                full_path = repo_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)

        if init_git:
            # Initial commit
            cls.run_git_command("git add .", repo_path)
            returncode, stdout, stderr = cls.run_git_command(
                "git commit -m 'Initial commit'", repo_path
            )
            if returncode == 0:
                commit_hash = cls.run_git_command("git rev-parse HEAD", repo_path)[1].strip()
                repo.commit_history.append(commit_hash)

        # Apply additional commits if provided
        if commits and init_git:
            for commit in commits:
                cls.apply_commit(repo, commit)

        return repo

    @classmethod
    def apply_commit(cls, repo: TestRepository, commit: GitCommit):
        """Apply a commit to the repository."""
        for file_path, action in commit.files.items():
            full_path = repo.path / file_path

            if action == "add":
                full_path.parent.mkdir(parents=True, exist_ok=True)
                content = f"# New file: {file_path}\n# Added in commit: {commit.message}\n"
                full_path.write_text(content)
                cls.run_git_command(f"git add {file_path}", repo.path)

            elif action == "modify":
                if full_path.exists():
                    content = full_path.read_text()
                    content += f"\n# Modified in commit: {commit.message}\n"
                    full_path.write_text(content)
                    cls.run_git_command(f"git add {file_path}", repo.path)

            elif action == "delete":
                if full_path.exists():
                    cls.run_git_command(f"git rm {file_path}", repo.path)

        # Commit changes
        returncode, stdout, stderr = cls.run_git_command(
            f'git commit -m "{commit.message}"', repo.path
        )
        if returncode == 0:
            commit_hash = cls.run_git_command("git rev-parse HEAD", repo.path)[1].strip()
            repo.commit_history.append(commit_hash)

    @classmethod
    def create_multi_language_repo(
        cls, base_dir: Path, name: str = "multi_lang_project"
    ) -> TestRepository:
        """Create a repository with multiple programming languages."""
        repo = cls.create_repository(base_dir, name, language="python", init_git=True)

        # Add JavaScript files
        js_files = TEST_FILE_TEMPLATES.get("javascript", {})
        for file_path, content in js_files.items():
            full_path = repo.path / "frontend" / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        # Add Go files
        go_files = TEST_FILE_TEMPLATES.get("go", {})
        for file_path, content in go_files.items():
            full_path = repo.path / "backend" / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        # Commit the additions
        cls.run_git_command("git add .", repo.path)
        cls.run_git_command("git commit -m 'Add frontend and backend code'", repo.path)

        commit_hash = cls.run_git_command("git rev-parse HEAD", repo.path)[1].strip()
        repo.commit_history.append(commit_hash)

        return repo


class PerformanceTracker:
    """Track performance metrics for tests."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.start_times: Dict[str, float] = {}

    def start_timing(self, operation: str):
        """Start timing an operation."""
        self.start_times[operation] = time.time()

    def end_timing(self, operation: str) -> float:
        """End timing and record the duration."""
        if operation not in self.start_times:
            return 0.0

        duration = time.time() - self.start_times[operation]

        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)

        del self.start_times[operation]
        return duration

    def get_average(self, operation: str) -> float:
        """Get average duration for an operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return 0.0
        return sum(self.metrics[operation]) / len(self.metrics[operation])

    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary statistics for all operations."""
        summary = {}
        for operation, durations in self.metrics.items():
            if durations:
                summary[operation] = {
                    "count": len(durations),
                    "total": sum(durations),
                    "average": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                }
        return summary


def create_test_environment() -> Path:
    """Create a temporary test environment."""
    return Path(tempfile.mkdtemp(prefix="mcp_test_"))


def cleanup_test_environment(path: Path):
    """Clean up test environment."""
    if path.exists() and str(path).startswith("/tmp"):
        shutil.rmtree(path)


def count_files_by_extension(path: Path) -> Dict[str, int]:
    """Count files by extension in a directory."""
    counts = {}
    for file_path in path.rglob("*"):
        if file_path.is_file() and not str(file_path).startswith(".git"):
            ext = file_path.suffix.lower()
            counts[ext] = counts.get(ext, 0) + 1
    return counts


def measure_index_size(index_path: Path) -> float:
    """Measure the size of an index in MB."""
    if not index_path.exists():
        return 0.0
    return index_path.stat().st_size / (1024 * 1024)  # Convert to MB
