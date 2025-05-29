# Pydantic v2 Comprehensive Documentation (2024)

## Table of Contents
1. [Basic Usage and Data Validation](#basic-usage-and-data-validation)
2. [Integration with FastAPI](#integration-with-fastapi)
3. [Custom Validators](#custom-validators)
4. [Schema Generation](#schema-generation)
5. [Performance Tips](#performance-tips)
6. [MCP Server Use Cases](#mcp-server-use-cases)

## Basic Usage and Data Validation

### Introduction
Pydantic v2 is the most widely used data validation library for Python. It's powered by type hints and features a Rust-based core for exceptional performance.

### Basic Model Definition
```python
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class User(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    is_active: bool = True
    age: Optional[int] = None
    
    # v2 uses model_config instead of Config metaclass
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
```

### Data Validation Examples
```python
# Creating a model instance
user = User(
    id=1,
    name="  John Doe  ",  # Will be stripped
    email="john@example.com",
    created_at="2024-01-15T10:30:00"  # Auto-parsed
)

# Validation errors
try:
    invalid_user = User(
        id="not-a-number",  # Will raise ValidationError
        name="Jane",
        email="invalid-email"
    )
except ValidationError as e:
    print(e.errors())
```

### Built-in Validation Features
- Automatic type coercion
- Required vs optional fields
- Default values
- Regex validation
- Email validation
- String manipulation
- Enum support

## Integration with FastAPI

### Basic FastAPI Integration
```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

app = FastAPI()

# Request/Response Models
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    
    model_config = ConfigDict(from_attributes=True)  # For ORM integration

# Endpoint Example
@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate):
    # Process user creation
    return UserResponse(id=1, name=user.name, email=user.email)

# List endpoint with query parameters
@app.get("/users/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = Field(default=100, le=100),
    is_active: Optional[bool] = None
):
    # Return filtered users
    return []
```

### Advanced FastAPI Patterns

#### 1. Dependency Injection for Validation
```python
from fastapi import Depends

async def validate_user_exists(user_id: int) -> User:
    # Check database
    user = await get_user_from_db(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/users/{user_id}")
async def get_user(user: User = Depends(validate_user_exists)):
    return user
```

#### 2. Custom Exception Handling
```python
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()}
    )
```

#### 3. Project Structure Best Practices
```
fastapi-project/
├── src/
│   ├── auth/
│   │   ├── router.py
│   │   ├── schemas.py      # Pydantic models
│   │   ├── models.py       # Database models
│   │   ├── dependencies.py
│   │   ├── service.py
│   │   └── exceptions.py
│   ├── users/
│   │   ├── router.py
│   │   └── schemas.py
│   └── common/
│       └── schemas.py      # Shared models
```

## Custom Validators

### Field Validators
```python
from pydantic import BaseModel, field_validator, ValidationInfo
from typing import List

class Product(BaseModel):
    name: str
    price: float
    tags: List[str]
    
    @field_validator('price')
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Price must be positive')
        return v
    
    @field_validator('tags')
    @classmethod
    def tags_must_be_unique(cls, v: List[str]) -> List[str]:
        if len(v) != len(set(v)):
            raise ValueError('Tags must be unique')
        return v
```

### Model Validators
```python
from pydantic import model_validator

class UserRegistration(BaseModel):
    username: str
    password: str
    confirm_password: str
    
    @model_validator(mode='after')
    def passwords_match(self) -> 'UserRegistration':
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self
```

### Accessing Other Fields in Validators
```python
class Order(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    total_price: float
    
    @field_validator('total_price', mode='after')
    @classmethod
    def validate_total(cls, v: float, info: ValidationInfo) -> float:
        data = info.data
        expected = data.get('quantity', 0) * data.get('unit_price', 0)
        if abs(v - expected) > 0.01:  # Allow for floating point errors
            raise ValueError(f'Total should be {expected}, got {v}')
        return v
```

### Custom Type Validators
```python
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from typing import Any

class PositiveInt:
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.chain_schema([
            core_schema.int_schema(),
            core_schema.no_info_plain_validator_function(cls.validate)
        ])
    
    @classmethod
    def validate(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Must be positive')
        return v

class Model(BaseModel):
    count: PositiveInt
```

## Schema Generation

### JSON Schema Generation
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class StatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"

class UserProfile(BaseModel):
    id: int = Field(..., description="User ID", example=123)
    username: str = Field(..., min_length=3, max_length=20)
    email: str = Field(..., description="User email address")
    status: StatusEnum = Field(default=StatusEnum.ACTIVE)
    tags: Optional[List[str]] = Field(default=None, max_items=10)
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 123,
                    "username": "johndoe",
                    "email": "john@example.com",
                    "status": "active",
                    "tags": ["developer", "python"]
                }
            ]
        }
    )

# Generate JSON Schema
schema = UserProfile.model_json_schema()
print(json.dumps(schema, indent=2))
```

### OpenAPI Schema Customization
```python
class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "title": "Standard API Response",
            "description": "Standard response format for all API endpoints"
        }
    )
```

### TypeAdapter for Standalone Validation
```python
from pydantic import TypeAdapter
from typing import List, Dict

# Validate without creating a model
list_adapter = TypeAdapter(List[int])
validated_list = list_adapter.validate_python([1, "2", 3.0])  # [1, 2, 3]

# Complex type validation
ComplexType = Dict[str, List[int]]
adapter = TypeAdapter(ComplexType)
result = adapter.validate_python({"numbers": [1, 2, 3]})
```

## Performance Tips

### 1. Reuse TypeAdapter Instances
```python
# Bad - Creates new adapter each time
def validate_data(data):
    adapter = TypeAdapter(List[int])
    return adapter.validate_python(data)

# Good - Reuse adapter
LIST_ADAPTER = TypeAdapter(List[int])

def validate_data(data):
    return LIST_ADAPTER.validate_python(data)
```

### 2. Use Specific Types
```python
# Less performant
from typing import Sequence, Mapping

class Model(BaseModel):
    items: Sequence[int]  # Generic sequence
    data: Mapping[str, str]  # Generic mapping

# More performant
class Model(BaseModel):
    items: List[int]  # Specific list type
    data: Dict[str, str]  # Specific dict type
```

### 3. FailFast for Sequences (v2.8+)
```python
from pydantic import BaseModel, FailFast
from typing import List, Annotated

class Model(BaseModel):
    # Stops validation on first error in sequence
    items: Annotated[List[int], FailFast()]
```

### 4. Defer Validation for Nested Models
```python
class NestedModel(BaseModel):
    value: str

class MainModel(BaseModel):
    nested: NestedModel
    
    model_config = ConfigDict(
        defer_build=True  # v2.10+ - Defer nested model validation
    )
```

### 5. Use Strict Mode
```python
class StrictModel(BaseModel):
    count: int
    
    model_config = ConfigDict(
        strict=True  # No type coercion
    )

# This will fail with strict=True
# StrictModel(count="123")  # ValidationError
```

### 6. Optimize Serialization
```python
class OptimizedModel(BaseModel):
    name: str
    
    model_config = ConfigDict(
        # v2.7+ - Enable duck-typing serialization
        serialize_as_any=True,
        # v2.11+ - Serialize by alias
        serialize_by_alias=True
    )
```

### 7. Performance Measurement
```python
import time
from pydantic import BaseModel

class PerformanceTest(BaseModel):
    data: List[Dict[str, Any]]

# Measure validation time
start = time.time()
for _ in range(10000):
    PerformanceTest(data=[{"key": "value"} for _ in range(10)])
end = time.time()
print(f"Validation time: {end - start:.4f}s")
```

## MCP Server Use Cases

### 1. PydanticAI as MCP Client
```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerHTTP

# Connect to MCP server via HTTP
server = MCPServerHTTP(url='http://localhost:3001/sse')
agent = Agent('openai:gpt-4o', mcp_servers=[server])

async def main():
    async with agent.run_mcp_servers():
        # Agent can now use MCP server tools
        result = await agent.run('Analyze the latest logs for errors')
        print(result.output)
```

### 2. PydanticAI as MCP Server
```python
from mcp.server.fastmcp import FastMCP
from pydantic_ai import Agent
from pydantic import BaseModel

# Define server
server = FastMCP('Analytics MCP Server')

# Create specialized agent
analytics_agent = Agent(
    'anthropic:claude-3-5-haiku-latest',
    system_prompt='You are a data analytics expert'
)

# Define input/output models
class QueryInput(BaseModel):
    query: str
    dataset: str
    filters: Optional[Dict[str, Any]] = None

class QueryResult(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    summary: str

@server.tool()
async def analyze_data(input: QueryInput) -> QueryResult:
    """Analyze data based on natural language query"""
    # Use agent to interpret query
    interpretation = await analytics_agent.run(
        f"Convert this query to SQL: {input.query} for dataset {input.dataset}"
    )
    
    # Execute analysis (pseudo-code)
    data = await execute_query(interpretation.output)
    
    # Generate summary
    summary = await analytics_agent.run(
        f"Summarize these results: {data[:5]}"  # First 5 rows
    )
    
    return QueryResult(
        success=True,
        data=data,
        summary=summary.output
    )

if __name__ == '__main__':
    server.run()
```

### 3. Real-World MCP Use Cases

#### Log Analysis Integration
```python
# Logfire MCP Server Integration
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerHTTP

logfire_server = MCPServerHTTP(url='http://logfire-mcp:3000/sse')
debug_agent = Agent(
    'openai:gpt-4o',
    mcp_servers=[logfire_server],
    system_prompt="You are a debugging assistant"
)

async def debug_error(error_message: str):
    async with debug_agent.run_mcp_servers():
        result = await debug_agent.run(
            f"Search logs for errors related to: {error_message}. "
            "Analyze the stack traces and suggest fixes."
        )
        return result.output
```

#### Code Execution Sandbox
```python
# Python Sandbox MCP Server
from pydantic_ai.mcp import MCPServerStdio

python_sandbox = MCPServerStdio(
    'deno',
    args=[
        'run', '-N', '-R=node_modules',
        'jsr:@pydantic/mcp-run-python', 'stdio'
    ]
)

code_agent = Agent(
    'anthropic:claude-3-5-sonnet',
    mcp_servers=[python_sandbox],
    system_prompt="You can execute Python code safely"
)

async def safe_code_execution(code: str):
    async with code_agent.run_mcp_servers():
        result = await code_agent.run(
            f"Execute this Python code and explain the output: {code}"
        )
        return result.output
```

### 4. MCP Server Configuration with Pydantic
```python
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import List, Optional

class MCPServerConfig(BaseSettings):
    """Configuration for MCP Server using Pydantic"""
    host: str = Field(default="localhost", env="MCP_HOST")
    port: int = Field(default=3000, env="MCP_PORT")
    auth_token: Optional[str] = Field(default=None, env="MCP_AUTH_TOKEN")
    allowed_tools: List[str] = Field(
        default_factory=lambda: ["search", "analyze"],
        env="MCP_ALLOWED_TOOLS"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Usage
config = MCPServerConfig()
```

## Best Practices Summary

1. **Model Organization**: Keep models modular and domain-specific
2. **Validation Strategy**: Use field validators for simple checks, model validators for cross-field validation
3. **Performance**: Reuse validators, use specific types, enable strict mode when appropriate
4. **FastAPI Integration**: Leverage dependencies for complex validation, use proper exception handling
5. **Schema Generation**: Provide examples and descriptions for better API documentation
6. **MCP Integration**: Use PydanticAI for AI-powered tool integration and context-aware applications

## Conclusion

Pydantic v2 represents a significant evolution in Python data validation, offering:
- **Performance**: Rust-based core provides exceptional speed
- **Flexibility**: Rich validation and serialization options
- **Integration**: Seamless FastAPI and MCP support
- **Developer Experience**: Type hints and IDE integration

The combination of these features makes Pydantic v2 an essential tool for modern Python applications, particularly in API development and AI-powered systems.