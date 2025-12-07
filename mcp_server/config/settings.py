"""
Comprehensive settings management for production deployments.
"""

import secrets
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator, validator

from .environment import Environment, get_env_var, get_environment, is_production


class DatabaseSettings(BaseModel):
    """Database configuration settings."""

    # Connection settings
    url: str = Field(default="sqlite:///./code_index.db", description="Database connection URL")
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=1, le=300)
    pool_recycle: int = Field(default=3600, ge=300, le=86400)

    # SQLite specific settings
    sqlite_timeout: int = Field(default=20, ge=1, le=60)
    sqlite_check_same_thread: bool = Field(default=False)

    # Migration settings
    auto_migrate: bool = Field(default=True)
    migration_timeout: int = Field(default=300, ge=30, le=1800)

    @classmethod
    def from_environment(cls) -> "DatabaseSettings":
        """Create database settings from environment variables."""
        env = get_environment()

        if env == Environment.PRODUCTION:
            # Production requires explicit database URL
            db_url = get_env_var("DATABASE_URL", required=True)
            return cls(
                url=db_url,
                pool_size=int(get_env_var("DB_POOL_SIZE", "20")),
                max_overflow=int(get_env_var("DB_MAX_OVERFLOW", "40")),
                pool_timeout=int(get_env_var("DB_POOL_TIMEOUT", "30")),
                pool_recycle=int(get_env_var("DB_POOL_RECYCLE", "3600")),
                auto_migrate=get_env_var("DB_AUTO_MIGRATE", "false").lower() == "true",
            )

        elif env == Environment.STAGING:
            # Staging can use PostgreSQL or SQLite
            db_url = get_env_var(
                "DATABASE_URL", "postgresql://mcp_user:mcp_pass@localhost/mcp_staging"
            )
            return cls(
                url=db_url,
                pool_size=int(get_env_var("DB_POOL_SIZE", "10")),
                auto_migrate=True,
            )

        elif env == Environment.TESTING:
            # Testing uses in-memory SQLite
            return cls(
                url="sqlite:///:memory:",
                auto_migrate=True,
                sqlite_check_same_thread=False,
            )

        else:  # Development
            # Development uses local SQLite file
            return cls(
                url=get_env_var("DATABASE_URL", "sqlite:///./dev_code_index.db"),
                auto_migrate=True,
            )

    @validator("url")
    def validate_database_url(cls, v):
        """Validate database URL format."""
        try:
            parsed = urlparse(v)
            if not parsed.scheme:
                raise ValueError(
                    "Database URL must include scheme (sqlite://, postgresql://, etc.)"
                )
            return v
        except Exception as e:
            raise ValueError(f"Invalid database URL: {e}")


class SecuritySettings(BaseModel):
    """Security configuration settings."""

    # JWT Configuration
    jwt_secret_key: str = Field(min_length=32, description="JWT signing secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)

    # Password Policy
    password_min_length: int = Field(default=8, ge=6, le=128)
    password_require_uppercase: bool = Field(default=True)
    password_require_lowercase: bool = Field(default=True)
    password_require_numbers: bool = Field(default=True)
    password_require_special: bool = Field(default=True)

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests: int = Field(default=100, ge=1, le=10000)
    rate_limit_window: int = Field(default=3600, ge=60, le=86400)

    # CORS Settings
    cors_enabled: bool = Field(default=True)
    cors_allowed_origins: List[str] = Field(default_factory=lambda: ["*"])
    cors_allowed_methods: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE"]
    )
    cors_allowed_headers: List[str] = Field(default_factory=lambda: ["*"])

    # Security Headers
    security_headers_enabled: bool = Field(default=True)
    hsts_max_age: int = Field(default=31536000, ge=0)

    # Admin User Settings
    default_admin_username: str = Field(default="admin")
    default_admin_email: str = Field(default="admin@localhost")

    @classmethod
    def from_environment(cls) -> "SecuritySettings":
        """Create security settings from environment variables."""
        env = get_environment()

        # Generate secure JWT secret if not provided
        jwt_secret = get_env_var("JWT_SECRET_KEY")
        if not jwt_secret:
            if is_production():
                raise ValueError("JWT_SECRET_KEY must be explicitly set in production environment")
            # Generate a secure secret for non-production
            jwt_secret = secrets.token_urlsafe(32)

        if env == Environment.PRODUCTION:
            return cls(
                jwt_secret_key=jwt_secret,
                access_token_expire_minutes=int(get_env_var("JWT_ACCESS_EXPIRE_MINUTES", "15")),
                refresh_token_expire_days=int(get_env_var("JWT_REFRESH_EXPIRE_DAYS", "7")),
                cors_allowed_origins=get_env_var("CORS_ALLOWED_ORIGINS", "").split(","),
                rate_limit_requests=int(get_env_var("RATE_LIMIT_REQUESTS", "60")),
                rate_limit_window=int(get_env_var("RATE_LIMIT_WINDOW", "3600")),
                default_admin_username=get_env_var("DEFAULT_ADMIN_USERNAME", "admin"),
                default_admin_email=get_env_var("DEFAULT_ADMIN_EMAIL", required=True),
            )

        elif env == Environment.STAGING:
            return cls(
                jwt_secret_key=jwt_secret,
                access_token_expire_minutes=int(get_env_var("JWT_ACCESS_EXPIRE_MINUTES", "30")),
                cors_allowed_origins=get_env_var(
                    "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
                ).split(","),
                rate_limit_requests=int(get_env_var("RATE_LIMIT_REQUESTS", "100")),
            )

        elif env == Environment.TESTING:
            return cls(
                jwt_secret_key="test-secret-key-32-characters-long",
                access_token_expire_minutes=5,
                rate_limit_enabled=False,
                cors_enabled=True,
            )

        else:  # Development
            return cls(
                jwt_secret_key=jwt_secret,
                access_token_expire_minutes=int(get_env_var("JWT_ACCESS_EXPIRE_MINUTES", "60")),
                rate_limit_requests=int(get_env_var("RATE_LIMIT_REQUESTS", "1000")),
                cors_allowed_origins=["*"],
            )


class CacheSettings(BaseModel):
    """Cache configuration settings."""

    # Redis Configuration
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    redis_pool_size: int = Field(default=10, ge=1, le=100)
    redis_timeout: int = Field(default=30, ge=1, le=300)

    # Cache TTL Settings
    default_ttl: int = Field(default=3600, ge=60, le=86400)
    symbol_cache_ttl: int = Field(default=1800, ge=60, le=86400)
    search_cache_ttl: int = Field(default=600, ge=60, le=3600)

    # Memory Cache Settings
    memory_cache_size: int = Field(default=1000, ge=100, le=100000)

    @classmethod
    def from_environment(cls) -> "CacheSettings":
        """Create cache settings from environment variables."""
        env = get_environment()

        if env == Environment.PRODUCTION:
            # Production requires Redis
            redis_url = get_env_var("REDIS_URL", required=True)
            return cls(
                redis_url=redis_url,
                redis_pool_size=int(get_env_var("REDIS_POOL_SIZE", "20")),
                default_ttl=int(get_env_var("CACHE_DEFAULT_TTL", "3600")),
                symbol_cache_ttl=int(get_env_var("CACHE_SYMBOL_TTL", "1800")),
                search_cache_ttl=int(get_env_var("CACHE_SEARCH_TTL", "600")),
            )

        elif env == Environment.STAGING:
            # Staging can use Redis if available
            redis_url = get_env_var("REDIS_URL", "redis://localhost:6379")
            return cls(
                redis_url=redis_url,
                default_ttl=int(get_env_var("CACHE_DEFAULT_TTL", "1800")),
            )

        else:  # Development and Testing
            # Use memory cache for simplicity
            return cls(
                redis_url=get_env_var("REDIS_URL"),  # Optional in dev
                memory_cache_size=int(get_env_var("MEMORY_CACHE_SIZE", "1000")),
            )


class MetricsSettings(BaseModel):
    """Metrics and monitoring configuration."""

    # Prometheus Settings
    prometheus_enabled: bool = Field(default=True)
    prometheus_port: int = Field(default=8001, ge=1024, le=65535)
    prometheus_path: str = Field(default="/metrics")

    # Health Check Settings
    health_check_enabled: bool = Field(default=True)
    health_check_interval: int = Field(default=30, ge=5, le=300)

    # Performance Monitoring
    performance_monitoring_enabled: bool = Field(default=True)
    slow_query_threshold: float = Field(default=1.0, ge=0.1, le=60.0)

    @classmethod
    def from_environment(cls) -> "MetricsSettings":
        """Create metrics settings from environment variables."""
        return cls(
            prometheus_enabled=get_env_var("PROMETHEUS_ENABLED", "true").lower() == "true",
            prometheus_port=int(get_env_var("PROMETHEUS_PORT", "8001")),
            health_check_enabled=get_env_var("HEALTH_CHECK_ENABLED", "true").lower() == "true",
            performance_monitoring_enabled=get_env_var(
                "PERFORMANCE_MONITORING_ENABLED", "true"
            ).lower()
            == "true",
            slow_query_threshold=float(get_env_var("SLOW_QUERY_THRESHOLD", "1.0")),
        )


class LoggingSettings(BaseModel):
    """Logging configuration settings."""

    # Log Level
    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # Log Format
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    json_format: bool = Field(default=False, description="Use JSON structured logging")

    # Log Output
    log_file: Optional[str] = Field(default=None, description="Log file path")
    log_rotation: bool = Field(default=True)
    log_max_size: str = Field(default="100MB")
    log_backup_count: int = Field(default=5, ge=1, le=20)

    # Request Logging
    request_logging_enabled: bool = Field(default=True)
    log_request_body: bool = Field(default=False)
    log_response_body: bool = Field(default=False)

    @classmethod
    def from_environment(cls) -> "LoggingSettings":
        """Create logging settings from environment variables."""
        env = get_environment()

        if env == Environment.PRODUCTION:
            return cls(
                level=get_env_var("LOG_LEVEL", "INFO"),
                json_format=True,  # Production uses structured logging
                log_file=get_env_var("LOG_FILE", "PathUtils.get_log_path()/app.log"),
                log_request_body=False,  # Don't log bodies in production
                log_response_body=False,
            )

        elif env == Environment.TESTING:
            return cls(
                level=get_env_var("LOG_LEVEL", "WARNING"),
                json_format=False,
                log_file=None,  # No file logging in tests
                request_logging_enabled=False,
            )

        else:  # Development and Staging
            return cls(
                level=get_env_var("LOG_LEVEL", "DEBUG"),
                json_format=get_env_var("LOG_JSON_FORMAT", "false").lower() == "true",
                log_file=get_env_var("LOG_FILE"),
                log_request_body=get_env_var("LOG_REQUEST_BODY", "false").lower() == "true",
            )


class RerankingSettings(BaseModel):
    """Reranking configuration for search result optimization."""

    # Enable/disable reranking
    enabled: bool = Field(default=False, description="Enable search result reranking")

    # Reranker type selection
    reranker_type: str = Field(
        default="hybrid",
        pattern="^(cohere|cross-encoder|tfidf|hybrid)$",
        description="Type of reranker to use",
    )

    # Cohere settings
    cohere_api_key: Optional[str] = Field(default=None, description="Cohere API key")
    cohere_model: str = Field(default="rerank-english-v2.0", description="Cohere reranking model")

    # Cross-encoder settings
    cross_encoder_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Cross-encoder model for local reranking",
    )
    cross_encoder_device: str = Field(default="cpu", pattern="^(cpu|cuda|mps)$")

    # Hybrid reranker settings
    hybrid_primary_type: str = Field(
        default="cohere", description="Primary reranker for hybrid mode"
    )
    hybrid_fallback_type: str = Field(
        default="tfidf", description="Fallback reranker for hybrid mode"
    )
    hybrid_primary_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    hybrid_fallback_weight: float = Field(default=0.3, ge=0.0, le=1.0)

    # General settings
    top_k: Optional[int] = Field(
        default=None, ge=1, le=100, description="Number of top results to rerank"
    )
    cache_ttl: int = Field(default=3600, ge=0, le=86400, description="Cache TTL in seconds")

    # Performance settings
    batch_size: int = Field(default=32, ge=1, le=128, description="Batch size for reranking")
    timeout: float = Field(default=5.0, ge=0.1, le=30.0, description="Reranking timeout in seconds")

    @validator("hybrid_primary_weight", "hybrid_fallback_weight")
    def validate_weights(cls, v, values):
        """Ensure weights sum to 1.0 for hybrid mode."""
        if "hybrid_primary_weight" in values and "hybrid_fallback_weight" in values:
            total = values["hybrid_primary_weight"] + values["hybrid_fallback_weight"]
            if abs(total - 1.0) > 0.001:  # Allow small floating point errors
                raise ValueError(f"Hybrid weights must sum to 1.0, got {total}")
        return v

    @classmethod
    def from_environment(cls) -> "RerankingSettings":
        """Create reranking settings from environment variables."""
        return cls(
            enabled=get_env_var("RERANKING_ENABLED", "false").lower() == "true",
            reranker_type=get_env_var("RERANKER_TYPE", "hybrid"),
            cohere_api_key=get_env_var("COHERE_API_KEY"),
            cohere_model=get_env_var("COHERE_MODEL", "rerank-english-v2.0"),
            cross_encoder_model=get_env_var(
                "CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
            ),
            cross_encoder_device=get_env_var("CROSS_ENCODER_DEVICE", "cpu"),
            hybrid_primary_type=get_env_var("HYBRID_PRIMARY_TYPE", "cohere"),
            hybrid_fallback_type=get_env_var("HYBRID_FALLBACK_TYPE", "tfidf"),
            top_k=int(get_env_var("RERANK_TOP_K", "0")) or None,
            cache_ttl=int(get_env_var("RERANK_CACHE_TTL", "3600")),
        )


class Settings(BaseModel):
    """Main application settings."""

    # Application Info
    app_name: str = Field(default="MCP Server")
    app_version: str = Field(default="1.0.0")
    app_description: str = Field(default="Code Index MCP Server")

    # Server Settings
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1024, le=65535)
    workers: int = Field(default=1, ge=1, le=16)

    # Environment
    environment: Environment = Field(default_factory=get_environment)
    debug: bool = Field(default=False)

    # Component Settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings.from_environment)
    security: SecuritySettings = Field(default_factory=SecuritySettings.from_environment)
    cache: CacheSettings = Field(default_factory=CacheSettings.from_environment)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings.from_environment)
    logging: LoggingSettings = Field(default_factory=LoggingSettings.from_environment)
    reranking: RerankingSettings = Field(default_factory=RerankingSettings.from_environment)

    # Feature Flags
    dynamic_plugin_loading: bool = Field(default=True)
    semantic_search_enabled: bool = Field(default=False)

    # Semantic Search Configuration
    voyage_api_key: Optional[str] = Field(default=None)
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_grpc_port: int = Field(default=6334)
    semantic_embedding_model: str = Field(default="voyage-code-3")
    semantic_collection_name: str = Field(default="code-embeddings")

    @classmethod
    def from_environment(cls) -> "Settings":
        """Create settings from environment variables."""
        env = get_environment()

        # Base settings
        settings = cls(
            app_name=get_env_var("APP_NAME", "MCP Server"),
            app_version=get_env_var("APP_VERSION", "1.0.0"),
            host=get_env_var("HOST", "0.0.0.0"),
            port=int(get_env_var("PORT", "8000")),
            environment=env,
            debug=get_env_var("DEBUG", "false").lower() == "true",
            semantic_search_enabled=get_env_var("SEMANTIC_SEARCH_ENABLED", "true").lower()
            == "true",
            voyage_api_key=get_env_var("VOYAGE_AI_API_KEY"),
            qdrant_host=get_env_var("QDRANT_HOST", "localhost"),
            qdrant_port=int(get_env_var("QDRANT_PORT", "6333")),
            qdrant_grpc_port=int(get_env_var("QDRANT_GRPC_PORT", "6334")),
            semantic_embedding_model=get_env_var("SEMANTIC_EMBEDDING_MODEL", "voyage-code-3"),
            semantic_collection_name=get_env_var("SEMANTIC_COLLECTION_NAME", "code-embeddings"),
        )

        # Environment-specific overrides
        if env == Environment.PRODUCTION:
            settings.debug = False
            settings.workers = int(get_env_var("WORKERS", "4"))
        elif env == Environment.DEVELOPMENT:
            settings.debug = get_env_var("DEBUG", "true").lower() == "true"
            settings.workers = 1

        return settings

    @model_validator(mode="after")
    def validate_production_settings(self):
        """Validate settings for production environment."""
        if self.environment == Environment.PRODUCTION:
            # Production validation
            if self.debug:
                raise ValueError("Debug mode must be disabled in production")

            if self.security and len(self.security.jwt_secret_key) < 32:
                raise ValueError("JWT secret key must be at least 32 characters in production")

        return self

    def get_database_url(self) -> str:
        """Get the database connection URL."""
        return self.database.url

    def is_redis_enabled(self) -> bool:
        """Check if Redis caching is enabled."""
        return self.cache.redis_url is not None

    def is_prometheus_enabled(self) -> bool:
        """Check if Prometheus metrics are enabled."""
        return self.metrics.prometheus_enabled


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings singleton.

    Returns:
        Settings: Application settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings.from_environment()
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment variables.

    Returns:
        Settings: New settings instance
    """
    global _settings
    _settings = Settings.from_environment()
    return _settings
