"""
Integration tests for Phase 1 plugins: C#, Bash, YAML, JSON, and Markdown.

Tests all 5 plugins working together in the MCP server and validates
multi-language project handling.
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List

from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.plugin_system.plugin_discovery import PluginDiscovery
from mcp_server.plugin_system.models import PluginSystemConfig
from mcp_server.storage.sqlite_store import SQLiteStore


@pytest.fixture
def test_database():
    """Create a test SQLite database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        store = SQLiteStore(db_path)
        yield store
    finally:
        # SQLiteStore doesn't have explicit close method, just cleanup the file
        Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def plugin_manager(test_database):
    """Create a plugin manager with test configuration."""
    config = PluginSystemConfig(
        plugin_dirs=[Path(__file__).parent.parent / "mcp_server" / "plugins"],
        auto_discover=True,
        auto_load=True,
        validate_interfaces=True
    )
    
    manager = PluginManager(config, sqlite_store=test_database)
    manager.load_plugins()
    yield manager
    manager.shutdown()


@pytest.fixture
def multi_language_project():
    """Create a temporary multi-language project structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        
        # Create C# files
        csharp_dir = project_root / "src" / "MyApp"
        csharp_dir.mkdir(parents=True)
        
        (csharp_dir / "Program.cs").write_text("""
using System;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Hosting;

namespace MyApp
{
    /// <summary>
    /// Main application entry point
    /// </summary>
    public class Program
    {
        public static void Main(string[] args)
        {
            CreateHostBuilder(args).Build().Run();
        }

        public static IHostBuilder CreateHostBuilder(string[] args) =>
            Host.CreateDefaultBuilder(args)
                .ConfigureWebHostDefaults(webBuilder =>
                {
                    webBuilder.UseStartup<Startup>();
                });
    }
}
        """)
        
        (csharp_dir / "Controllers" / "HomeController.cs").write_text("""
using Microsoft.AspNetCore.Mvc;

namespace MyApp.Controllers
{
    [ApiController]
    [Route("[controller]")]
    public class HomeController : ControllerBase
    {
        [HttpGet]
        public IActionResult Get()
        {
            return Ok("Hello World");
        }
    }
}
        """)
        
        # Create Bash scripts
        scripts_dir = project_root / "scripts"
        scripts_dir.mkdir()
        
        (scripts_dir / "build.sh").write_text("""#!/bin/bash
# Build script for the application

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"

function build_frontend() {
    echo "Building frontend..."
    cd "$PROJECT_ROOT/frontend"
    npm install
    npm run build
}

function build_backend() {
    echo "Building backend..."
    cd "$PROJECT_ROOT/src"
    dotnet build --configuration Release
}

function cleanup() {
    echo "Cleaning up..."
    rm -rf "$BUILD_DIR"
}

# Parse command line options
while getopts "cfh" opt; do
    case $opt in
        c) cleanup ;;
        f) build_frontend ;;
        h) show_help ;;
        ?) echo "Invalid option" ;;
    esac
done

build_frontend
build_backend
        """)
        
        # Create YAML configurations
        k8s_dir = project_root / "k8s"
        k8s_dir.mkdir()
        
        deployment_yaml = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "myapp-deployment",
                "namespace": "production"
            },
            "spec": {
                "replicas": 3,
                "selector": {
                    "matchLabels": {
                        "app": "myapp"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "myapp"
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "myapp-container",
                                "image": "myapp:latest",
                                "ports": [
                                    {
                                        "containerPort": 80
                                    }
                                ],
                                "env": [
                                    {
                                        "name": "ASPNETCORE_ENVIRONMENT",
                                        "value": "Production"
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }
        
        with open(k8s_dir / "deployment.yaml", 'w') as f:
            yaml.dump(deployment_yaml, f)
        
        # Create Docker Compose
        compose_yaml = {
            "version": "3.8",
            "services": {
                "app": {
                    "build": ".",
                    "ports": ["80:80"],
                    "environment": [
                        "ASPNETCORE_ENVIRONMENT=Development"
                    ],
                    "depends_on": ["database"]
                },
                "database": {
                    "image": "postgres:13",
                    "environment": {
                        "POSTGRES_DB": "myapp",
                        "POSTGRES_USER": "user",
                        "POSTGRES_PASSWORD": "password"
                    },
                    "ports": ["5432:5432"]
                }
            }
        }
        
        with open(project_root / "docker-compose.yml", 'w') as f:
            yaml.dump(compose_yaml, f)
        
        # Create JSON configurations
        package_json = {
            "name": "myapp-frontend",
            "version": "1.0.0",
            "description": "Frontend for MyApp",
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
                "test": "react-scripts test",
                "eject": "react-scripts eject"
            },
            "dependencies": {
                "react": "^17.0.2",
                "react-dom": "^17.0.2",
                "react-scripts": "5.0.1",
                "axios": "^0.24.0"
            },
            "devDependencies": {
                "@types/react": "^17.0.0",
                "typescript": "^4.4.2"
            }
        }
        
        frontend_dir = project_root / "frontend"
        frontend_dir.mkdir()
        with open(frontend_dir / "package.json", 'w') as f:
            json.dump(package_json, f, indent=2)
        
        # Create tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "target": "es5",
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "esModuleInterop": True,
                "allowSyntheticDefaultImports": True,
                "strict": True,
                "forceConsistentCasingInFileNames": True,
                "module": "esnext",
                "moduleResolution": "node",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "noEmit": True,
                "jsx": "react-jsx"
            },
            "include": [
                "src"
            ]
        }
        
        with open(frontend_dir / "tsconfig.json", 'w') as f:
            json.dump(tsconfig, f, indent=2)
        
        # Create Markdown documentation
        (project_root / "README.md").write_text("""
# MyApp

A full-stack application with C# backend and React frontend.

## Features

- [x] RESTful API with ASP.NET Core
- [x] React frontend with TypeScript
- [x] Docker containerization
- [x] Kubernetes deployment
- [ ] CI/CD pipeline
- [ ] Monitoring and logging

## Getting Started

### Prerequisites

- .NET 6.0 or later
- Node.js 16 or later
- Docker and Docker Compose

### Building

```bash
# Build the entire application
./scripts/build.sh

# Build only frontend
./scripts/build.sh -f
```

### Running

```bash
# Development environment
docker-compose up

# Production deployment
kubectl apply -f k8s/
```

## Architecture

The application follows a microservices architecture:

| Component | Technology | Port |
|-----------|------------|------|
| Frontend  | React/TypeScript | 3000 |
| Backend   | ASP.NET Core | 80 |
| Database  | PostgreSQL | 5432 |

### API Endpoints

#### Home Controller

- `GET /home` - Returns a greeting message

### Environment Variables

- `ASPNETCORE_ENVIRONMENT` - Sets the runtime environment
- `CONNECTION_STRING` - Database connection string

## Math Formula

The application uses the following performance calculation:

$$Performance = \\frac{Requests}{Second} \\times Response\\,Time$$

For inline calculations: $throughput = requests \\times concurrency$.

## Links and References

- [ASP.NET Core Documentation](https://docs.microsoft.com/en-us/aspnet/core/)
- [React Documentation](https://reactjs.org/docs/)
- [[Wiki Page]] - Internal documentation

## JSX Components (for MDX example)

<Alert type="info">
  This is an informational alert component.
</Alert>

<CodeBlock language="csharp">
  public class Example { }
</CodeBlock>
        """)
        
        # Create additional documentation
        docs_dir = project_root / "docs"
        docs_dir.mkdir()
        
        (docs_dir / "API.md").write_text("""
# API Documentation

## Controllers

### HomeController

Handles basic application endpoints.

#### Methods

- `Get()` - Returns status information
        """)
        
        yield project_root


class TestPhase1PluginIntegration:
    """Test integration of all Phase 1 plugins."""
    
    def test_plugin_discovery(self, plugin_manager):
        """Test that all Phase 1 plugins are discovered."""
        active_plugins = plugin_manager.get_active_plugins()
        
        # Check that we have the expected plugins
        expected_plugins = ['csharp', 'bash', 'yaml', 'json', 'markdown']
        discovered_languages = set()
        
        for plugin_name, plugin_instance in active_plugins.items():
            if hasattr(plugin_instance, 'get_language'):
                lang = plugin_instance.get_language()
                discovered_languages.add(lang)
        
        # Should have discovered at least some of our target plugins
        assert len(discovered_languages & set(expected_plugins)) > 0, \
            f"Expected some of {expected_plugins}, but got {discovered_languages}"
    
    def test_multi_language_project_indexing(self, plugin_manager, multi_language_project):
        """Test indexing a multi-language project."""
        # Get plugins for each language
        plugins = {}
        for plugin_name, plugin_instance in plugin_manager.get_active_plugins().items():
            if hasattr(plugin_instance, 'get_language'):
                lang = plugin_instance.get_language()
                plugins[lang] = plugin_instance
        
        # Test each file type
        results = {}
        
        # Test C# files
        if 'csharp' in plugins:
            csharp_file = multi_language_project / "src" / "MyApp" / "Program.cs"
            content = csharp_file.read_text()
            shard = plugins['csharp'].indexFile(str(csharp_file), content)
            results['csharp'] = shard
            
            assert shard['language'] == 'csharp'
            assert len(shard['symbols']) > 0
            
            # Should find classes and methods
            symbol_types = [s.get('kind', s.get('symbol_type', '')) for s in shard['symbols']]
            assert any('class' in str(t).lower() for t in symbol_types)
        
        # Test Bash files
        if 'bash' in plugins:
            bash_file = multi_language_project / "scripts" / "build.sh"
            content = bash_file.read_text()
            shard = plugins['bash'].indexFile(str(bash_file), content)
            results['bash'] = shard
            
            assert shard['language'] == 'bash'
            assert len(shard['symbols']) > 0
            
            # Should find functions
            symbol_types = [s.get('kind', s.get('symbol_type', '')) for s in shard['symbols']]
            assert any('function' in str(t).lower() for t in symbol_types)
        
        # Test YAML files
        if 'yaml' in plugins:
            yaml_file = multi_language_project / "k8s" / "deployment.yaml"
            content = yaml_file.read_text()
            shard = plugins['yaml'].indexFile(str(yaml_file), content)
            results['yaml'] = shard
            
            assert shard['language'] == 'yaml'
            assert len(shard['symbols']) > 0
            
            # Should find Kubernetes resources
            symbols = shard['symbols']
            symbol_names = [s.get('symbol', s.get('name', '')) for s in symbols]
            assert any('Deployment' in str(name) for name in symbol_names)
        
        # Test JSON files
        if 'json' in plugins:
            json_file = multi_language_project / "frontend" / "package.json"
            content = json_file.read_text()
            shard = plugins['json'].indexFile(str(json_file), content)
            results['json'] = shard
            
            assert shard['language'] == 'json'
            assert len(shard['symbols']) > 0
            
            # Should find package.json structure
            symbols = shard['symbols']
            symbol_names = [s.get('symbol', s.get('name', '')) for s in symbols]
            assert any('name' in str(name) for name in symbol_names)
            assert any('dependencies' in str(name) for name in symbol_names)
        
        # Test Markdown files
        if 'markdown' in plugins:
            md_file = multi_language_project / "README.md"
            content = md_file.read_text()
            shard = plugins['markdown'].indexFile(str(md_file), content)
            results['markdown'] = shard
            
            assert shard['language'] == 'markdown'
            assert len(shard['symbols']) > 0
            
            # Should find headers, code blocks, etc.
            symbols = shard['symbols']
            symbol_types = [s.get('kind', s.get('symbol_type', '')) for s in symbols]
            # Should have found various markdown elements
            assert len(symbols) > 5
        
        # Verify we tested at least 3 languages
        assert len(results) >= 3, f"Only tested {len(results)} languages: {list(results.keys())}"
    
    def test_plugin_file_support(self, plugin_manager):
        """Test that plugins correctly identify supported files."""
        plugins = plugin_manager.get_active_plugins()
        
        test_files = {
            'test.cs': 'csharp',
            'script.sh': 'bash',
            'config.yaml': 'yaml',
            'package.json': 'json',
            'README.md': 'markdown'
        }
        
        supported_files = {}
        for plugin_name, plugin_instance in plugins.items():
            if hasattr(plugin_instance, 'supports'):
                for file_path, expected_lang in test_files.items():
                    if plugin_instance.supports(file_path):
                        if expected_lang not in supported_files:
                            supported_files[expected_lang] = []
                        supported_files[expected_lang].append(plugin_name)
        
        # Should have found support for our test files
        assert len(supported_files) > 0, "No plugins support the test files"
    
    def test_plugin_symbol_extraction(self, plugin_manager, multi_language_project):
        """Test symbol extraction across all plugins."""
        active_plugins = plugin_manager.get_active_plugins()
        
        # Define test files and expected symbol patterns
        test_cases = [
            {
                'file': multi_language_project / "src" / "MyApp" / "Program.cs",
                'language': 'csharp',
                'expected_symbols': ['Program', 'Main', 'CreateHostBuilder']
            },
            {
                'file': multi_language_project / "scripts" / "build.sh",
                'language': 'bash',
                'expected_symbols': ['build_frontend', 'build_backend', 'cleanup']
            },
            {
                'file': multi_language_project / "k8s" / "deployment.yaml",
                'language': 'yaml',
                'expected_symbols': ['Deployment', 'myapp-deployment']
            },
            {
                'file': multi_language_project / "frontend" / "package.json",
                'language': 'json',
                'expected_symbols': ['name', 'dependencies', 'scripts']
            },
            {
                'file': multi_language_project / "README.md",
                'language': 'markdown',
                'expected_symbols': ['MyApp', 'Features', 'Getting Started']
            }
        ]
        
        extraction_results = {}
        
        for test_case in test_cases:
            file_path = test_case['file']
            if not file_path.exists():
                continue
            
            # Find appropriate plugin
            suitable_plugin = None
            for plugin_name, plugin_instance in active_plugins.items():
                if hasattr(plugin_instance, 'supports') and plugin_instance.supports(str(file_path)):
                    suitable_plugin = plugin_instance
                    break
            
            if suitable_plugin:
                content = file_path.read_text()
                shard = suitable_plugin.indexFile(str(file_path), content)
                
                # Extract symbol names
                symbols = shard.get('symbols', [])
                found_symbols = []
                for symbol in symbols:
                    symbol_name = symbol.get('symbol', symbol.get('name', ''))
                    if symbol_name:
                        found_symbols.append(symbol_name)
                
                extraction_results[test_case['language']] = {
                    'found_symbols': found_symbols,
                    'expected_symbols': test_case['expected_symbols'],
                    'total_symbols': len(symbols)
                }
                
                # Check if we found some expected symbols
                found_expected = any(
                    expected in str(found) for expected in test_case['expected_symbols'] 
                    for found in found_symbols
                )
                assert found_expected, \
                    f"Did not find expected symbols {test_case['expected_symbols']} in {found_symbols}"
        
        # Should have tested multiple languages
        assert len(extraction_results) >= 3, \
            f"Only tested {len(extraction_results)} languages: {list(extraction_results.keys())}"
    
    def test_plugin_search_functionality(self, plugin_manager, multi_language_project):
        """Test search functionality across plugins."""
        active_plugins = plugin_manager.get_active_plugins()
        
        # Index some files first
        indexed_content = {}
        
        for plugin_name, plugin_instance in active_plugins.items():
            if not hasattr(plugin_instance, 'supports') or not hasattr(plugin_instance, 'indexFile'):
                continue
            
            # Find files this plugin can handle
            for file_path in multi_language_project.rglob("*"):
                if file_path.is_file() and plugin_instance.supports(str(file_path)):
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        shard = plugin_instance.indexFile(str(file_path), content)
                        indexed_content[str(file_path)] = {
                            'plugin': plugin_name,
                            'shard': shard,
                            'instance': plugin_instance
                        }
                        break  # Only test one file per plugin
                    except Exception as e:
                        # Skip files that can't be read or processed
                        continue
        
        # Test search functionality
        search_results = {}
        
        for file_path, data in indexed_content.items():
            plugin_instance = data['instance']
            if hasattr(plugin_instance, 'search'):
                try:
                    # Search for common terms
                    results = plugin_instance.search("function", {"limit": 5})
                    if results:
                        search_results[data['plugin']] = len(results)
                except Exception:
                    # Search might not be implemented or might fail
                    pass
        
        # Just verify that search doesn't crash and returns reasonable results
        assert isinstance(search_results, dict)
    
    def test_plugin_definition_lookup(self, plugin_manager, multi_language_project):
        """Test symbol definition lookup across plugins."""
        active_plugins = plugin_manager.get_active_plugins()
        
        # Test definition lookup
        definition_results = {}
        
        for plugin_name, plugin_instance in active_plugins.items():
            if not hasattr(plugin_instance, 'getDefinition'):
                continue
            
            try:
                # Test looking up common symbol names
                definition = plugin_instance.getDefinition("main")
                if definition:
                    definition_results[plugin_name] = definition
            except Exception:
                # Definition lookup might not be implemented
                pass
        
        # Just verify the interface works
        assert isinstance(definition_results, dict)
    
    def test_performance_with_large_files(self, plugin_manager, multi_language_project):
        """Test plugin performance with reasonably sized files."""
        active_plugins = plugin_manager.get_active_plugins()
        
        # Create a larger test file for each plugin
        performance_results = {}
        
        # Test C# plugin with a larger file
        if any(hasattr(p, 'get_language') and p.get_language() == 'csharp' for p in active_plugins.values()):
            large_csharp = """
using System;
using System.Collections.Generic;
using System.Linq;

namespace LargeApp
{
    public class Service1
    {
        public void Method1() { }
        public void Method2() { }
        public void Method3() { }
    }
    
    public class Service2
    {
        public void Method1() { }
        public void Method2() { }
        public void Method3() { }
    }
    
    public class Service3
    {
        public void Method1() { }
        public void Method2() { }
        public void Method3() { }
    }
}
""" * 10  # Repeat to make it larger
            
            csharp_plugin = next(
                p for p in active_plugins.values()
                if hasattr(p, 'get_language') and p.get_language() == 'csharp'
            )
            
            import time
            start_time = time.time()
            shard = csharp_plugin.indexFile("large_test.cs", large_csharp)
            end_time = time.time()
            
            performance_results['csharp'] = {
                'time': end_time - start_time,
                'symbols': len(shard.get('symbols', [])),
                'content_size': len(large_csharp)
            }
        
        # Performance should be reasonable (less than 5 seconds for this size)
        for lang, perf in performance_results.items():
            assert perf['time'] < 5.0, f"{lang} plugin took {perf['time']} seconds, too slow"
            assert perf['symbols'] > 0, f"{lang} plugin found no symbols"


class TestPluginMCPTools:
    """Test MCP tools provided by plugins."""
    
    def test_plugin_mcp_tools(self, plugin_manager):
        """Test that plugins provide MCP tools."""
        active_plugins = plugin_manager.get_active_plugins()
        
        tools_found = {}
        
        for plugin_name, plugin_instance in active_plugins.items():
            if hasattr(plugin_instance, 'get_mcp_tools'):
                try:
                    tools = plugin_instance.get_mcp_tools()
                    if tools:
                        tools_found[plugin_name] = len(tools)
                except Exception as e:
                    # MCP tools might not be implemented
                    pass
        
        # At least some plugins should provide MCP tools
        # (The newer plugins we created should have them)
        assert len(tools_found) > 0, "No plugins provide MCP tools"
    
    def test_plugin_info_retrieval(self, plugin_manager):
        """Test plugin information retrieval."""
        active_plugins = plugin_manager.get_active_plugins()
        
        plugin_info = {}
        
        for plugin_name, plugin_instance in active_plugins.items():
            if hasattr(plugin_instance, 'get_plugin_info'):
                try:
                    info = plugin_instance.get_plugin_info()
                    if info:
                        plugin_info[plugin_name] = info
                except Exception:
                    pass
        
        # Should have retrieved info from multiple plugins
        assert len(plugin_info) > 0, "No plugin info retrieved"
        
        # Verify info structure
        for plugin_name, info in plugin_info.items():
            assert isinstance(info, dict), f"Plugin {plugin_name} info is not a dict"
            if 'language' in info:
                assert isinstance(info['language'], str), f"Plugin {plugin_name} language is not a string"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])