from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging
import os
import time
from .dispatcher import Dispatcher
from .plugin_base import SymbolDef, SearchResult
from .storage.sqlite_store import SQLiteStore
from .watcher import FileWatcher
from .core.logging import setup_logging
from .plugin_system import PluginManager, PluginSystemConfig
from .security import (
    SecurityConfig, AuthManager, SecurityMiddlewareStack,
    AuthCredentials, User, UserRole, Permission,
    get_current_user, get_current_active_user, require_permission, require_role
)
from .metrics import (
    get_metrics_collector, get_health_checker, HealthStatus
)
from .metrics.middleware import setup_metrics_middleware, get_business_metrics
from .cache import (
    CacheManagerFactory, CacheConfig, CacheBackendType, 
    QueryResultCache, QueryCacheConfig, QueryType
)

# Set up logging
setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Server", description="Code Index MCP Server with Security, Metrics, and Health Checks")
dispatcher: Dispatcher | None = None
sqlite_store: SQLiteStore | None = None
file_watcher: FileWatcher | None = None
plugin_manager: PluginManager | None = None
auth_manager: AuthManager | None = None
security_config: SecurityConfig | None = None
cache_manager = None
query_cache: QueryResultCache | None = None

# Initialize metrics and health checking
metrics_collector = get_metrics_collector()
health_checker = get_health_checker()
business_metrics = get_business_metrics()

# Setup metrics middleware
setup_metrics_middleware(app, enable_detailed_metrics=True)

@app.on_event("startup")
async def startup_event():
    """Initialize the dispatcher and register plugins on startup."""
    global dispatcher, sqlite_store, file_watcher, plugin_manager, auth_manager, security_config, cache_manager, query_cache
    
    try:
        # Initialize security configuration
        logger.info("Initializing security configuration...")
        security_config = SecurityConfig(
            jwt_secret_key=os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production-min-32-chars"),
            jwt_algorithm="HS256",
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
            password_min_length=int(os.getenv("PASSWORD_MIN_LENGTH", "8")),
            max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
            lockout_duration_minutes=int(os.getenv("LOCKOUT_DURATION_MINUTES", "15")),
            rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
            rate_limit_window_minutes=int(os.getenv("RATE_LIMIT_WINDOW_MINUTES", "1")),
            cors_origins=os.getenv("CORS_ORIGINS", "*").split(","),
            cors_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            cors_headers=["*"]
        )
        
        # Initialize authentication manager
        logger.info("Initializing authentication manager...")
        auth_manager = AuthManager(security_config)
        
        # Create default admin user if it doesn't exist
        admin_user = await auth_manager.get_user_by_username("admin")
        if not admin_user:
            admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123!")
            logger.info("Creating default admin user...")
            await auth_manager.create_user(
                username="admin",
                password=admin_password,
                email=os.getenv("DEFAULT_ADMIN_EMAIL", "admin@localhost"),
                role=UserRole.ADMIN
            )
            logger.info("Default admin user created")
        
        # Set up security middleware
        logger.info("Setting up security middleware...")
        security_middleware = SecurityMiddlewareStack(app, security_config, auth_manager)
        security_middleware.setup_middleware()
        logger.info("Security middleware configured successfully")
        
        # Initialize cache system
        logger.info("Initializing cache system...")
        cache_backend_type = os.getenv("CACHE_BACKEND", "memory").lower()
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        if cache_backend_type == "redis":
            try:
                cache_manager = CacheManagerFactory.create_redis_cache(
                    redis_url=redis_url,
                    default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
                )
                logger.info("Using Redis cache backend")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache, falling back to memory: {e}")
                cache_manager = CacheManagerFactory.create_memory_cache()
        elif cache_backend_type == "hybrid":
            try:
                cache_manager = CacheManagerFactory.create_hybrid_cache(
                    redis_url=redis_url,
                    max_entries=int(os.getenv("CACHE_MAX_ENTRIES", "1000")),
                    max_memory_mb=int(os.getenv("CACHE_MAX_MEMORY_MB", "100")),
                    default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
                )
                logger.info("Using hybrid cache backend")
            except Exception as e:
                logger.warning(f"Failed to initialize hybrid cache, falling back to memory: {e}")
                cache_manager = CacheManagerFactory.create_memory_cache()
        else:
            cache_manager = CacheManagerFactory.create_memory_cache(
                max_entries=int(os.getenv("CACHE_MAX_ENTRIES", "1000")),
                max_memory_mb=int(os.getenv("CACHE_MAX_MEMORY_MB", "100")),
                default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
            )
            logger.info("Using memory cache backend")
        
        await cache_manager.initialize()
        
        # Initialize query result cache
        query_cache_config = QueryCacheConfig(
            enabled=os.getenv("QUERY_CACHE_ENABLED", "true").lower() == "true",
            default_ttl=int(os.getenv("QUERY_CACHE_DEFAULT_TTL", "300")),
            symbol_lookup_ttl=int(os.getenv("QUERY_CACHE_SYMBOL_TTL", "1800")),
            search_ttl=int(os.getenv("QUERY_CACHE_SEARCH_TTL", "600")),
            semantic_search_ttl=int(os.getenv("QUERY_CACHE_SEMANTIC_TTL", "3600"))
        )
        query_cache = QueryResultCache(cache_manager, query_cache_config)
        logger.info("Query result cache initialized successfully")
        # Initialize SQLite store
        logger.info("Initializing SQLite store...")
        sqlite_store = SQLiteStore("code_index.db")
        logger.info("SQLite store initialized successfully")
        
        # Initialize plugin manager with SQLite store
        logger.info("Initializing plugin system...")
        config_path = Path("plugins.yaml")
        plugin_manager = PluginManager(sqlite_store=sqlite_store)
        
        # Load plugins from configuration using safe method for better error handling
        logger.info("Loading plugins...")
        load_result = plugin_manager.load_plugins_safe(config_path if config_path.exists() else None)
        
        if not load_result.success:
            logger.error(f"Plugin loading failed: {load_result.error.message}")
            logger.error(f"Error details: {load_result.error.details}")
            # Continue with any successfully loaded plugins
        else:
            logger.info(f"Plugin loading completed: {load_result.metadata}")
        
        # Get active plugin instances
        active_plugins = plugin_manager.get_active_plugins()
        plugin_instances = list(active_plugins.values())
        
        logger.info(f"Loaded {len(plugin_instances)} active plugins")
        
        # Create a new Dispatcher instance with the loaded plugins
        logger.info("Creating dispatcher...")
        dispatcher = Dispatcher(plugin_instances)
        logger.info(f"Dispatcher created with {len(plugin_instances)} plugins")
        
        # Initialize file watcher with dispatcher and query cache
        logger.info("Starting file watcher...")
        file_watcher = FileWatcher(Path("."), dispatcher, query_cache)
        file_watcher.start()
        logger.info("File watcher started for current directory with cache invalidation")
        
        # Store in app.state for potential future use
        app.state.dispatcher = dispatcher
        app.state.sqlite_store = sqlite_store
        app.state.file_watcher = file_watcher
        app.state.plugin_manager = plugin_manager
        app.state.auth_manager = auth_manager
        app.state.security_config = security_config
        app.state.cache_manager = cache_manager
        app.state.query_cache = query_cache
        app.state.metrics_collector = metrics_collector
        app.state.health_checker = health_checker
        app.state.business_metrics = business_metrics
        
        # Register health checks for system components
        logger.info("Registering component health checks...")
        health_checker.register_health_check(
            "database", 
            health_checker.create_database_health_check("code_index.db")
        )
        health_checker.register_health_check(
            "plugins",
            health_checker.create_plugin_health_check(plugin_manager)
        )
        
        # Update system metrics
        business_metrics.update_system_metrics(
            active_plugins=len(plugin_instances),
            indexed_files=0,  # Will be updated as files are indexed
            database_size=0,  # Will be updated periodically
            memory_usage=0    # Will be updated by middleware
        )
        
        # Log loaded plugins with detailed status
        plugin_status = plugin_manager.get_detailed_plugin_status()
        for name, status in plugin_status.items():
            basic_info = status['basic_info']
            runtime_info = status['runtime_info']
            logger.info(f"Plugin '{name}': {runtime_info['state']} (v{basic_info['version']}, language: {basic_info['language']}, enabled: {runtime_info['enabled']})")
            if runtime_info.get('error'):
                logger.warning(f"Plugin '{name}' has error: {runtime_info['error']}")
        
        logger.info("MCP Server initialized successfully with dynamic plugin system, SQLite persistence, and file watcher")
    except Exception as e:
        logger.error(f"Failed to initialize MCP Server: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global file_watcher, plugin_manager, cache_manager
    
    if file_watcher:
        try:
            file_watcher.stop()
            logger.info("File watcher stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping file watcher: {e}", exc_info=True)
    
    if plugin_manager:
        try:
            shutdown_result = plugin_manager.shutdown_safe()
            if shutdown_result.success:
                logger.info("Plugin manager shutdown successfully")
            else:
                logger.error(f"Plugin manager shutdown failed: {shutdown_result.error.message}")
                logger.error(f"Shutdown error details: {shutdown_result.error.details}")
        except Exception as e:
            logger.error(f"Error shutting down plugin manager: {e}", exc_info=True)
    
    if cache_manager:
        try:
            await cache_manager.shutdown()
            logger.info("Cache manager shutdown successfully")
        except Exception as e:
            logger.error(f"Error shutting down cache manager: {e}", exc_info=True)

# Authentication endpoints

@app.post("/api/v1/auth/login")
async def login(credentials: AuthCredentials) -> Dict[str, Any]:
    """User login endpoint."""
    if auth_manager is None:
        raise HTTPException(503, "Authentication service not ready")
    
    try:
        user = await auth_manager.authenticate_user(credentials)
        if not user:
            raise HTTPException(401, "Invalid credentials")
        
        access_token = await auth_manager.create_access_token(user)
        refresh_token = await auth_manager.create_refresh_token(user)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": security_config.access_token_expire_minutes * 60,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role.value,
                "permissions": [p.value for p in user.permissions]
            }
        }
    except Exception as e:
        logger.error(f"Login failed for user '{credentials.username}': {e}")
        raise HTTPException(401, "Authentication failed")

@app.post("/api/v1/auth/refresh")
async def refresh_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh access token."""
    if auth_manager is None:
        raise HTTPException(503, "Authentication service not ready")
    
    try:
        new_access_token = await auth_manager.refresh_access_token(refresh_token)
        if not new_access_token:
            raise HTTPException(401, "Invalid refresh token")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": security_config.access_token_expire_minutes * 60
        }
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(401, "Token refresh failed")

@app.post("/api/v1/auth/logout")
async def logout(
    refresh_token: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """User logout endpoint."""
    if auth_manager is None:
        raise HTTPException(503, "Authentication service not ready")
    
    try:
        if refresh_token:
            await auth_manager.revoke_refresh_token(refresh_token)
        
        await auth_manager._log_security_event(
            "user_logout",
            user_id=current_user.id,
            username=current_user.username
        )
        
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(500, "Logout failed")

@app.get("/api/v1/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get current user information."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value,
        "permissions": [p.value for p in current_user.permissions],
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }

@app.post("/api/v1/auth/register")
async def register(
    credentials: AuthCredentials,
    email: Optional[str] = None,
    admin_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """Register new user (admin only)."""
    if auth_manager is None:
        raise HTTPException(503, "Authentication service not ready")
    
    try:
        user = await auth_manager.create_user(
            username=credentials.username,
            password=credentials.password,
            email=email,
            role=UserRole.USER
        )
        
        return {
            "message": "User created successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value
            }
        }
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        raise HTTPException(400, str(e))

# Security management endpoints

@app.get("/api/v1/security/events")
async def get_security_events(
    limit: int = 100,
    admin_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """Get security events (admin only)."""
    if auth_manager is None:
        raise HTTPException(503, "Authentication service not ready")
    
    try:
        events = await auth_manager.get_security_events(limit)
        return {
            "events": [
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "user_id": event.user_id,
                    "username": event.username,
                    "ip_address": event.ip_address,
                    "timestamp": event.timestamp.isoformat(),
                    "details": event.details,
                    "severity": event.severity
                }
                for event in events
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get security events: {e}")
        raise HTTPException(500, "Failed to retrieve security events")

# Health check endpoints (public)
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "mcp-server", "timestamp": time.time()}

@app.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check endpoint."""
    try:
        overall_health = await health_checker.get_overall_health()
        component_results = await health_checker.check_all_components()
        
        return {
            "status": overall_health.status.value,
            "message": overall_health.message,
            "timestamp": overall_health.timestamp,
            "details": overall_health.details,
            "components": [
                {
                    "component": result.component,
                    "status": result.status.value,
                    "message": result.message,
                    "details": result.details
                }
                for result in component_results
            ]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
            "timestamp": time.time()
        }

@app.get("/health/{component}")
async def component_health_check(component: str) -> Dict[str, Any]:
    """Health check for a specific component."""
    try:
        result = await health_checker.check_component(component)
        return {
            "component": result.component,
            "status": result.status.value,
            "message": result.message,
            "timestamp": result.timestamp,
            "details": result.details
        }
    except Exception as e:
        logger.error(f"Component health check failed for {component}: {e}", exc_info=True)
        raise HTTPException(500, f"Health check failed: {str(e)}")

# Metrics endpoints
@app.get("/metrics", response_class=PlainTextResponse)
def get_metrics() -> str:
    """Prometheus metrics endpoint."""
    try:
        return metrics_collector.get_metrics()
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get metrics: {str(e)}")

@app.get("/metrics/json")
def get_metrics_json(current_user: User = Depends(require_permission(Permission.READ))) -> Dict[str, Any]:
    """JSON metrics endpoint for programmatic access."""
    try:
        families = metrics_collector.get_metric_families()
        stats = metrics_collector.get_stats()
        
        return {
            "timestamp": time.time(),
            "collector_stats": stats,
            "metric_families": families
        }
    except Exception as e:
        logger.error(f"Failed to get JSON metrics: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get metrics: {str(e)}")

@app.get("/symbol", response_model=SymbolDef | None)
async def symbol(
    symbol: str,
    current_user: User = Depends(require_permission(Permission.READ))
):
    if dispatcher is None:
        logger.error("Symbol lookup attempted but dispatcher not ready")
        raise HTTPException(503, "Dispatcher not ready")
    
    start_time = time.time()
    try:
        logger.debug(f"Looking up symbol: {symbol} for user: {current_user.username}")
        
        # Try cache first if query cache is available
        cached_result = None
        if query_cache and query_cache.config.enabled:
            cached_result = await query_cache.get_cached_result(
                QueryType.SYMBOL_LOOKUP,
                symbol=symbol
            )
        
        if cached_result is not None:
            logger.debug(f"Found cached symbol: {symbol}")
            duration = time.time() - start_time
            business_metrics.record_search_performed(
                query=symbol,
                semantic=False,
                results_count=1,
                duration=duration
            )
            return cached_result
        
        # Record symbol lookup metrics
        with metrics_collector.time_function("symbol_lookup"):
            result = dispatcher.lookup(symbol)
        
        # Cache the result if available
        if query_cache and query_cache.config.enabled and result:
            await query_cache.cache_result(
                QueryType.SYMBOL_LOOKUP,
                result,
                symbol=symbol
            )
        
        # Record business metrics
        duration = time.time() - start_time
        business_metrics.record_search_performed(
            query=symbol,
            semantic=False,
            results_count=1 if result else 0,
            duration=duration
        )
        
        if result:
            logger.debug(f"Found symbol: {symbol}")
        else:
            logger.debug(f"Symbol not found: {symbol}")
        return result
    except Exception as e:
        duration = time.time() - start_time
        business_metrics.record_search_performed(
            query=symbol,
            semantic=False,
            results_count=0,
            duration=duration
        )
        logger.error(f"Error looking up symbol '{symbol}': {e}", exc_info=True)
        raise HTTPException(500, f"Internal error during symbol lookup: {str(e)}")

@app.get("/search", response_model=list[SearchResult])
async def search(
    q: str,
    semantic: bool = False,
    limit: int = 20,
    current_user: User = Depends(require_permission(Permission.READ))
):
    if dispatcher is None:
        logger.error("Search attempted but dispatcher not ready")
        raise HTTPException(503, "Dispatcher not ready")
    
    start_time = time.time()
    try:
        logger.debug(f"Searching for: '{q}' (semantic={semantic}, limit={limit}) for user: {current_user.username}")
        
        # Try cache first if query cache is available
        cached_results = None
        if query_cache and query_cache.config.enabled:
            query_type = QueryType.SEMANTIC_SEARCH if semantic else QueryType.SEARCH
            cached_results = await query_cache.get_cached_result(
                query_type,
                q=q,
                semantic=semantic,
                limit=limit
            )
        
        if cached_results is not None:
            logger.debug(f"Found cached search results for: '{q}' ({len(cached_results)} results)")
            duration = time.time() - start_time
            business_metrics.record_search_performed(
                query=q,
                semantic=semantic,
                results_count=len(cached_results),
                duration=duration
            )
            return cached_results
        
        # Record search metrics
        with metrics_collector.time_function("search", labels={"semantic": str(semantic)}):
            results = list(dispatcher.search(q, semantic=semantic, limit=limit))
        
        # Cache the results if available
        if query_cache and query_cache.config.enabled and results:
            query_type = QueryType.SEMANTIC_SEARCH if semantic else QueryType.SEARCH
            await query_cache.cache_result(
                query_type,
                results,
                q=q,
                semantic=semantic,
                limit=limit
            )
        
        # Record business metrics
        duration = time.time() - start_time
        business_metrics.record_search_performed(
            query=q,
            semantic=semantic,
            results_count=len(results),
            duration=duration
        )
        
        logger.debug(f"Search returned {len(results)} results")
        return results
    except Exception as e:
        duration = time.time() - start_time
        business_metrics.record_search_performed(
            query=q,
            semantic=semantic,
            results_count=0,
            duration=duration
        )
        logger.error(f"Error during search for '{q}': {e}", exc_info=True)
        raise HTTPException(500, f"Internal error during search: {str(e)}")

@app.get("/status")
async def status(current_user: User = Depends(require_permission(Permission.READ))) -> Dict[str, Any]:
    """Returns server status including plugin information and statistics."""
    if dispatcher is None:
        return {
            "status": "error",
            "plugins": 0,
            "indexed_files": {"total": 0, "by_language": {}},
            "version": "0.1.0",
            "message": "Dispatcher not initialized"
        }
    
    try:
        # Try cache first if query cache is available
        cached_status = None
        if query_cache and query_cache.config.enabled:
            cached_status = await query_cache.get_cached_result(
                QueryType.PROJECT_STATUS
            )
        
        if cached_status is not None:
            return cached_status
        
        # Get plugin count
        plugin_count = len(dispatcher._plugins) if hasattr(dispatcher, '_plugins') else 0
        
        # Get indexed files statistics
        indexed_stats = {"total": 0, "by_language": {}}
        if hasattr(dispatcher, 'get_statistics'):
            indexed_stats = dispatcher.get_statistics()
        elif hasattr(dispatcher, '_plugins'):
            # Calculate basic statistics from plugins
            for plugin in dispatcher._plugins:
                if hasattr(plugin, 'get_indexed_count'):
                    count = plugin.get_indexed_count()
                    indexed_stats["total"] += count
                    lang = getattr(plugin, 'language', getattr(plugin, 'lang', 'unknown'))
                    indexed_stats["by_language"][lang] = count
        
        # Add database statistics if available
        db_stats = {}
        if sqlite_store:
            db_stats = sqlite_store.get_statistics()
        
        # Add cache statistics if available
        cache_stats = {}
        if cache_manager:
            try:
                cache_metrics = await cache_manager.get_metrics()
                cache_stats = {
                    "hit_rate": cache_metrics.hit_rate,
                    "entries": cache_metrics.entries_count,
                    "memory_usage_mb": cache_metrics.memory_usage_mb
                }
            except Exception as e:
                logger.warning(f"Failed to get cache stats: {e}")
        
        status_data = {
            "status": "operational",
            "plugins": plugin_count,
            "indexed_files": indexed_stats,
            "database": db_stats,
            "cache": cache_stats,
            "version": "0.1.0"
        }
        
        # Cache the status
        if query_cache and query_cache.config.enabled:
            await query_cache.cache_result(
                QueryType.PROJECT_STATUS,
                status_data
            )
        
        return status_data
    except Exception as e:
        logger.error(f"Error getting server status: {e}", exc_info=True)
        return {
            "status": "error",
            "plugins": 0,
            "indexed_files": {"total": 0, "by_language": {}},
            "version": "0.1.0",
            "message": str(e)
        }

@app.get("/plugins")
def plugins(current_user: User = Depends(require_permission(Permission.READ))) -> List[Dict[str, Any]]:
    """Returns list of loaded plugins with their information."""
    if plugin_manager is None:
        logger.error("Plugin list requested but plugin manager not ready")
        raise HTTPException(503, "Plugin manager not ready")
    
    try:
        plugin_list = []
        plugin_infos = plugin_manager._registry.list_plugins()
        plugin_status = plugin_manager.get_plugin_status()
        
        for info in plugin_infos:
            status = plugin_status.get(info.name, {})
            plugin_data = {
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "author": info.author,
                "language": info.language,
                "file_extensions": info.file_extensions,
                "state": status.get('state', 'unknown'),
                "enabled": status.get('enabled', False)
            }
            plugin_list.append(plugin_data)
        
        logger.debug(f"Returning {len(plugin_list)} plugins")
        return plugin_list
    except Exception as e:
        logger.error(f"Error getting plugin list: {e}", exc_info=True)
        raise HTTPException(500, f"Internal error getting plugins: {str(e)}")

@app.post("/reindex")
async def reindex(
    path: Optional[str] = None,
    current_user: User = Depends(require_permission(Permission.EXECUTE))
) -> Dict[str, str]:
    """Triggers manual reindexing of files.
    
    Args:
        path: Optional specific directory path to reindex. If not provided,
              reindexes all configured paths.
    
    Returns:
        Task status information.
    """
    if dispatcher is None:
        logger.error("Reindex requested but dispatcher not ready")
        raise HTTPException(503, "Dispatcher not ready")
    
    try:
        logger.info(f"Manual reindex requested for path: {path or 'all'}")
        # Since dispatcher has index_file method, we can use it for reindexing
        if path:
            # Reindex specific path
            target_path = Path(path)
            if not target_path.exists():
                raise HTTPException(404, f"Path not found: {path}")
            
            indexed_count = 0
            if target_path.is_file():
                # Single file
                dispatcher.index_file(target_path)
                indexed_count = 1
            else:
                # Directory - find all supported files
                for file_path in target_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            # Check if any plugin supports this file
                            for plugin in dispatcher._plugins:
                                if plugin.supports(file_path):
                                    dispatcher.index_file(file_path)
                                    indexed_count += 1
                                    break
                        except Exception as e:
                            # Log but continue with other files
                            logger.warning(f"Failed to index {file_path}: {e}")
            
            logger.info(f"Successfully reindexed {indexed_count} files in {path}")
            return {
                "status": "completed",
                "message": f"Reindexed {indexed_count} files in {path}"
            }
        else:
            # Reindex all supported files
            indexed_count = 0
            indexed_by_type = {}
            
            # Find all files and check if any plugin supports them
            for file_path in Path(".").rglob("*"):
                if file_path.is_file():
                    try:
                        # Check if any plugin supports this file
                        for plugin in dispatcher._plugins:
                            if plugin.supports(file_path):
                                dispatcher.index_file(file_path)
                                indexed_count += 1
                                
                                # Track by file type
                                suffix = file_path.suffix.lower()
                                indexed_by_type[suffix] = indexed_by_type.get(suffix, 0) + 1
                                break
                    except Exception as e:
                        # Log but continue with other files
                        logger.warning(f"Failed to index {file_path}: {e}")
            
            # Build summary message
            type_summary = ", ".join([f"{count} {ext} files" for ext, count in indexed_by_type.items()])
            logger.info(f"Successfully reindexed {indexed_count} files: {type_summary}")
            return {
                "status": "completed",
                "message": f"Reindexed {indexed_count} files ({type_summary})"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reindexing failed: {e}", exc_info=True)
        raise HTTPException(500, f"Reindexing failed: {str(e)}")

@app.post("/plugins/{plugin_name}/reload")
async def reload_plugin(
    plugin_name: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, str]:
    """Reload a specific plugin.
    
    Args:
        plugin_name: Name of the plugin to reload
        
    Returns:
        Status message
    """
    if plugin_manager is None:
        logger.error("Plugin reload requested but plugin manager not ready")
        raise HTTPException(503, "Plugin manager not ready")
    
    try:
        plugin_manager.reload_plugin(plugin_name)
        return {
            "status": "success",
            "message": f"Plugin '{plugin_name}' reloaded successfully"
        }
    except Exception as e:
        logger.error(f"Failed to reload plugin '{plugin_name}': {e}", exc_info=True)
        raise HTTPException(500, f"Failed to reload plugin: {str(e)}")

@app.post("/plugins/{plugin_name}/enable")
async def enable_plugin(
    plugin_name: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, str]:
    """Enable a disabled plugin.
    
    Args:
        plugin_name: Name of the plugin to enable
        
    Returns:
        Status message
    """
    if plugin_manager is None:
        logger.error("Plugin enable requested but plugin manager not ready")
        raise HTTPException(503, "Plugin manager not ready")
    
    try:
        plugin_manager.enable_plugin(plugin_name)
        # Recreate dispatcher with updated plugins
        active_plugins = plugin_manager.get_active_plugins()
        global dispatcher
        dispatcher = Dispatcher(list(active_plugins.values()))
        
        return {
            "status": "success",
            "message": f"Plugin '{plugin_name}' enabled successfully"
        }
    except Exception as e:
        logger.error(f"Failed to enable plugin '{plugin_name}': {e}", exc_info=True)
        raise HTTPException(500, f"Failed to enable plugin: {str(e)}")

@app.post("/plugins/{plugin_name}/disable")
async def disable_plugin(
    plugin_name: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, str]:
    """Disable an active plugin.
    
    Args:
        plugin_name: Name of the plugin to disable
        
    Returns:
        Status message
    """
    if plugin_manager is None:
        logger.error("Plugin disable requested but plugin manager not ready")
        raise HTTPException(503, "Plugin manager not ready")
    
    try:
        plugin_manager.disable_plugin(plugin_name)
        # Recreate dispatcher with updated plugins
        active_plugins = plugin_manager.get_active_plugins()
        global dispatcher
        dispatcher = Dispatcher(list(active_plugins.values()))
        
        return {
            "status": "success",
            "message": f"Plugin '{plugin_name}' disabled successfully"
        }
    except Exception as e:
        logger.error(f"Failed to disable plugin '{plugin_name}': {e}", exc_info=True)
        raise HTTPException(500, f"Failed to disable plugin: {str(e)}")

# Cache management endpoints

@app.get("/cache/stats")
async def get_cache_stats(
    current_user: User = Depends(require_permission(Permission.READ))
) -> Dict[str, Any]:
    """Get cache statistics and performance metrics."""
    if not cache_manager:
        raise HTTPException(503, "Cache manager not ready")
    
    try:
        cache_metrics = await cache_manager.get_metrics()
        backend_stats = await cache_manager.get_backend_stats()
        
        stats = {
            "cache_metrics": {
                "hits": cache_metrics.hits,
                "misses": cache_metrics.misses,
                "sets": cache_metrics.sets,
                "deletes": cache_metrics.deletes,
                "hit_rate": cache_metrics.hit_rate,
                "avg_response_time_ms": cache_metrics.avg_response_time_ms,
                "entries_count": cache_metrics.entries_count,
                "memory_usage_mb": cache_metrics.memory_usage_mb
            },
            "backend_stats": backend_stats
        }
        
        # Add query cache stats if available
        if query_cache:
            query_stats = await query_cache.get_cache_stats()
            stats["query_cache"] = query_stats
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(500, f"Failed to get cache statistics: {str(e)}")

@app.post("/cache/clear")
async def clear_cache(
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """Clear all cache entries (admin only)."""
    if not cache_manager:
        raise HTTPException(503, "Cache manager not ready")
    
    try:
        count = await cache_manager.clear()
        logger.info(f"Cache cleared by admin user {current_user.username}: {count} entries")
        
        return {
            "status": "success",
            "message": f"Cleared {count} cache entries",
            "cleared_entries": count
        }
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(500, f"Failed to clear cache: {str(e)}")

@app.post("/cache/invalidate")
async def invalidate_cache_by_tags(
    tags: List[str],
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """Invalidate cache entries by tags (admin only)."""
    if not cache_manager:
        raise HTTPException(503, "Cache manager not ready")
    
    try:
        tag_set = set(tags)
        count = await cache_manager.invalidate_by_tags(tag_set)
        logger.info(f"Cache invalidated by admin user {current_user.username}: {count} entries with tags {tags}")
        
        return {
            "status": "success",
            "message": f"Invalidated {count} cache entries with tags {tags}",
            "invalidated_entries": count,
            "tags": tags
        }
    except Exception as e:
        logger.error(f"Failed to invalidate cache by tags: {e}")
        raise HTTPException(500, f"Failed to invalidate cache: {str(e)}")

@app.post("/cache/invalidate/files")
async def invalidate_cache_by_files(
    file_paths: List[str],
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """Invalidate cache entries that depend on specific files (admin only)."""
    if not query_cache:
        raise HTTPException(503, "Query cache not ready")
    
    try:
        total_count = 0
        for file_path in file_paths:
            count = await query_cache.invalidate_file_queries(file_path)
            total_count += count
        
        logger.info(f"File-based cache invalidation by admin user {current_user.username}: {total_count} entries for {len(file_paths)} files")
        
        return {
            "status": "success",
            "message": f"Invalidated {total_count} cache entries for {len(file_paths)} files",
            "invalidated_entries": total_count,
            "files": file_paths
        }
    except Exception as e:
        logger.error(f"Failed to invalidate cache by files: {e}")
        raise HTTPException(500, f"Failed to invalidate cache by files: {str(e)}")

@app.post("/cache/invalidate/semantic")
async def invalidate_semantic_cache(
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """Invalidate all semantic search cache entries (admin only)."""
    if not query_cache:
        raise HTTPException(503, "Query cache not ready")
    
    try:
        count = await query_cache.invalidate_semantic_queries()
        logger.info(f"Semantic cache invalidated by admin user {current_user.username}: {count} entries")
        
        return {
            "status": "success",
            "message": f"Invalidated {count} semantic search cache entries",
            "invalidated_entries": count
        }
    except Exception as e:
        logger.error(f"Failed to invalidate semantic cache: {e}")
        raise HTTPException(500, f"Failed to invalidate semantic cache: {str(e)}")

@app.post("/cache/warm")
async def warm_cache(
    keys: List[str],
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """Warm cache with predefined keys (admin only)."""
    if not cache_manager:
        raise HTTPException(503, "Cache manager not ready")
    
    try:
        # Simple factory function for warming - would need more sophisticated logic in production
        async def factory(key: str):
            # This is a placeholder - in real implementation would depend on key type
            return f"warmed_value_for_{key}"
        
        count = await cache_manager.warm_cache(keys, factory)
        logger.info(f"Cache warmed by admin user {current_user.username}: {count} entries")
        
        return {
            "status": "success",
            "message": f"Warmed {count} cache entries",
            "warmed_entries": count,
            "requested_keys": len(keys)
        }
    except Exception as e:
        logger.error(f"Failed to warm cache: {e}")
        raise HTTPException(500, f"Failed to warm cache: {str(e)}")

@app.post("/cache/cleanup")
async def cleanup_cache(
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> Dict[str, Any]:
    """Manually trigger cache cleanup (admin only)."""
    if not cache_manager:
        raise HTTPException(503, "Cache manager not ready")
    
    try:
        count = await cache_manager.cleanup()
        logger.info(f"Cache cleanup triggered by admin user {current_user.username}: {count} entries cleaned")
        
        return {
            "status": "success",
            "message": f"Cleaned up {count} expired cache entries",
            "cleaned_entries": count
        }
    except Exception as e:
        logger.error(f"Failed to cleanup cache: {e}")
        raise HTTPException(500, f"Failed to cleanup cache: {str(e)}")
