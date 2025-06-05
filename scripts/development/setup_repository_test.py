#!/usr/bin/env python3
"""
Development script to set up test repositories for repository management testing.

This script creates sample external repositories for testing the enhanced
repository management and cross-language translation features.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def create_sample_rust_repo(base_path: Path) -> Path:
    """Create a sample Rust repository with authentication patterns."""
    rust_repo = base_path / "rust_auth_examples"
    rust_repo.mkdir(parents=True, exist_ok=True)
    
    # Create Cargo.toml
    (rust_repo / "Cargo.toml").write_text("""[package]
name = "auth_examples"
version = "0.1.0"
edition = "2021"

[dependencies]
axum = "0.7"
tokio = { version = "1.0", features = ["full"] }
jsonwebtoken = "8"
bcrypt = "0.14"
serde = { version = "1.0", features = ["derive"] }
uuid = { version = "1.0", features = ["v4"] }
sqlx = { version = "0.7", features = ["runtime-tokio-rustls", "postgres"] }
""")
    
    # Create src directory
    src_dir = rust_repo / "src"
    src_dir.mkdir(exist_ok=True)
    
    # Create main.rs
    (src_dir / "main.rs").write_text("""use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use std::net::SocketAddr;
use tokio;

mod auth;
mod models;
mod middleware;

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/login", post(auth::login))
        .route("/protected", get(auth::protected_route))
        .layer(middleware::auth_middleware());

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Server running on {}", addr);
    
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}
""")
    
    # Create auth.rs
    (src_dir / "auth.rs").write_text("""use axum::{
    extract::Json,
    response::Json as ResponseJson,
    http::StatusCode,
};
use bcrypt::{hash, verify, DEFAULT_COST};
use jsonwebtoken::{encode, decode, Header, Algorithm, Validation, EncodingKey, DecodingKey};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::models::{User, LoginRequest, AuthError};

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    sub: String,
    exp: usize,
}

pub async fn authenticate_user(token: &str) -> Result<User, AuthError> {
    let token_data = decode::<Claims>(
        token,
        &DecodingKey::from_secret("secret".as_ref()),
        &Validation::new(Algorithm::HS256),
    )?;
    
    // In real app, fetch user from database
    let user = User {
        id: Uuid::parse_str(&token_data.claims.sub)?,
        username: "user".to_string(),
        email: "user@example.com".to_string(),
        password_hash: "".to_string(),
    };
    
    Ok(user)
}

pub async fn login(Json(payload): Json<LoginRequest>) -> Result<ResponseJson<String>, StatusCode> {
    // Hash password for comparison
    let password_hash = hash(&payload.password, DEFAULT_COST)
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    
    // Verify password (in real app, compare with stored hash)
    if verify(&payload.password, &password_hash)
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)? {
        
        let claims = Claims {
            sub: Uuid::new_v4().to_string(),
            exp: (chrono::Utc::now() + chrono::Duration::hours(24)).timestamp() as usize,
        };
        
        let token = encode(
            &Header::default(),
            &claims,
            &EncodingKey::from_secret("secret".as_ref()),
        ).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
        
        Ok(ResponseJson(token))
    } else {
        Err(StatusCode::UNAUTHORIZED)
    }
}

pub async fn protected_route() -> &'static str {
    "This is a protected route!"
}
""")
    
    # Create models.rs
    (src_dir / "models.rs").write_text("""use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize)]
pub struct User {
    pub id: Uuid,
    pub username: String,
    pub email: String,
    pub password_hash: String,
}

#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    pub username: String,
    pub password: String,
}

#[derive(Debug)]
pub enum AuthError {
    InvalidToken,
    TokenExpired,
    DatabaseError,
    HashError,
}

impl From<jsonwebtoken::errors::Error> for AuthError {
    fn from(_: jsonwebtoken::errors::Error) -> Self {
        AuthError::InvalidToken
    }
}

impl From<uuid::Error> for AuthError {
    fn from(_: uuid::Error) -> Self {
        AuthError::InvalidToken
    }
}
""")
    
    # Create middleware.rs
    (src_dir / "middleware.rs").write_text("""use axum::{
    extract::Request,
    http::{HeaderValue, StatusCode},
    middleware::Next,
    response::Response,
};

use crate::auth::authenticate_user;

pub async fn auth_middleware(request: Request, next: Next) -> Result<Response, StatusCode> {
    let auth_header = request
        .headers()
        .get("authorization")
        .and_then(|header| header.to_str().ok())
        .and_then(|header| header.strip_prefix("Bearer "));

    match auth_header {
        Some(token) => {
            match authenticate_user(token).await {
                Ok(_user) => {
                    let response = next.run(request).await;
                    Ok(response)
                }
                Err(_) => Err(StatusCode::UNAUTHORIZED),
            }
        }
        None => Err(StatusCode::UNAUTHORIZED),
    }
}

pub fn auth_middleware() -> axum::middleware::FromFn<impl Fn(Request, Next) -> Result<Response, StatusCode>> {
    axum::middleware::from_fn(auth_middleware)
}
""")
    
    print(f"✅ Created Rust authentication examples at: {rust_repo}")
    return rust_repo

def create_sample_go_repo(base_path: Path) -> Path:
    """Create a sample Go repository with web service patterns."""
    go_repo = base_path / "go_web_examples"
    go_repo.mkdir(parents=True, exist_ok=True)
    
    # Create go.mod
    (go_repo / "go.mod").write_text("""module github.com/example/go-web-examples

go 1.21

require (
    github.com/golang-jwt/jwt/v5 v5.0.0
    github.com/gorilla/mux v1.8.0
    golang.org/x/crypto v0.14.0
)
""")
    
    # Create main.go
    (go_repo / "main.go").write_text("""package main

import (
    "log"
    "net/http"
    
    "github.com/gorilla/mux"
    "github.com/example/go-web-examples/auth"
    "github.com/example/go-web-examples/middleware"
)

func main() {
    r := mux.NewRouter()
    
    // Public routes
    r.HandleFunc("/login", auth.LoginHandler).Methods("POST")
    
    // Protected routes
    protected := r.PathPrefix("/api").Subrouter()
    protected.Use(middleware.AuthMiddleware)
    protected.HandleFunc("/profile", auth.GetProfile).Methods("GET")
    
    log.Println("Server starting on :8080")
    log.Fatal(http.ListenAndServe(":8080", r))
}
""")
    
    # Create auth directory
    auth_dir = go_repo / "auth"
    auth_dir.mkdir(exist_ok=True)
    
    # Create auth/handlers.go
    (auth_dir / "handlers.go").write_text("""package auth

import (
    "encoding/json"
    "net/http"
    "time"
    
    "github.com/golang-jwt/jwt/v5"
    "golang.org/x/crypto/bcrypt"
)

type User struct {
    ID       string `json:"id"`
    Username string `json:"username"`
    Email    string `json:"email"`
    Password string `json:"-"`
}

type LoginRequest struct {
    Username string `json:"username"`
    Password string `json:"password"`
}

type LoginResponse struct {
    Token string `json:"token"`
    User  User   `json:"user"`
}

var jwtSecret = []byte("your-secret-key")

func AuthenticateUser(username, password string) (*User, error) {
    // In real app, fetch from database
    user := &User{
        ID:       "1",
        Username: username,
        Email:    username + "@example.com",
        Password: "$2a$10$hash...", // bcrypt hash
    }
    
    err := bcrypt.CompareHashAndPassword([]byte(user.Password), []byte(password))
    if err != nil {
        return nil, err
    }
    
    return user, nil
}

func GenerateToken(user *User) (string, error) {
    claims := jwt.MapClaims{
        "user_id": user.ID,
        "username": user.Username,
        "exp": time.Now().Add(time.Hour * 24).Unix(),
    }
    
    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString(jwtSecret)
}

func LoginHandler(w http.ResponseWriter, r *http.Request) {
    var req LoginRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "Invalid request", http.StatusBadRequest)
        return
    }
    
    user, err := AuthenticateUser(req.Username, req.Password)
    if err != nil {
        http.Error(w, "Invalid credentials", http.StatusUnauthorized)
        return
    }
    
    token, err := GenerateToken(user)
    if err != nil {
        http.Error(w, "Failed to generate token", http.StatusInternalServerError)
        return
    }
    
    response := LoginResponse{
        Token: token,
        User:  *user,
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}

func GetProfile(w http.ResponseWriter, r *http.Request) {
    // User is available from middleware context
    user := r.Context().Value("user").(*User)
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(user)
}
""")
    
    # Create middleware directory
    middleware_dir = go_repo / "middleware"
    middleware_dir.mkdir(exist_ok=True)
    
    # Create middleware/auth.go
    (middleware_dir / "auth.go").write_text("""package middleware

import (
    "context"
    "net/http"
    "strings"
    
    "github.com/golang-jwt/jwt/v5"
    "github.com/example/go-web-examples/auth"
)

func AuthMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        authHeader := r.Header.Get("Authorization")
        if authHeader == "" {
            http.Error(w, "Authorization header required", http.StatusUnauthorized)
            return
        }
        
        tokenString := strings.TrimPrefix(authHeader, "Bearer ")
        if tokenString == authHeader {
            http.Error(w, "Bearer token required", http.StatusUnauthorized)
            return
        }
        
        token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
            return []byte("your-secret-key"), nil
        })
        
        if err != nil || !token.Valid {
            http.Error(w, "Invalid token", http.StatusUnauthorized)
            return
        }
        
        claims, ok := token.Claims.(jwt.MapClaims)
        if !ok {
            http.Error(w, "Invalid token claims", http.StatusUnauthorized)
            return
        }
        
        userID := claims["user_id"].(string)
        user := &auth.User{
            ID:       userID,
            Username: claims["username"].(string),
        }
        
        ctx := context.WithValue(r.Context(), "user", user)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
""")
    
    print(f"✅ Created Go web service examples at: {go_repo}")
    return go_repo

def create_sample_python_repo(base_path: Path) -> Path:
    """Create a sample Python FastAPI repository for comparison."""
    python_repo = base_path / "python_fastapi_examples"
    python_repo.mkdir(parents=True, exist_ok=True)
    
    # Create requirements.txt
    (python_repo / "requirements.txt").write_text("""fastapi==0.104.1
uvicorn==0.24.0
pyjwt==2.8.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pydantic==2.5.0
""")
    
    # Create main.py
    (python_repo / "main.py").write_text("""from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Python FastAPI Auth Examples")

# Configuration
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Models
class User(BaseModel):
    id: str
    username: str
    email: str

class UserInDB(User):
    hashed_password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Authentication functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    # In real app, fetch from database
    fake_user = UserInDB(
        id="1",
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("secret123")
    )
    
    if verify_password(password, fake_user.hashed_password):
        return fake_user
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # In real app, fetch user from database
    user = User(id="1", username=username, email=f"{username}@example.com")
    return user

# Routes
@app.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/profile", response_model=User)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}, this is a protected route!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
""")
    
    print(f"✅ Created Python FastAPI examples at: {python_repo}")
    return python_repo

def main():
    """Set up test repositories for development."""
    print("🔧 Setting up test repositories for repository management...")
    
    # Create external_repos directory
    project_root = Path(__file__).parent.parent.parent
    external_repos_dir = project_root / "external_repos"
    external_repos_dir.mkdir(exist_ok=True)
    
    print(f"📁 Using external repositories directory: {external_repos_dir}")
    
    # Create sample repositories
    repos_created = []
    
    try:
        # Create Rust examples
        rust_repo = create_sample_rust_repo(external_repos_dir)
        repos_created.append(("Rust Auth Examples", rust_repo))
        
        # Create Go examples  
        go_repo = create_sample_go_repo(external_repos_dir)
        repos_created.append(("Go Web Examples", go_repo))
        
        # Create Python examples for comparison
        python_repo = create_sample_python_repo(external_repos_dir)
        repos_created.append(("Python FastAPI Examples", python_repo))
        
        print("\n🎉 Successfully created test repositories:")
        for name, path in repos_created:
            print(f"   • {name}: {path}")
        
        print(f"\n📋 Next steps:")
        print(f"   1. Start the development container:")
        print(f"      docker-compose -f docker-compose.yml -f docker-compose.dev.yml up")
        print(f"   2. Add repositories using MCP tools:")
        print(f"      add_reference_repository(path='/external_repos/rust_auth_examples', language='rust')")
        print(f"   3. Index and search across repositories:")
        print(f"      search_code('authentication', repository_filter={{'group_by_repository': true}})")
        print(f"   4. Clean up when done:")
        print(f"      cleanup_repositories(cleanup_expired=true)")
        
    except Exception as e:
        print(f"❌ Error creating test repositories: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())