# System Architecture

## Level 1: System Context

```mermaid
C4Context
    title System Context Diagram for Code-Index-MCP

    Person(developer, "Developer", "Uses the system to index and search code")
    System(code_index_mcp, "Code-Index-MCP", "Local-first code indexer providing MCP interface to LLMs")
    
    System_Ext(claude, "Claude / LLM", "AI Assistant consuming the MCP tools")
    System_Ext(git, "Git Repository", "Source code to be indexed")
    System_Ext(github, "GitHub Artifacts", "Storage for shared indexes")

    Rel(developer, claude, "Prompts", "Text")
    Rel(claude, code_index_mcp, "Calls Tools", "MCP Protocol")
    Rel(code_index_mcp, git, "Watches & Indexes", "File System Events")
    Rel(code_index_mcp, github, "Syncs Indexes", "HTTPS")
```

## Level 2: Container Diagram

```mermaid
C4Container
    title Container Diagram for Code-Index-MCP Server

    Container_Boundary(mcp_server_boundary, "MCP Server Host") {
        Container(gateway, "Gateway API", "FastAPI / Uvicorn", "Entry point for MCP protocol and HTTP requests")
        Container(handshake_gate, "HandshakeGate", "Python Class", "Validates repository roots; raises path_outside_allowed_roots on violations")
        Container(dispatcher, "Dispatcher", "Python Class", "Orchestrates search and indexing requests")
        Container(plugin_system, "Plugin System", "Python Modules", "Manages language-specific analysis")
        Container_Boundary(watcher_boundary, "File Watching") {
            Container(multi_repo_watcher, "MultiRepositoryWatcher", "Python Class", "Coordinates per-repo watchers across all registered repositories")
            Container(ref_poller, "RefPoller", "Python Class", "Polls Git refs for branch changes every 30s")
        }
        Container(sync_service, "Sync Service", "Python Module", "Manages index synchronization")
    }

    ContainerDb(sqlite, "Local Index", "SQLite + FTS5", "Stores symbol tables and text index")
    ContainerDb(vector_db, "Semantic Index", "Qdrant / LanceDB", "Stores vector embeddings")

    Rel(gateway, handshake_gate, "Validates path", "raises path_outside_allowed_roots")
    Rel(gateway, dispatcher, "Delegates requests")
    Rel(dispatcher, plugin_system, "Uses for analysis")
    Rel(dispatcher, sqlite, "Reads/Writes")
    Rel(dispatcher, vector_db, "Reads/Writes")
    Rel(multi_repo_watcher, dispatcher, "Triggers indexing")
    Rel(ref_poller, multi_repo_watcher, "Reports ref changes")
    Rel(gateway, sync_service, "Triggers sync")
```

## Level 3: Component Diagram (MCP Server)

```mermaid
C4Component
    title Component Diagram for Code-Index-MCP Core

    Container_Boundary(core, "Core Components") {
        Component(enhanced_dispatcher, "EnhancedDispatcher", "Python Class", "Handles routing, fallback, and aggregation")
        Component(repo_context, "RepoContext", "Python Class", "Holds per-repo state: path, branch, language profile")
        Component(plugin_factory, "Plugin Factory", "Factory Pattern", "Creates and caches plugin instances")
        Component(repo_plugin_loader, "Repo Plugin Loader", "class", "Optimizes plugin loading based on repo content")
        Component(result_aggregator, "Result Aggregator", "class", "Merges results from multiple sources")
    }

    Container_Boundary(registry, "Registry Layer") {
        Component(store_registry, "StoreRegistry", "Python Class", "Maps repo IDs to SQLite store instances")
        Component(repository_registry, "RepositoryRegistry", "Python Class", "Tracks all registered repository roots and their metadata")
    }

    Container_Boundary(plugins, "Plugin Layer") {
        Component(language_plugins, "Language Plugins", "IPlugin Implementation", "Specific logic for Python, JS, Go, etc.")
        Component(parser, "Tree Sitter", "Library", "Parses code into AST")
    }

    Container_Boundary(storage, "Storage Layer") {
        Component(sqlite_store, "SQLite Store", "Data Access", "Manages SQLite connections and queries")
        Component(semantic_indexer, "Semantic Indexer", "Vector Client", "Manages embeddings generation and storage")
    }
    
    Container_Boundary(services, "Services") {
        Component(cloud_sync, "Cloud Sync", "class", "Handles artifact upload/download (Needs Implementation)")
    }

    Rel(enhanced_dispatcher, plugin_factory, "Requests plugins")
    Rel(plugin_factory, language_plugins, "Instantiates")
    Rel(language_plugins, parser, "Uses")
    Rel(enhanced_dispatcher, result_aggregator, "Uses")
    Rel(enhanced_dispatcher, sqlite_store, "Queries")
    Rel(enhanced_dispatcher, semantic_indexer, "Queries")
    Rel(enhanced_dispatcher, cloud_sync, "Notifies")
    Rel(enhanced_dispatcher, repo_context, "Resolves per-repo context")
    Rel(repo_context, store_registry, "Looks up store by repo ID")
    Rel(repo_context, repository_registry, "Validates repo root")
```

## Dependability Notes

`EnhancedDispatcher.lookup()` falls through to `plugin.getDefinition()` for every registered language plugin when a symbol is absent from the SQLite index. The C plugin can hang in tree-sitter traversal on this fallback path. Surfaced during the multi-repo integration test in P5/SL-3. Not fixed; callers should expect occasional slow lookups on C-file symbols.
