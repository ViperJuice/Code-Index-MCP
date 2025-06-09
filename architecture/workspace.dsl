workspace "Code-Index-MCP" "Local-first code indexer with 48-language support via Model Context Protocol" {
    # Implementation Status: 100% complete - PRODUCTION READY
    # Complexity Score: 5/5
    # Last Updated: 2025-06-09

    !identifiers hierarchical
    
    model {
        # External actors
        developer = person "Developer" "Uses Claude Code or other LLMs for code navigation and search"
        claudeCode = softwareSystem "Claude Code" "AI-powered code assistant" {
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
                queryOptimizer = component "Query Optimizer" "Optimizes search queries across languages" "Python Class"
                semanticIndexer = component "Semantic Indexer" "Manages embeddings and vector search" "Python Class"
            }
            
            storage = container "Storage Layer" "Persistent storage for code symbols and search indices" "SQLite + Qdrant" {
                tags "Container" "Database"
                
                # Component Level - Storage
                sqliteStore = component "SQLite Store" "Stores symbols, references, and metadata" "SQLite with FTS5"
                qdrantStore = component "Qdrant Store" "Vector database for semantic embeddings" "Qdrant"
            }
            
            fileWatcher = container "File Watcher" "Monitors file system changes for real-time updates" "Python/Watchdog" {
                tags "Container"
            }
            
            embeddingService = container "Embedding Service" "Generates code embeddings for semantic search" "Python/Voyage AI" {
                tags "Container" "AI Service"
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
        claudeCode -> codeIndexMCP "Queries via MCP protocol"
        codeIndexMCP -> fileSystem "Monitors and indexes"
        codeIndexMCP -> voyageAI "Generates embeddings"
        
        # Relationships - Container Level
        claudeCode -> apiGateway "Sends MCP requests"
        apiGateway -> dispatcher "Routes requests"
        dispatcher -> pluginFramework "Delegates to plugins"
        dispatcher -> storage "Caches results"
        pluginFramework -> indexEngine "Triggers indexing"
        pluginFramework -> storage "Stores symbols"
        indexEngine -> storage "Reads/writes indices"
        indexEngine -> embeddingService "Requests embeddings"
        embeddingService -> voyageAI "API calls"
        fileWatcher -> indexEngine "Triggers re-indexing"
        fileWatcher -> fileSystem "Monitors changes"
        
        # Relationships - Component Level (Plugin System)
        dispatcher -> pluginFactory "Requests plugin instance"
        pluginFactory -> languageRegistry "Looks up language config"
        pluginFactory -> pluginCache "Checks cache"
        pluginFactory -> pythonPlugin "Creates if Python"
        pluginFactory -> jsPlugin "Creates if JavaScript"
        pluginFactory -> cPlugin "Creates if C"
        pluginFactory -> cppPlugin "Creates if C++"
        pluginFactory -> dartPlugin "Creates if Dart"
        pluginFactory -> htmlCssPlugin "Creates if HTML/CSS"
        pluginFactory -> javaPlugin "Creates if Java"
        pluginFactory -> goPlugin "Creates if Go"
        pluginFactory -> rustPlugin "Creates if Rust"
        pluginFactory -> csharpPlugin "Creates if C#"
        pluginFactory -> swiftPlugin "Creates if Swift"
        pluginFactory -> kotlinPlugin "Creates if Kotlin"
        pluginFactory -> typescriptPlugin "Creates if TypeScript"
        pluginFactory -> markdownPlugin "Creates if Markdown"
        pluginFactory -> plaintextPlugin "Creates if PlainText"
        pluginFactory -> genericPlugin "Creates for other languages"
        
        # Plugin inheritance relationships
        pythonPlugin -> semanticPluginBase "Extends"
        jsPlugin -> semanticPluginBase "Extends"
        cPlugin -> semanticPluginBase "Extends"
        cppPlugin -> semanticPluginBase "Extends"
        dartPlugin -> semanticPluginBase "Extends"
        htmlCssPlugin -> semanticPluginBase "Extends"
        javaPlugin -> semanticPluginBase "Extends"
        goPlugin -> semanticPluginBase "Extends"
        rustPlugin -> semanticPluginBase "Extends"
        csharpPlugin -> semanticPluginBase "Extends"
        swiftPlugin -> semanticPluginBase "Extends"
        kotlinPlugin -> semanticPluginBase "Extends"
        typescriptPlugin -> semanticPluginBase "Extends"
        markdownPlugin -> pluginBase "Extends"
        plaintextPlugin -> pluginBase "Extends"
        genericPlugin -> semanticPluginBase "Extends"
        semanticPluginBase -> pluginBase "Extends"
        
        # Indexing relationships
        pythonPlugin -> indexManager "Sends symbols"
        jsPlugin -> indexManager "Sends symbols"
        cPlugin -> indexManager "Sends symbols"
        cppPlugin -> indexManager "Sends symbols"
        dartPlugin -> indexManager "Sends symbols"
        htmlCssPlugin -> indexManager "Sends symbols"
        javaPlugin -> indexManager "Sends symbols"
        goPlugin -> indexManager "Sends symbols"
        rustPlugin -> indexManager "Sends symbols"
        csharpPlugin -> indexManager "Sends symbols"
        swiftPlugin -> indexManager "Sends symbols"
        kotlinPlugin -> indexManager "Sends symbols"
        typescriptPlugin -> indexManager "Sends symbols"
        markdownPlugin -> indexManager "Sends documents"
        plaintextPlugin -> indexManager "Sends documents"
        genericPlugin -> indexManager "Sends symbols"
        indexManager -> sqliteStore "Stores symbols"
        indexManager -> semanticIndexer "Requests embeddings"
        semanticIndexer -> embeddingService "Gets embeddings"
        semanticIndexer -> qdrantStore "Stores vectors"
        queryOptimizer -> sqliteStore "Queries symbols"
        queryOptimizer -> qdrantStore "Semantic search"
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
        component pluginFramework "PluginSystemComponents" {
            include *
            autoLayout
            description "Component diagram showing the plugin system architecture supporting 48 languages"
        }
        
        # Level 3: Component Diagram - Index Engine
        component indexEngine "IndexEngineComponents" {
            include *
            include pluginFramework
            autoLayout
            description "Component diagram showing the indexing and search components"
        }
        
        # Level 3: Component Diagram - Storage
        component storage "StorageComponents" {
            include *
            autoLayout
            description "Component diagram showing the storage layer with SQLite and Qdrant"
        }
        
        # Dynamic view showing indexing flow
        dynamic codeIndexMCP "IndexingFlow" "Shows the flow of indexing a Python file" {
            developer -> claudeCode "Requests file indexing"
            claudeCode -> apiGateway "POST /reindex"
            apiGateway -> dispatcher "Route to indexer"
            dispatcher -> pluginFactory "Get Python plugin"
            pluginFactory -> pythonPlugin "Create/retrieve instance"
            pythonPlugin -> indexManager "Parse and extract symbols"
            indexManager -> sqliteStore "Store symbols"
            indexManager -> semanticIndexer "Generate embeddings"
            semanticIndexer -> embeddingService "Get code embeddings"
            embeddingService -> voyageAI "API: voyage-code-3"
            semanticIndexer -> qdrantStore "Store vectors"
            autoLayout
        }
        
        # Dynamic view showing search flow
        dynamic codeIndexMCP "SearchFlow" "Shows semantic search across multiple languages" {
            developer -> claudeCode "Search: 'calculate fibonacci'"
            claudeCode -> apiGateway "POST /search"
            apiGateway -> dispatcher "Route search"
            dispatcher -> queryOptimizer "Optimize query"
            queryOptimizer -> semanticIndexer "Semantic search"
            semanticIndexer -> qdrantStore "Vector similarity search"
            queryOptimizer -> sqliteStore "FTS5 search"
            queryOptimizer -> dispatcher "Merge results"
            dispatcher -> claudeCode "Return ranked results"
            claudeCode -> developer "Display results"
            autoLayout
        }
        
        # Deployment view
        deployment codeIndexMCP "Production" "ProductionDeployment" {
            deploymentNode "Developer Machine" "Local development environment" {
                deploymentNode "Docker Host" "Docker Engine" {
                    deploymentNode "app-network" "Docker Network" {
                        containerInstance apiGateway
                        containerInstance dispatcher
                        containerInstance pluginFramework
                        containerInstance indexEngine
                        containerInstance fileWatcher
                        containerInstance embeddingService
                    }
                    deploymentNode "Storage Volume" "Persistent storage" {
                        containerInstance storage
                    }
                }
            }
            deploymentNode "Cloud Services" "External services" {
                deploymentNode "Voyage AI Cloud" "voyage.ai" {
                    softwareSystemInstance voyageAI
                }
            }
            autoLayout
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
        }
    }
    
    configuration {
        scope softwaresystem
    }
    
}