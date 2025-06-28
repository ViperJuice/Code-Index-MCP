workspace "Code-Index-MCP" "Local-first code indexer with 48-language support via Model Context Protocol" {
    # Implementation Status: 100% complete - PRODUCTION READY
    # Complexity Score: 5/5
    # Last Updated: 2025-06-26

    !identifiers hierarchical
    
    model {
        # External actors
        developer = person "Developer" "Uses Claude Code or other LLMs for code navigation and search"
        claudeCode = softwareSystem "Claude Code" "AI-powered code assistant with MCP sub-agent support" {
            tags "External System"
        }
        
        # The Code-Index-MCP system
        codeIndexMCP = softwareSystem "Code-Index-MCP" "Local-first code indexer providing fast symbol search and semantic code navigation across 48 programming languages" {
            
            # Container Level
            apiGateway = container "API Gateway" "Handles MCP requests and routes to appropriate services" "FastAPI/Python" {
                tags "Container"
            }
            
            dispatcher = container "Dispatcher" "Routes requests to appropriate language plugins with caching" "Python" {
                tags "Container"
            }
            
            pluginFramework = container "Language Plugin Framework" "Manages 48 language plugins via factory pattern" "Python" {
                tags "Container" "Core Component"
                
                # Component Level - Plugin System
                pluginFactory = component "Plugin Factory" "Creates appropriate plugin instances based on file type" "Python Class"
                languageRegistry = component "Language Registry" "Stores configurations for all 48 supported languages" "Python Module"
                pluginCache = component "Plugin Cache" "Caches plugin instances for performance" "Python Class"
                
                # Language Plugins - Enhanced (6)
                pythonPlugin = component "Python Plugin" "Enhanced Python analysis with Jedi integration" "Python Class" {
                    tags "Language Plugin" "Enhanced"
                }
                jsPlugin = component "JavaScript Plugin" "JavaScript/TypeScript analysis with semantic support" "Python Class" {
                    tags "Language Plugin" "Enhanced"
                }
                cPlugin = component "C Plugin" "C language analysis with preprocessor support" "Python Class" {
                    tags "Language Plugin" "Enhanced"
                }
                cppPlugin = component "C++ Plugin" "C++ analysis with template support" "Python Class" {
                    tags "Language Plugin" "Enhanced"
                }
                dartPlugin = component "Dart Plugin" "Dart language analysis" "Python Class" {
                    tags "Language Plugin" "Enhanced"
                }
                htmlCssPlugin = component "HTML/CSS Plugin" "HTML/CSS analysis with selector support" "Python Class" {
                    tags "Language Plugin" "Enhanced"
                }
                
                # Language Plugins - Specialized (7)
                javaPlugin = component "Java Plugin" "Java analysis with Maven/Gradle and type system support" "Python Class" {
                    tags "Language Plugin" "Specialized"
                }
                goPlugin = component "Go Plugin" "Go analysis with module system and interface checking" "Python Class" {
                    tags "Language Plugin" "Specialized"
                }
                rustPlugin = component "Rust Plugin" "Rust analysis with trait system and Cargo integration" "Python Class" {
                    tags "Language Plugin" "Specialized"
                }
                csharpPlugin = component "C# Plugin" "C# analysis with namespace resolution and NuGet support" "Python Class" {
                    tags "Language Plugin" "Specialized"
                }
                swiftPlugin = component "Swift Plugin" "Swift analysis with protocol conformance and Obj-C interop" "Python Class" {
                    tags "Language Plugin" "Specialized"
                }
                kotlinPlugin = component "Kotlin Plugin" "Kotlin analysis with null safety and coroutines support" "Python Class" {
                    tags "Language Plugin" "Specialized"
                }
                typescriptPlugin = component "TypeScript Plugin" "TypeScript analysis with full type system and tsconfig support" "Python Class" {
                    tags "Language Plugin" "Specialized"
                }
                
                # Document Processing Plugins (2)
                markdownPlugin = component "Markdown Plugin" "Markdown processing with hierarchical extraction" "Python Class" {
                    tags "Language Plugin" "Document"
                }
                plaintextPlugin = component "PlainText Plugin" "Plain text processing with NLP features" "Python Class" {
                    tags "Language Plugin" "Document"
                }
                
                # Generic Plugin
                genericPlugin = component "Generic Tree-Sitter Plugin" "Handles 35+ additional languages via tree-sitter" "Python Class" {
                    tags "Language Plugin" "Generic"
                }
                
                # Plugin Base Classes
                pluginBase = component "Plugin Base" "Abstract base class for all plugins" "Python Abstract Class"
                semanticPluginBase = component "Semantic Plugin Base" "Base class with semantic search support" "Python Class"
            }
            
            indexEngine = container "Index Engine" "Manages code indexing and search operations" "Python" {
                tags "Container"
                
                # Component Level - Indexing
                indexManager = component "Index Manager" "Coordinates indexing operations" "Python Class"
                multiRepoManager = component "Multi-Repository Manager" "Manages indexes across multiple repositories" "Python Class"
                pluginMemoryManager = component "Plugin Memory Manager" "LRU cache with memory-aware eviction" "Python Class"
                languageDetector = component "Language Detector" "Detects languages from repository indexes" "Python Class"
                queryOptimizer = component "Query Optimizer" "Optimizes search queries across languages" "Python Class"
                semanticIndexer = component "Semantic Indexer" "Manages embeddings and vector search" "Python Class"
            }
            
            storage = container "Storage Layer" "Centralized storage for code symbols and search indices at ~/.mcp/indexes/" "SQLite + Qdrant" {
                tags "Container" "Database"
                
                # Component Level - Storage
                sqliteStore = component "SQLite Store" "Stores symbols, references, and metadata in centralized location" "SQLite with FTS5"
                qdrantStore = component "Qdrant Store" "Vector database for semantic embeddings" "Qdrant"
                indexManager = component "Index Manager" "Manages centralized index storage with repo isolation" "Python Class"
                indexDiscovery = component "Index Discovery" "Multi-path discovery with enhanced validation and compatibility checking" "Python Class"
            }
            
            fileWatcher = container "File Watcher" "Monitors file system changes for real-time updates" "Python/Watchdog" {
                tags "Container"
            }
            
            embeddingService = container "Embedding Service" "Generates code embeddings for semantic search" "Python/Voyage AI" {
                tags "Container" "AI Service"
            }
            
            mcpServer = container "MCP Server" "Enhanced MCP protocol server with sync integration and performance optimization" "Python/MCP Protocol" {
                tags "Container"
                
                # Final 5% completion components
                mcpConfigPropagator = component "MCP Config Propagator" "Enables MCP tool inheritance for sub-agents" "Python Class"
                preflightValidator = component "Pre-flight Validator" "Validates system state before operations" "Python Class"
                indexManagementCLI = component "Index Management CLI" "Comprehensive CLI for index operations" "Python Module"
                repositoryAwareLoader = component "Repository-Aware Plugin Loader" "Smart plugin loading based on repository structure" "Python Class"
                memoryAwareManager = component "Memory-Aware Plugin Manager" "LRU cache with memory constraints" "Python Class"
                crossRepoCoordinator = component "Cross-Repository Coordinator" "Coordinates searches across multiple repositories" "Python Class"
                syncIntegration = component "Sync Integration" "Git hooks and automatic index synchronization" "Python Module"
            }
            
            userDocumentation = container "User Documentation" "Performance tuning, troubleshooting, and best practices guides" "Markdown/HTML" {
                tags "Container" "Documentation"
                
                performanceTuningGuide = component "Performance Tuning Guide" "Optimization strategies and configuration tips" "Markdown"
                troubleshootingGuide = component "Troubleshooting Guide" "Common issues and solutions" "Markdown"
                bestPracticesGuide = component "Best Practices Guide" "Recommended usage patterns and workflows" "Markdown"
                quickStartGuide = component "Quick Start Guide" "Getting started with Code-Index-MCP" "Markdown"
            }
            
            productionValidation = container "Production Validation Suite" "End-to-end testing and monitoring framework" "Python/Pytest" {
                tags "Container" "Testing"
                
                componentTestFramework = component "Component Test Framework" "Isolated testing of individual components" "Python"
                integrationTestFramework = component "Integration Test Framework" "Cross-component integration testing" "Python"
                e2eTestFramework = component "End-to-End Test Framework" "Full workflow testing" "Python"
                performanceTestSuite = component "Performance Test Suite" "Load and stress testing" "Python"
                architectureValidation = component "Architecture Validation" "Validates alignment between docs and implementation" "Python"
            }
        }
        
        # External dependencies
        voyageAI = softwareSystem "Voyage AI" "Code embedding generation service" {
            tags "External System" "AI Service"
        }
        
        fileSystem = softwareSystem "File System" "Local file system containing source code" {
            tags "External System"
        }
        
        # Relationships - System Context
        developer -> claudeCode "Uses for code assistance"
        claudeCode -> codeIndexMCP "Queries via MCP protocol with sub-agent support"
        codeIndexMCP -> fileSystem "Monitors and indexes"
        codeIndexMCP -> voyageAI "Generates embeddings"
        
        # Relationships - Container Level
        claudeCode -> codeIndexMCP.apiGateway "Sends MCP requests"
        codeIndexMCP.apiGateway -> codeIndexMCP.dispatcher "Routes requests"
        codeIndexMCP.dispatcher -> codeIndexMCP.pluginFramework "Delegates to plugins"
        codeIndexMCP.dispatcher -> codeIndexMCP.storage "Caches results"
        codeIndexMCP.pluginFramework -> codeIndexMCP.indexEngine "Triggers indexing"
        codeIndexMCP.pluginFramework -> codeIndexMCP.storage "Stores symbols"
        codeIndexMCP.indexEngine -> codeIndexMCP.storage "Reads/writes indices"
        codeIndexMCP.indexEngine -> codeIndexMCP.embeddingService "Requests embeddings"
        codeIndexMCP.embeddingService -> voyageAI "API calls"
        codeIndexMCP.fileWatcher -> codeIndexMCP.indexEngine "Triggers re-indexing"
        codeIndexMCP.fileWatcher -> fileSystem "Monitors changes"
        
        # Final 5% completion relationships
        claudeCode -> codeIndexMCP.mcpServer "Enhanced MCP protocol communication"
        codeIndexMCP.mcpServer -> codeIndexMCP.apiGateway "Improved request routing"
        developer -> codeIndexMCP.userDocumentation "References guides"
        codeIndexMCP.mcpServer.syncIntegration -> codeIndexMCP.storage "Syncs repository state"
        codeIndexMCP.productionValidation.e2eTestFramework -> codeIndexMCP.apiGateway "Validates full workflows"
        
        # Relationships - Component Level (Plugin System)
        codeIndexMCP.dispatcher -> codeIndexMCP.pluginFramework.pluginFactory "Requests plugin instance"
        codeIndexMCP.pluginFramework.pluginFactory -> codeIndexMCP.pluginFramework.languageRegistry "Looks up language config"
        codeIndexMCP.pluginFramework.pluginFactory -> codeIndexMCP.pluginFramework.pluginCache "Checks cache"
        codeIndexMCP.pluginFramework.pluginFactory -> codeIndexMCP.pluginFramework.pythonPlugin "Creates if Python"
        codeIndexMCP.pluginFramework.pluginFactory -> codeIndexMCP.pluginFramework.jsPlugin "Creates if JavaScript"
        codeIndexMCP.pluginFramework.pluginFactory -> codeIndexMCP.pluginFramework.javaPlugin "Creates if Java"
        codeIndexMCP.pluginFramework.pluginFactory -> codeIndexMCP.pluginFramework.goPlugin "Creates if Go"
        
        # Plugin inheritance relationships (simplified)
        codeIndexMCP.pluginFramework.pythonPlugin -> codeIndexMCP.pluginFramework.semanticPluginBase "Extends"
        codeIndexMCP.pluginFramework.jsPlugin -> codeIndexMCP.pluginFramework.semanticPluginBase "Extends"
        codeIndexMCP.pluginFramework.javaPlugin -> codeIndexMCP.pluginFramework.semanticPluginBase "Extends"
        codeIndexMCP.pluginFramework.goPlugin -> codeIndexMCP.pluginFramework.semanticPluginBase "Extends"
        codeIndexMCP.pluginFramework.semanticPluginBase -> codeIndexMCP.pluginFramework.pluginBase "Extends"
        
        # Indexing relationships (simplified)
        codeIndexMCP.pluginFramework.pythonPlugin -> codeIndexMCP.indexEngine.indexManager "Sends symbols"
        codeIndexMCP.pluginFramework.jsPlugin -> codeIndexMCP.indexEngine.indexManager "Sends symbols"
        codeIndexMCP.pluginFramework.javaPlugin -> codeIndexMCP.indexEngine.indexManager "Sends symbols"
        codeIndexMCP.pluginFramework.goPlugin -> codeIndexMCP.indexEngine.indexManager "Sends symbols"
        codeIndexMCP.indexEngine.indexManager -> codeIndexMCP.storage.sqliteStore "Stores symbols"
        codeIndexMCP.indexEngine.semanticIndexer -> codeIndexMCP.embeddingService "Gets embeddings"
        codeIndexMCP.indexEngine.semanticIndexer -> codeIndexMCP.storage.qdrantStore "Stores vectors"
        codeIndexMCP.indexEngine.queryOptimizer -> codeIndexMCP.storage.sqliteStore "Queries symbols"
        codeIndexMCP.indexEngine.queryOptimizer -> codeIndexMCP.storage.qdrantStore "Semantic search"
        codeIndexMCP.indexEngine.indexManager -> codeIndexMCP.storage.indexDiscovery "Uses to find indexes"
        codeIndexMCP.storage.indexDiscovery -> codeIndexMCP.storage.sqliteStore "Discovers indexes via multi-path search"
    }
    
    views {
        # Level 1: System Context
        systemContext codeIndexMCP "SystemContext" {
            include *
            autoLayout
            description "System context showing Code-Index-MCP's role in the development ecosystem"
        }
        
        # Level 2: Container Diagram
        container codeIndexMCP "Containers" {
            include *
            autoLayout
            description "Container diagram showing the major components of Code-Index-MCP"
        }
        
        # Level 3: Component Diagram - Plugin System
        component codeIndexMCP.pluginFramework "PluginSystemComponents" {
            include *
            autoLayout
            description "Component diagram showing the plugin system architecture supporting 48 languages"
        }
        
        # Level 3: Component Diagram - Index Engine
        component codeIndexMCP.indexEngine "IndexEngineComponents" {
            include *
            autoLayout
            description "Component diagram showing the indexing and search components"
        }
        
        # Level 3: Component Diagram - Storage
        component codeIndexMCP.storage "StorageComponents" {
            include *
            autoLayout
            description "Component diagram showing the storage layer with SQLite and Qdrant"
        }
        
        # Dynamic view showing indexing flow
        dynamic codeIndexMCP "IndexingFlow" "Shows the flow of indexing a Python file" {
            developer -> claudeCode "Requests file indexing"
            claudeCode -> codeIndexMCP.apiGateway "POST /reindex"
            codeIndexMCP.apiGateway -> codeIndexMCP.dispatcher "Route to indexer"
            codeIndexMCP.dispatcher -> codeIndexMCP.pluginFramework "Get Python plugin"
            codeIndexMCP.pluginFramework -> codeIndexMCP.storage "Store symbols"
            codeIndexMCP.embeddingService -> voyageAI "API: voyage-code-3"
            autoLayout
        }
        
        # Dynamic view showing search flow
        dynamic codeIndexMCP "SearchFlow" "Shows semantic search across multiple languages" {
            developer -> claudeCode "Search: 'calculate fibonacci'"
            claudeCode -> codeIndexMCP.apiGateway "POST /search"
            codeIndexMCP.apiGateway -> codeIndexMCP.dispatcher "Route search"
            codeIndexMCP.dispatcher -> codeIndexMCP.pluginFramework "Delegate to plugins"
            codeIndexMCP.pluginFramework -> codeIndexMCP.storage "Query symbols and vectors"
            codeIndexMCP.apiGateway -> claudeCode "Return ranked results"
            claudeCode -> developer "Display results"
            autoLayout
        }
        
        # Dynamic view showing MCP success with enhanced server
        dynamic codeIndexMCP "MCPSuccessFlow" "Shows how the enhanced MCP server handles requests" {
            developer -> claudeCode "Request code search"
            claudeCode -> codeIndexMCP.mcpServer "Enhanced MCP protocol"
            codeIndexMCP.mcpServer -> codeIndexMCP.apiGateway "Route MCP call"
            codeIndexMCP.apiGateway -> codeIndexMCP.dispatcher "Process request"
            codeIndexMCP.dispatcher -> codeIndexMCP.apiGateway "Return results"
            codeIndexMCP.apiGateway -> claudeCode "Send results"
            claudeCode -> developer "Present search results"
            autoLayout
            description "This flow demonstrates how the enhanced MCP server enables successful tool access for all agents including sub-agents"
        }
        
        # Deployment view - simplified
        systemLandscape "SystemLandscape" {
            include *
            autoLayout
            description "System landscape showing Code-Index-MCP in its operational environment"
        }
        
        styles {
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "External System" {
                background #999999
                color #ffffff
                shape RoundedBox
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
            element "Component" {
                background #85bbf0
                color #000000
            }
            element "Database" {
                shape Cylinder
            }
            element "Person" {
                background #08427b
                color #ffffff
                shape Person
            }
            element "Language Plugin" {
                background #85f0bb
                color #000000
            }
            element "Enhanced" {
                background #5fb85f
                color #ffffff
            }
            element "Generic" {
                background #f0bb85
                color #000000
            }
            element "AI Service" {
                background #ff6b6b
                color #ffffff
            }
            element "Core Component" {
                background #4a90e2
                color #ffffff
            }
            element "Issue" {
                background #ff6b6b
                color #ffffff
                shape RoundedBox
            }
            element "AI Agent" {
                background #9b59b6
                color #ffffff
            }
            relationship "Broken" {
                color #ff0000
                style dashed
            }
        }
    }
    
    configuration {
        scope softwaresystem
    }
    
}