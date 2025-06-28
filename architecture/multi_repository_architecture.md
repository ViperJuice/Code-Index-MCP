# Multi-Repository and Smart Plugin Loading Architecture

## Overview

This document describes the architecture for enhancing MCP to support multiple use cases through intelligent plugin loading and multi-repository search capabilities.

## Use Cases

### Use Case 1: Single Repository Development
**Scenario**: Developer using Claude Code to build/enhance a single repository.

**Current Behavior**:
- MCP loads all 47 plugins regardless of repository content
- High memory usage (~1.4GB) and slow startup
- Wasteful for repos with only 2-3 languages

**Enhanced Behavior**:
- Detect languages in repository index on startup
- Load only required plugins (e.g., 7 plugins for Python/HTML/CSS repo)
- 85% reduction in memory usage
- Faster startup and search operations

### Use Case 2: Multi-Repository Reference
**Scenario**: Developer refactoring code using multiple repositories as reference.

**Current Behavior**:
- MCP only searches current working directory repository
- Other repos require manual Grep/Read tools
- Loss of MCP benefits for reference repositories

**Enhanced Behavior**:
- Optional `repository` parameter in MCP tools
- Dynamic loading of plugins for referenced repositories
- Unified search across multiple repositories
- Memory-aware caching of repository indexes

### Use Case 3: Comprehensive Analysis
**Scenario**: Testing MCP capabilities across many languages and repositories.

**Current Behavior**:
- Must manually switch between repositories
- No built-in support for cross-repository analysis
- Benchmarking requires custom scripts

**Enhanced Behavior**:
- Analysis mode flag loads all plugins upfront
- Support for querying multiple repositories
- Comprehensive metrics collection
- Higher memory limits for testing scenarios

## Architecture Components

### 1. Repository Language Detection

```python
class RepositoryLanguageDetector:
    """Detects languages present in a repository index."""
    
    def detect_languages(self, db_path: str) -> Set[str]:
        """Query index database for distinct languages."""
        # Query files table for language distribution
        # Map file extensions to plugin languages
        # Return set of required plugin languages
```

### 2. Multi-Repository Index Manager

```python
class MultiRepoIndexManager:
    """Manages indexes across multiple repositories."""
    
    def __init__(self, primary_repo_id: str, storage_path: str):
        self.primary_repo_id = primary_repo_id
        self.loaded_indexes = {}  # repo_id -> SQLiteStore
        self.repo_languages = {}   # repo_id -> Set[str]
        
    def get_index(self, repo_id: Optional[str] = None) -> SQLiteStore:
        """Get index for specified or primary repository."""
        
    def search_across_repos(self, query: str, repo_ids: List[str]) -> List[SearchResult]:
        """Search multiple repositories in parallel."""
```

### 3. Memory-Aware Plugin Manager

```python
class MemoryAwarePluginManager:
    """Manages plugins with memory constraints and LRU eviction."""
    
    def __init__(self, max_memory_mb: int = 1024):
        self.plugins: OrderedDict[str, PluginInfo] = OrderedDict()
        self.max_memory_mb = max_memory_mb
        self.access_counts = defaultdict(int)
        self.last_access = {}
        
    async def get_plugin(self, language: str, timeout: float = 5.0) -> IPlugin:
        """Get plugin with memory management and timeout."""
        
    def _evict_lru_plugins(self, target_free_mb: int = 100):
        """Evict least recently used plugins to free memory."""
```

### 4. Enhanced MCP Tools

```python
# Updated tool schema with repository parameter
types.Tool(
    name="search_code",
    inputSchema={
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "repository": {
                "type": "string",
                "description": "Repository ID or path. Defaults to current repo.",
                "optional": True
            },
            "semantic": {"type": "boolean", "default": False},
            "limit": {"type": "integer", "default": 20}
        }
    }
)
```

## Repository Resolution

### Repository ID Generation
1. Primary method: SHA256 hash of git remote URL (first 12 chars)
2. Fallback: SHA256 hash of absolute path for non-git directories

### Index Storage Structure
```
.indexes/
├── f7b49f5d0ae0/          # Current repo
│   ├── current.db
│   └── metadata.json
├── d72d7e1e17d2/          # Reference repo 1
│   ├── current.db
│   └── metadata.json
└── e3acd2328eea/          # Reference repo 2
    ├── current.db
    └── metadata.json
```

## Configuration Strategy

### Environment Variables
```bash
# Plugin loading strategy
MCP_PLUGIN_STRATEGY=auto|all|minimal
- auto: Load based on detected languages (default)
- all: Load all plugins (analysis mode)
- minimal: Load only on-demand

# Multi-repository support
MCP_ENABLE_MULTI_REPO=true|false
- Enable/disable multi-repo features

MCP_REFERENCE_REPOS=repo1,repo2,repo3
- Pre-authorized repository IDs for cross-repo search

# Memory management
MCP_MAX_MEMORY_MB=1024
- Maximum memory for plugin manager

MCP_MIN_FREE_MB=256
- Minimum free memory to maintain

# Performance tuning
MCP_PLUGIN_LOAD_TIMEOUT=5.0
- Timeout for loading individual plugins

MCP_CACHE_HIGH_PRIORITY_LANGS=python,javascript,typescript
- Languages to keep in memory
```

### Language Priority System
```python
LANGUAGE_PRIORITIES = {
    "python": 100,      # Most common
    "javascript": 95,
    "typescript": 95,
    "java": 85,
    "go": 80,
    "rust": 75,
    "c": 70,
    "cpp": 70,
    # ... others get default priority of 50
}
```

## Implementation Flow

### Startup Sequence
1. Determine repository ID from git remote or path
2. Load primary repository index
3. Detect languages in primary repository
4. Load plugins based on strategy:
   - auto: Load detected languages only
   - all: Load all 47 plugins
   - minimal: Load nothing, wait for requests
5. Initialize multi-repo manager if enabled
6. Pre-cache authorized reference repositories

### Query Processing
1. Parse tool request for repository parameter
2. If repository specified:
   - Resolve repository ID
   - Check authorization
   - Load repository index if not cached
   - Detect new languages
   - Load required plugins with memory check
3. Route query to appropriate repository index
4. Return results with repository context

### Memory Management Flow
1. Monitor process memory usage
2. When approaching limit:
   - Calculate eviction candidates
   - Score by: priority, frequency, recency
   - Evict lowest scoring plugins
   - Free plugin resources properly
3. Log eviction events for monitoring

## Performance Considerations

### Optimization Strategies
1. **Lazy Loading**: Plugins load only when needed
2. **Parallel Search**: Multi-repo queries execute in parallel
3. **Index Caching**: Recently used indexes stay in memory
4. **Query Caching**: Results cached per repository
5. **Batch Operations**: Group plugin loads together

### Expected Performance
- Single repo startup: < 2 seconds (vs 10+ seconds)
- Plugin load time: < 5 seconds per language
- Multi-repo search: < 3 seconds for 3 repos
- Memory usage: 200-400MB typical (vs 1.4GB)

## Backward Compatibility

### Preserved Behavior
1. Default mode works exactly as before
2. No repository parameter = current directory
3. All existing APIs remain unchanged
4. Configuration is opt-in via environment

### Migration Path
1. Existing installations work without changes
2. Enable features gradually via environment
3. Monitor performance improvements
4. Adjust configuration based on usage

## Security Considerations

### Repository Authorization
- Only allow searching pre-authorized repos
- Validate repository IDs before access
- Log all cross-repository operations
- Respect existing index access controls

### Resource Limits
- Enforce memory limits strictly
- Timeout long-running operations
- Limit concurrent repository loads
- Monitor for resource exhaustion

## Future Extensions

### Potential Enhancements
1. Repository groups for project sets
2. Distributed index synchronization
3. Cloud-based repository indexes
4. Automatic language detection from file content
5. Plugin performance profiling and optimization