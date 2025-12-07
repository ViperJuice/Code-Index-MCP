#!/usr/bin/env python3
"""Test multi-language codebase handling comprehensively."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import mcp_server_cli


async def test_multi_language_codebase():
    """Test handling of a single codebase with multiple languages."""
    print("=== Testing Multi-Language Codebase Handling ===\n")

    # Create a realistic multi-language project structure
    project_files = {
        # Frontend (JavaScript/TypeScript)
        "frontend/src/App.tsx": """import React from 'react';
import { UserService } from './services/UserService';

interface AppProps {
    title: string;
}

export default function App({ title }: AppProps) {
    const userService = new UserService();
    
    return (
        <div className="app">
            <h1>{title}</h1>
        </div>
    );
}""",
        "frontend/src/services/UserService.ts": """export interface User {
    id: number;
    name: string;
    email: string;
}

export class UserService {
    private apiUrl = '/api/users';
    
    async getUser(id: number): Promise<User> {
        const response = await fetch(`${this.apiUrl}/${id}`);
        return response.json();
    }
    
    async createUser(userData: Omit<User, 'id'>): Promise<User> {
        const response = await fetch(this.apiUrl, {
            method: 'POST',
            body: JSON.stringify(userData)
        });
        return response.json();
    }
}""",
        # Backend (Python)
        "backend/main.py": """from fastapi import FastAPI, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from database import UserRepository

app = FastAPI(title="User Management API")
user_repo = UserRepository()

class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str

class UserCreate(BaseModel):
    name: str
    email: str

@app.get("/api/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/users", response_model=User)
async def create_user(user_data: UserCreate):
    return await user_repo.create(user_data.dict())""",
        "backend/database.py": """import asyncpg
from typing import Optional, Dict, Any

class UserRepository:
    def __init__(self):
        self.connection_pool = None
    
    async def connect(self, database_url: str):
        self.connection_pool = await asyncpg.create_pool(database_url)
    
    async def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, email FROM users WHERE id = $1", 
                user_id
            )
            return dict(row) if row else None
    
    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id, name, email",
                user_data["name"], user_data["email"]
            )
            return dict(row)""",
        # Microservice (Go)
        "services/auth-service/main.go": """package main

import (
    "fmt"
    "log"
    "net/http"
    "github.com/gin-gonic/gin"
)

type AuthService struct {
    jwtSecret string
}

type LoginRequest struct {
    Email    string `json:"email" binding:"required"`
    Password string `json:"password" binding:"required"`
}

type AuthResponse struct {
    Token string `json:"token"`
    User  User   `json:"user"`
}

func NewAuthService(secret string) *AuthService {
    return &AuthService{jwtSecret: secret}
}

func (s *AuthService) Login(c *gin.Context) {
    var req LoginRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    // Authenticate user logic here
    token := s.generateToken(req.Email)
    
    c.JSON(http.StatusOK, AuthResponse{
        Token: token,
        User:  User{Email: req.Email},
    })
}

func main() {
    authService := NewAuthService("secret-key")
    
    r := gin.Default()
    r.POST("/auth/login", authService.Login)
    
    log.Println("Auth service starting on :8001")
    r.Run(":8001")
}""",
        "services/auth-service/types.go": """package main

type User struct {
    ID    int    `json:"id"`
    Email string `json:"email"`
    Name  string `json:"name"`
}

type TokenClaims struct {
    UserID int    `json:"user_id"`
    Email  string `json:"email"`
    Exp    int64  `json:"exp"`
}""",
        # Infrastructure (Rust)
        "infrastructure/logger/src/lib.rs": """use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LogLevel {
    Debug,
    Info,
    Warning,
    Error,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub level: LogLevel,
    pub message: String,
    pub metadata: HashMap<String, String>,
}

pub struct Logger {
    level: LogLevel,
    entries: Vec<LogEntry>,
}

impl Logger {
    pub fn new(level: LogLevel) -> Self {
        Self {
            level,
            entries: Vec::new(),
        }
    }
    
    pub fn log(&mut self, level: LogLevel, message: &str) {
        if self.should_log(&level) {
            let entry = LogEntry {
                timestamp: chrono::Utc::now(),
                level,
                message: message.to_string(),
                metadata: HashMap::new(),
            };
            self.entries.push(entry);
        }
    }
    
    fn should_log(&self, level: &LogLevel) -> bool {
        match (&self.level, level) {
            (LogLevel::Debug, _) => true,
            (LogLevel::Info, LogLevel::Debug) => false,
            (LogLevel::Info, _) => true,
            (LogLevel::Warning, LogLevel::Debug | LogLevel::Info) => false,
            (LogLevel::Warning, _) => true,
            (LogLevel::Error, LogLevel::Error) => true,
            (LogLevel::Error, _) => false,
        }
    }
}""",
        # Configuration
        "config/database.sql": """CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

INSERT INTO users (name, email) VALUES 
    ('John Doe', 'john@example.com'),
    ('Jane Smith', 'jane@example.com');""",
        "docker-compose.yml": """version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
      
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/app
    depends_on:
      - db
      - auth-service
      
  auth-service:
    build: ./services/auth-service
    ports:
      - "8001:8001"
      
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:""",
        "README.md": """# Multi-Language Microservices Project

## Architecture

- **Frontend**: React/TypeScript SPA
- **Backend**: Python FastAPI REST API  
- **Auth Service**: Go microservice
- **Logger**: Rust shared library
- **Database**: PostgreSQL

## Services

- Frontend (TypeScript): User interface
- Backend (Python): Main API server
- Auth Service (Go): Authentication microservice
- Logger (Rust): Shared logging infrastructure

## Getting Started

```bash
docker-compose up -d
```""",
    }

    # Create temporary directory and files
    temp_dir = tempfile.mkdtemp(prefix="multi_lang_test_")
    original_cwd = os.getcwd()
    os.chdir(temp_dir)

    try:
        print(f"Created test project in: {temp_dir}")

        # Create directory structure and files
        for file_path, content in project_files.items():
            full_path = Path(file_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        print(f"✓ Created {len(project_files)} files across multiple languages")

        # Initialize MCP services
        await mcp_server_cli.initialize_services()
        dispatcher = mcp_server_cli.dispatcher

        print(f"✓ Dispatcher supports {len(dispatcher.supported_languages)} languages")

        # Test 1: Index files across different languages
        print("\n1. Testing Cross-Language File Indexing...")

        languages_found = set()
        indexed_files = 0

        for file_path in project_files.keys():
            path_obj = Path(file_path)
            if path_obj.suffix in [".tsx", ".ts", ".py", ".go", ".rs", ".sql"]:
                try:
                    dispatcher.index_file(path_obj)
                    ext = path_obj.suffix
                    if ext == ".tsx" or ext == ".ts":
                        languages_found.add("typescript")
                    elif ext == ".py":
                        languages_found.add("python")
                    elif ext == ".go":
                        languages_found.add("go")
                    elif ext == ".rs":
                        languages_found.add("rust")
                    elif ext == ".sql":
                        languages_found.add("sql")

                    indexed_files += 1
                    print(f"   ✓ Indexed {file_path}")
                except Exception as e:
                    print(f"   ✗ Failed to index {file_path}: {e}")

        print(
            f"\n   Summary: {indexed_files} files indexed across {len(languages_found)} languages"
        )
        print(f"   Languages detected: {', '.join(sorted(languages_found))}")

        # Test 2: Cross-language symbol search
        print("\n2. Testing Cross-Language Symbol Search...")

        # Search for common concepts that appear in multiple languages
        cross_lang_symbols = {
            "User": "Data model used across frontend and backend",
            "create": "CRUD operation in multiple services",
            "login": "Authentication functionality",
            "Logger": "Shared logging infrastructure",
            "main": "Entry points in Go and Rust",
            "async": "Async patterns in Python and TypeScript",
        }

        search_results = {}
        for symbol, description in cross_lang_symbols.items():
            results = list(dispatcher.search(symbol, limit=20))
            files_found = set()

            for result in results:
                file_path = result.get("file", "")
                if file_path:
                    files_found.add(Path(file_path).name)

            search_results[symbol] = {
                "total_results": len(results),
                "files_found": len(files_found),
                "description": description,
            }

            print(f"   '{symbol}': {len(results)} results in {len(files_found)} files")

        # Test 3: Cross-language semantic search
        print("\n3. Testing Cross-Language Semantic Search...")

        semantic_queries = [
            "user authentication",
            "database operations",
            "API endpoints",
            "error handling",
            "data validation",
        ]

        semantic_results = {}
        for query in semantic_queries:
            try:
                results = list(dispatcher.search(query, semantic=True, limit=10))
                files_with_results = set()

                for result in results:
                    file_path = result.get("file", "")
                    if file_path:
                        files_with_results.add(Path(file_path).suffix)

                semantic_results[query] = {
                    "results": len(results),
                    "languages": len(files_with_results),
                }

                print(
                    f"   '{query}': {len(results)} results across {len(files_with_results)} language types"
                )
            except Exception as e:
                print(f"   '{query}': Error - {e}")
                semantic_results[query] = {"results": 0, "languages": 0}

        # Test 4: Project structure analysis
        print("\n4. Testing Project Structure Analysis...")

        stats = dispatcher.get_statistics()
        loaded_languages = stats.get("loaded_languages", [])

        print(f"   ✓ Total plugins loaded: {stats.get('total_plugins', 0)}")
        print(f"   ✓ Languages active: {', '.join(sorted(loaded_languages))}")
        print(f"   ✓ Search operations: {stats.get('operations', {}).get('searches', 0)}")
        print(f"   ✓ Index operations: {stats.get('operations', {}).get('indexings', 0)}")

        # Test 5: Symbol lookup across languages
        print("\n5. Testing Cross-Language Symbol Lookup...")

        symbol_lookup_tests = ["User", "Logger", "AuthService", "create_user"]
        found_symbols = 0

        for symbol in symbol_lookup_tests:
            definition = dispatcher.lookup(symbol)
            if definition:
                file_name = Path(definition.get("defined_in", "")).name
                lang = Path(definition.get("defined_in", "")).suffix
                print(f"   ✓ {symbol}: {definition.get('kind', 'unknown')} in {file_name} ({lang})")
                found_symbols += 1
            else:
                print(f"   ✗ {symbol}: not found")

        # Summary and assessment
        print("\n=== Multi-Language Codebase Assessment ===")

        total_symbol_results = sum(r["total_results"] for r in search_results.values())
        total_semantic_results = sum(r["results"] for r in semantic_results.values())

        print("\nCapabilities Demonstrated:")
        print(f"  ✓ Languages indexed: {len(languages_found)}")
        print(f"  ✓ Files processed: {indexed_files}")
        print(f"  ✓ Cross-language symbol search: {total_symbol_results} results")
        print(f"  ✓ Semantic search across languages: {total_semantic_results} results")
        print(f"  ✓ Symbol definitions found: {found_symbols}/{len(symbol_lookup_tests)}")
        print(f"  ✓ Active language plugins: {len(loaded_languages)}")

        # Multi-language specific features
        print("\nMulti-Language Features:")

        # Check for cross-references
        user_results = search_results.get("User", {})
        if user_results.get("files_found", 0) > 1:
            print(
                f"  ✓ Cross-language data models: 'User' found in {user_results['files_found']} files"
            )

        # Check for shared concepts
        create_results = search_results.get("create", {})
        if create_results.get("total_results", 0) > 0:
            print("  ✓ Shared functionality patterns: 'create' operations across languages")

        # Check for service communication
        if total_semantic_results > 0:
            print("  ✓ Semantic understanding: AI can find related concepts across languages")

        success_criteria = (
            len(languages_found) >= 4  # At least 4 different languages
            and indexed_files >= 8  # At least 8 files indexed
            and total_symbol_results > 20  # Good symbol search results
            and found_symbols >= 2  # Symbol lookup working
        )

        return success_criteria, {
            "languages_found": list(languages_found),
            "indexed_files": indexed_files,
            "search_results": search_results,
            "semantic_results": semantic_results,
            "loaded_languages": loaded_languages,
            "symbol_lookups": found_symbols,
        }

    finally:
        # Cleanup
        os.chdir(original_cwd)
        import shutil

        shutil.rmtree(temp_dir)
        print("\n✓ Cleaned up test directory")


async def main():
    """Run multi-language codebase test."""
    try:
        success, results = await test_multi_language_codebase()

        if success:
            print("\n🎉 Multi-Language Codebase Support: EXCELLENT!")
            print("The MCP server successfully handles complex multi-language projects")
            print("with cross-language search, symbol lookup, and semantic understanding!")
        else:
            print("\n⚠️ Multi-Language Support needs improvement")
            print("Some cross-language features may need enhancement")

        return success

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)
