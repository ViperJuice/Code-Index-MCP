# JWT Authentication Overview

## Introduction
JSON Web Tokens (JWT) provide a secure, stateless authentication mechanism for APIs. In the MCP Server context, JWT enables secure access control for code indexing and search operations while maintaining high performance.

## Key Concepts

### JWT Structure
- **Header**: Algorithm and token type
- **Payload**: Claims (user data, permissions)
- **Signature**: Verification mechanism

### Benefits for MCP Server
- Stateless authentication (no session storage)
- Scalable across multiple API instances
- Fine-grained permissions per token
- Time-based access control
- Cross-service authentication

## Installation

```bash
# Recommended dependencies (2024)
pip install PyJWT>=2.8.0
pip install "passlib[bcrypt]"
pip install python-multipart
pip install cryptography  # For RS256 support
```

## Basic Implementation

### Configuration
```python
# config.py
from pydantic import BaseSettings
from datetime import timedelta

class JWTSettings(BaseSettings):
    SECRET_KEY: str  # Generate with: openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # For RS256 (optional)
    PRIVATE_KEY_PATH: str = None
    PUBLIC_KEY_PATH: str = None
    
    class Config:
        env_file = ".env"

jwt_settings = JWTSettings()
```

### Token Generation
```python
# auth/jwt.py
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=jwt_settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode, 
        jwt_settings.SECRET_KEY, 
        algorithm=jwt_settings.ALGORITHM
    )
    
    return encoded_jwt

def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=jwt_settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        jwt_settings.SECRET_KEY,
        algorithm=jwt_settings.ALGORITHM
    )
    
    return encoded_jwt
```

### Token Verification
```python
def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            jwt_settings.SECRET_KEY,
            algorithms=[jwt_settings.ALGORITHM]
        )
        
        # Verify token type
        if payload.get("type") != token_type:
            raise jwt.InvalidTokenError("Invalid token type")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

## FastAPI Integration

### Security Dependencies
```python
# auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

security = HTTPBearer()

class JWTBearer(HTTPBearer):
    """Custom JWT Bearer for better error handling"""
    
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[str]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403,
                    detail="Invalid authentication scheme"
                )
            
            # Verify token
            try:
                payload = verify_token(credentials.credentials)
                return payload
            except Exception as e:
                raise HTTPException(
                    status_code=403,
                    detail=f"Invalid token: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=403,
                detail="Invalid authorization code"
            )

# Dependency for protected routes
async def get_current_user(
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(token.credentials)
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
        
        # Optional: Load user from database
        user = get_user(username=username)
        if user is None:
            raise credentials_exception
        
        return user
        
    except Exception:
        raise credentials_exception
```

### Protected Endpoints
```python
# api/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint that returns JWT tokens"""
    # Authenticate user
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token"""
    try:
        payload = verify_token(refresh_token, token_type="refresh")
        username = payload.get("sub")
        
        # Create new access token
        access_token = create_access_token(
            data={"sub": username}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )
```

### Using Protected Routes
```python
# api/endpoints/indexing.py
@router.post("/index", dependencies=[Depends(JWTBearer())])
async def index_repository(
    repo_path: str,
    current_user: Dict = Depends(get_current_user)
):
    """Protected endpoint for indexing repositories"""
    # Check permissions
    if "index:write" not in current_user.get("scopes", []):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions"
        )
    
    # Perform indexing
    result = await index_service.index_repository(
        repo_path,
        user_id=current_user["id"]
    )
    
    return result
```

## Advanced Features

### Role-Based Access Control (RBAC)
```python
# auth/permissions.py
from enum import Enum
from typing import List

class Permission(str, Enum):
    INDEX_READ = "index:read"
    INDEX_WRITE = "index:write"
    SEARCH_READ = "search:read"
    ADMIN = "admin"

class Role(str, Enum):
    VIEWER = "viewer"
    DEVELOPER = "developer"
    ADMIN = "admin"

ROLE_PERMISSIONS = {
    Role.VIEWER: [Permission.SEARCH_READ],
    Role.DEVELOPER: [
        Permission.INDEX_READ,
        Permission.INDEX_WRITE,
        Permission.SEARCH_READ
    ],
    Role.ADMIN: [
        Permission.INDEX_READ,
        Permission.INDEX_WRITE,
        Permission.SEARCH_READ,
        Permission.ADMIN
    ]
}

def has_permission(
    user_scopes: List[str],
    required_permission: Permission
) -> bool:
    """Check if user has required permission"""
    return required_permission.value in user_scopes

# Permission dependency
def require_permission(permission: Permission):
    def permission_checker(
        current_user: Dict = Depends(get_current_user)
    ):
        if not has_permission(
            current_user.get("scopes", []),
            permission
        ):
            raise HTTPException(
                status_code=403,
                detail=f"Permission required: {permission.value}"
            )
        return current_user
    return permission_checker
```

### API Key Support
```python
# auth/api_key.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(
    api_key: Optional[str] = Security(api_key_header)
):
    """Validate API key for machine-to-machine auth"""
    if not api_key:
        return None
    
    # Validate API key
    key_data = validate_api_key(api_key)
    if not key_data:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return key_data

# Combined auth (JWT or API key)
async def get_current_user_or_api_key(
    jwt_user: Optional[Dict] = Depends(get_current_user),
    api_key_data: Optional[Dict] = Depends(get_api_key)
):
    """Allow either JWT or API key authentication"""
    if jwt_user:
        return {"type": "user", "data": jwt_user}
    elif api_key_data:
        return {"type": "api_key", "data": api_key_data}
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
```

### Token Blacklisting
```python
# auth/blacklist.py
import redis
from datetime import datetime, timedelta

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def blacklist_token(token: str, expiry: datetime):
    """Add token to blacklist until expiry"""
    ttl = int((expiry - datetime.now()).total_seconds())
    if ttl > 0:
        redis_client.setex(f"blacklist:{token}", ttl, "1")

def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted"""
    return redis_client.exists(f"blacklist:{token}")

# Update verify_token to check blacklist
def verify_token_with_blacklist(token: str) -> Dict[str, Any]:
    """Verify token and check blacklist"""
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked"
        )
    
    return verify_token(token)
```

## Security Best Practices

### 1. Secure Key Management
```python
# Use environment variables
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY must be set")

# For production, use key rotation
class KeyRotation:
    def __init__(self):
        self.current_key = os.environ.get("JWT_CURRENT_KEY")
        self.previous_key = os.environ.get("JWT_PREVIOUS_KEY")
    
    def verify_with_rotation(self, token: str):
        """Try current key first, then previous"""
        try:
            return jwt.decode(token, self.current_key, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            if self.previous_key:
                return jwt.decode(token, self.previous_key, algorithms=["HS256"])
            raise
```

### 2. Token Payload Best Practices
```python
# Minimal payload
token_payload = {
    "sub": user_id,  # Subject (user identifier)
    "exp": expiry,   # Expiration time
    "iat": issued_at,  # Issued at
    "jti": str(uuid.uuid4()),  # JWT ID for tracking
}

# Don't include sensitive data
# BAD: "password", "ssn", "credit_card"
# GOOD: "user_id", "roles", "permissions"
```

### 3. HTTPS Only
```python
# Enforce HTTPS in production
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

if settings.ENVIRONMENT == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

### 4. CORS Configuration
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],  # Specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Total-Count"],
)
```

## Testing JWT Authentication

```python
# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from datetime import timedelta

def test_login(client: TestClient):
    """Test login endpoint"""
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()

def test_protected_endpoint(client: TestClient, auth_token: str):
    """Test accessing protected endpoint"""
    response = client.get(
        "/api/protected",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200

def test_expired_token(client: TestClient):
    """Test expired token handling"""
    # Create expired token
    expired_token = create_access_token(
        data={"sub": "testuser"},
        expires_delta=timedelta(seconds=-1)
    )
    
    response = client.get(
        "/api/protected",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
```

## Integration with MCP Server

### Authentication Flow
1. User provides credentials to `/auth/login`
2. Server validates credentials and returns JWT
3. Client includes JWT in Authorization header
4. Server validates JWT on each request
5. Server checks permissions for specific operations

### MCP-Specific Permissions
```python
class MCPPermission(str, Enum):
    # Indexing permissions
    INDEX_CREATE = "mcp:index:create"
    INDEX_UPDATE = "mcp:index:update"
    INDEX_DELETE = "mcp:index:delete"
    
    # Search permissions
    SEARCH_CODE = "mcp:search:code"
    SEARCH_SEMANTIC = "mcp:search:semantic"
    
    # Plugin permissions
    PLUGIN_MANAGE = "mcp:plugin:manage"
    
    # Admin permissions
    SYSTEM_CONFIG = "mcp:system:config"
    USER_MANAGE = "mcp:user:manage"
```

JWT authentication provides the security foundation for MCP Server, ensuring that only authorized users can access indexing and search capabilities while maintaining high performance and scalability.