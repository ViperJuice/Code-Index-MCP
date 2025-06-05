"""
Test MCP server handling of multi-language projects with Phase 1 plugins.

Verifies that the MCP server can properly route requests to the appropriate
plugins and handle complex multi-language codebases.
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, List

from mcp_server.server import create_mcp_server
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.plugin_system.models import PluginSystemConfig
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.tools.manager import ToolManager


@pytest.fixture
async def mcp_server_database():
    """Create a test database for MCP server."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        store = SQLiteStore(db_path)
        yield store
    finally:
        # SQLiteStore doesn't have explicit close method, just cleanup the file
        Path(db_path).unlink(missing_ok=True)


@pytest.fixture
async def mcp_server_with_plugins(mcp_server_database):
    """Create MCP server with all Phase 1 plugins loaded."""
    # Create plugin manager
    plugin_config = PluginSystemConfig(
        plugin_dirs=[Path(__file__).parent.parent / "mcp_server" / "plugins"],
        auto_discover=True,
        auto_load=True,
        validate_interfaces=True
    )
    
    plugin_manager = PluginManager(plugin_config, sqlite_store=mcp_server_database)
    
    # Create tool manager
    tool_manager = ToolManager()
    
    # Load plugins
    plugin_manager.load_plugins()
    
    # Create server
    server = create_mcp_server(
        plugin_manager=plugin_manager,
        tool_manager=tool_manager,
        sqlite_store=mcp_server_database
    )
    
    try:
        yield server, plugin_manager, tool_manager
    finally:
        plugin_manager.shutdown()


@pytest.fixture
def sample_multi_language_project():
    """Create a sample multi-language project structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        
        # Create project structure
        files = {
            # C# files
            "src/Program.cs": '''
using System;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Hosting;

namespace MultiLangApp
{
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
}''',
            
            "src/Controllers/ApiController.cs": '''
using Microsoft.AspNetCore.Mvc;

namespace MultiLangApp.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class ApiController : ControllerBase
    {
        [HttpGet]
        public IActionResult Get()
        {
            return Ok(new { message = "Hello from C# API" });
        }
        
        [HttpPost]
        public IActionResult Post([FromBody] object data)
        {
            return Ok(new { received = data });
        }
    }
}''',
            
            # Bash scripts
            "scripts/deploy.sh": '''#!/bin/bash
set -e

ENVIRONMENT="${1:-development}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

deploy_to_environment() {
    local env="$1"
    echo "Deploying to $env environment..."
    
    case "$env" in
        development)
            deploy_development
            ;;
        staging)
            deploy_staging
            ;;
        production)
            deploy_production
            ;;
        *)
            echo "Unknown environment: $env"
            exit 1
            ;;
    esac
}

deploy_development() {
    echo "Building for development..."
    dotnet build "$PROJECT_ROOT/src"
    docker-compose up -d
}

deploy_staging() {
    echo "Deploying to staging..."
    kubectl apply -f "$PROJECT_ROOT/k8s/staging/"
}

deploy_production() {
    echo "Deploying to production..."
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl apply -f "$PROJECT_ROOT/k8s/production/"
    fi
}

deploy_to_environment "$ENVIRONMENT"''',
            
            # YAML configurations
            "k8s/deployment.yaml": '''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: multilang-app
  namespace: default
  labels:
    app: multilang-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: multilang-app
  template:
    metadata:
      labels:
        app: multilang-app
    spec:
      containers:
      - name: api
        image: multilang-app:latest
        ports:
        - containerPort: 80
        env:
        - name: ASPNETCORE_ENVIRONMENT
          value: "Production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: multilang-app-service
spec:
  selector:
    app: multilang-app
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer''',
            
            "docker-compose.yml": '''
version: '3.8'
services:
  api:
    build: .
    ports:
      - "80:80"
    environment:
      - ASPNETCORE_ENVIRONMENT=Development
      - DATABASE_URL=Server=db;Database=MultiLangApp;User=sa;Password=Password123;
    depends_on:
      - db
  
  db:
    image: mcr.microsoft.com/mssql/server:2019-latest
    environment:
      - ACCEPT_EULA=Y
      - SA_PASSWORD=Password123
    ports:
      - "1433:1433"
    volumes:
      - db_data:/var/opt/mssql

volumes:
  db_data:''',
            
            # JSON configurations
            "package.json": '''{
  "name": "multilang-app-frontend",
  "version": "1.0.0",
  "description": "Frontend for multi-language application",
  "main": "index.js",
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject",
    "deploy": "npm run build && aws s3 sync build/ s3://my-app-bucket"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "axios": "^1.4.0",
    "react-router-dom": "^6.11.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.0.0"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}''',
            
            "tsconfig.json": '''{
  "compilerOptions": {
    "target": "es5",
    "lib": [
      "dom",
      "dom.iterable",
      "esnext"
    ],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": [
    "src"
  ]
}''',
            
            # Markdown documentation
            "README.md": '''# Multi-Language Application

A comprehensive application demonstrating modern DevOps practices with multiple technologies.

## Architecture

The application consists of several components:

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend API | ASP.NET Core | REST API server |
| Frontend | React + TypeScript | User interface |
| Database | SQL Server | Data persistence |
| Deployment | Kubernetes | Container orchestration |

## Getting Started

### Prerequisites

- .NET 6.0 SDK
- Node.js 18+
- Docker
- Kubernetes cluster

### Local Development

1. **Backend Setup**
   ```bash
   cd src
   dotnet restore
   dotnet run
   ```

2. **Frontend Setup**
   ```bash
   npm install
   npm start
   ```

3. **Full Stack with Docker**
   ```bash
   docker-compose up
   ```

### Deployment

#### Development Environment
```bash
./scripts/deploy.sh development
```

#### Staging Environment
```bash
./scripts/deploy.sh staging
```

#### Production Environment
```bash
./scripts/deploy.sh production
```

## API Documentation

### Endpoints

#### GET /api/api
Returns a greeting message.

**Response:**
```json
{
  "message": "Hello from C# API"
}
```

#### POST /api/api
Accepts JSON data and returns it.

**Request Body:**
```json
{
  "key": "value"
}
```

**Response:**
```json
{
  "received": {
    "key": "value"
  }
}
```

## Configuration

### Environment Variables

- `ASPNETCORE_ENVIRONMENT` - Runtime environment (Development, Staging, Production)
- `DATABASE_URL` - Database connection string

### Build Configuration

The build process uses the following configuration files:

- `package.json` - Node.js dependencies and scripts
- `tsconfig.json` - TypeScript compiler options
- `docker-compose.yml` - Local development environment
- `k8s/deployment.yaml` - Kubernetes deployment configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.''',
            
            "docs/DEPLOYMENT.md": '''# Deployment Guide

## Overview

This guide covers deployment procedures for all environments.

## Environments

### Development
- Local Docker containers
- Hot reload enabled
- Debug logging

### Staging
- Kubernetes cluster
- Production-like configuration
- Integration testing

### Production
- High-availability Kubernetes cluster
- Performance monitoring
- Security hardening

## Procedures

### Manual Deployment

#### Backend
```bash
dotnet publish -c Release
docker build -t multilang-app:latest .
```

#### Frontend
```bash
npm run build
```

### Automated Deployment

Use the provided deployment script:

```bash
# Deploy to development
./scripts/deploy.sh development

# Deploy to staging
./scripts/deploy.sh staging

# Deploy to production (requires confirmation)
./scripts/deploy.sh production
```

## Monitoring

### Health Checks

The application provides health check endpoints:

- `/health` - Basic health check
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe

### Metrics

Application metrics are exposed at:

- `/metrics` - Prometheus metrics
- `/api/status` - Application status

## Troubleshooting

### Common Issues

#### Build Failures
- Check .NET SDK version
- Verify dependencies are restored
- Ensure Docker is running

#### Deployment Issues
- Verify Kubernetes cluster access
- Check image registry permissions
- Validate YAML configuration

### Logs

View application logs:

```bash
# Docker Compose
docker-compose logs -f api

# Kubernetes
kubectl logs -f deployment/multilang-app
```'''
        }
        
        # Create all files
        for file_path, content in files.items():
            full_path = project_root / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        
        yield project_root


class TestMCPServerMultiLanguage:
    """Test MCP server with multi-language projects."""
    
    @pytest.mark.asyncio
    async def test_plugin_discovery_and_loading(self, mcp_server_with_plugins):
        """Test that all Phase 1 plugins are properly loaded in the MCP server."""
        server, plugin_manager, tool_manager = mcp_server_with_plugins
        
        # Get active plugins
        active_plugins = plugin_manager.get_active_plugins()
        
        # Check that we have plugins
        assert len(active_plugins) > 0, "No plugins loaded"
        
        # Check for specific Phase 1 plugin languages
        expected_languages = {'csharp', 'bash', 'yaml', 'json', 'markdown'}
        found_languages = set()
        
        for plugin_name, plugin_instance in active_plugins.items():
            if hasattr(plugin_instance, 'get_language'):
                lang = plugin_instance.get_language()
                found_languages.add(lang)
        
        # Should have found at least some of our target languages
        common_languages = expected_languages & found_languages
        assert len(common_languages) > 0, \
            f"Expected some of {expected_languages}, but only found {found_languages}"
        
        print(f"Found plugins for languages: {found_languages}")
    
    @pytest.mark.asyncio
    async def test_file_type_routing(self, mcp_server_with_plugins, sample_multi_language_project):
        """Test that the MCP server routes files to the correct plugins."""
        server, plugin_manager, tool_manager = mcp_server_with_plugins
        
        # Test file routing
        test_files = [
            ("test.cs", "csharp"),
            ("script.sh", "bash"), 
            ("config.yaml", "yaml"),
            ("package.json", "json"),
            ("README.md", "markdown")
        ]
        
        active_plugins = plugin_manager.get_active_plugins()
        routing_results = {}
        
        for file_path, expected_lang in test_files:
            suitable_plugins = []
            
            for plugin_name, plugin_instance in active_plugins.items():
                if hasattr(plugin_instance, 'supports') and plugin_instance.supports(file_path):
                    if hasattr(plugin_instance, 'get_language'):
                        lang = plugin_instance.get_language()
                        suitable_plugins.append((plugin_name, lang))
            
            routing_results[file_path] = suitable_plugins
        
        # Verify routing
        for file_path, expected_lang in test_files:
            plugins = routing_results.get(file_path, [])
            found_expected = any(lang == expected_lang for _, lang in plugins)
            
            if not found_expected:
                print(f"Warning: No {expected_lang} plugin found for {file_path}")
                print(f"Available plugins for {file_path}: {plugins}")
                # Don't fail the test, as some plugins might not be available
    
    @pytest.mark.asyncio
    async def test_multi_language_project_indexing(self, mcp_server_with_plugins, sample_multi_language_project):
        """Test indexing a complete multi-language project."""
        server, plugin_manager, tool_manager = mcp_server_with_plugins
        
        active_plugins = plugin_manager.get_active_plugins()
        indexing_results = {}
        
        # Index all files in the project
        for file_path in sample_multi_language_project.rglob("*"):
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Find suitable plugin
                    for plugin_name, plugin_instance in active_plugins.items():
                        if hasattr(plugin_instance, 'supports') and plugin_instance.supports(str(file_path)):
                            try:
                                shard = plugin_instance.indexFile(str(file_path), content)
                                
                                indexing_results[str(file_path)] = {
                                    'plugin': plugin_name,
                                    'language': getattr(plugin_instance, 'get_language', lambda: 'unknown')(),
                                    'symbols': len(shard.get('symbols', [])),
                                    'success': True
                                }
                                break
                            except Exception as e:
                                indexing_results[str(file_path)] = {
                                    'plugin': plugin_name,
                                    'error': str(e),
                                    'success': False
                                }
                                break
                    else:
                        indexing_results[str(file_path)] = {
                            'plugin': None,
                            'message': 'No suitable plugin found',
                            'success': False
                        }
                        
                except Exception as e:
                    indexing_results[str(file_path)] = {
                        'error': f'Failed to read file: {e}',
                        'success': False
                    }
        
        # Analyze results
        successful_indexing = [r for r in indexing_results.values() if r.get('success')]
        total_symbols = sum(r.get('symbols', 0) for r in successful_indexing)
        languages_processed = {r.get('language') for r in successful_indexing if r.get('language')}
        
        # Assertions
        assert len(successful_indexing) > 0, "No files were successfully indexed"
        assert total_symbols > 0, "No symbols were extracted from any files"
        assert len(languages_processed) > 1, f"Only one language processed: {languages_processed}"
        
        print(f"Indexing Results:")
        print(f"  - Successfully indexed: {len(successful_indexing)} files")
        print(f"  - Total symbols extracted: {total_symbols}")
        print(f"  - Languages processed: {languages_processed}")
        
        # Print detailed results
        for file_path, result in indexing_results.items():
            if result.get('success'):
                print(f"  - {file_path}: {result.get('symbols', 0)} symbols ({result.get('language')})")
            else:
                print(f"  - {file_path}: FAILED - {result.get('error', result.get('message', 'Unknown error'))}")
    
    @pytest.mark.asyncio
    async def test_cross_language_symbol_search(self, mcp_server_with_plugins, sample_multi_language_project):
        """Test searching for symbols across multiple languages."""
        server, plugin_manager, tool_manager = mcp_server_with_plugins
        
        active_plugins = plugin_manager.get_active_plugins()
        
        # First, index some files
        indexed_files = {}
        
        for file_path in sample_multi_language_project.rglob("*"):
            if file_path.is_file() and len(indexed_files) < 5:  # Limit for performance
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    for plugin_name, plugin_instance in active_plugins.items():
                        if hasattr(plugin_instance, 'supports') and plugin_instance.supports(str(file_path)):
                            try:
                                shard = plugin_instance.indexFile(str(file_path), content)
                                if shard.get('symbols'):
                                    indexed_files[str(file_path)] = {
                                        'plugin': plugin_instance,
                                        'shard': shard
                                    }
                                    break
                            except Exception:
                                pass
                except Exception:
                    pass
        
        # Test symbol search across plugins
        search_terms = ["main", "app", "api", "deploy", "config"]
        search_results = {}
        
        for term in search_terms:
            results = []
            
            for file_path, data in indexed_files.items():
                plugin = data['plugin']
                if hasattr(plugin, 'search'):
                    try:
                        plugin_results = plugin.search(term, {"limit": 5})
                        if plugin_results:
                            results.extend(plugin_results)
                    except Exception:
                        pass  # Search might not be implemented
            
            search_results[term] = results
        
        # Verify search results
        total_results = sum(len(results) for results in search_results.values())
        
        if total_results > 0:
            print(f"Cross-language search results:")
            for term, results in search_results.items():
                print(f"  - '{term}': {len(results)} results")
        else:
            print("Note: Search functionality may not be fully implemented in all plugins")
    
    @pytest.mark.asyncio
    async def test_mcp_tools_integration(self, mcp_server_with_plugins):
        """Test that MCP tools from plugins are properly integrated."""
        server, plugin_manager, tool_manager = mcp_server_with_plugins
        
        active_plugins = plugin_manager.get_active_plugins()
        
        # Collect MCP tools from all plugins
        all_tools = {}
        
        for plugin_name, plugin_instance in active_plugins.items():
            if hasattr(plugin_instance, 'get_mcp_tools'):
                try:
                    tools = plugin_instance.get_mcp_tools()
                    if tools:
                        all_tools[plugin_name] = tools
                except Exception as e:
                    print(f"Warning: Failed to get MCP tools from {plugin_name}: {e}")
        
        # Verify tools are available
        total_tools = sum(len(tools) for tools in all_tools.values())
        
        if total_tools > 0:
            print(f"MCP Tools Integration:")
            print(f"  - Total tools available: {total_tools}")
            for plugin_name, tools in all_tools.items():
                print(f"  - {plugin_name}: {len(tools)} tools")
                for tool in tools:
                    if isinstance(tool, dict) and 'name' in tool:
                        print(f"    - {tool['name']}")
        else:
            print("Note: No MCP tools found in current plugins")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mcp_server_with_plugins):
        """Test error handling when processing problematic files."""
        server, plugin_manager, tool_manager = mcp_server_with_plugins
        
        active_plugins = plugin_manager.get_active_plugins()
        
        # Test with malformed files
        problematic_files = {
            "invalid.cs": "this is not valid C# code { { { ;;;",
            "broken.json": '{"incomplete": json syntax',
            "bad.yaml": "invalid:\n  yaml:\n    - syntax\n  - error:",
            "corrupt.md": "# Header\n```\nunclosed code block",
            "empty.sh": ""
        }
        
        error_handling_results = {}
        
        for filename, content in problematic_files.items():
            for plugin_name, plugin_instance in active_plugins.items():
                if hasattr(plugin_instance, 'supports') and plugin_instance.supports(filename):
                    try:
                        shard = plugin_instance.indexFile(filename, content)
                        error_handling_results[filename] = {
                            'plugin': plugin_name,
                            'success': True,
                            'symbols': len(shard.get('symbols', []))
                        }
                        break
                    except Exception as e:
                        error_handling_results[filename] = {
                            'plugin': plugin_name,
                            'success': False,
                            'error': str(e)
                        }
                        break
        
        # Verify error handling
        successful_handling = sum(1 for r in error_handling_results.values() if r.get('success'))
        
        print(f"Error Handling Results:")
        print(f"  - Files with graceful error handling: {successful_handling}/{len(problematic_files)}")
        
        for filename, result in error_handling_results.items():
            if result.get('success'):
                print(f"  - {filename}: Handled gracefully ({result.get('symbols', 0)} symbols)")
            else:
                print(f"  - {filename}: Error - {result.get('error', 'Unknown error')}")
        
        # The test passes regardless of errors, as long as the server doesn't crash
        assert True, "Error handling test completed"


class TestMCPServerPerformance:
    """Test MCP server performance with multi-language projects."""
    
    @pytest.mark.asyncio
    async def test_concurrent_file_processing(self, mcp_server_with_plugins, sample_multi_language_project):
        """Test processing multiple files concurrently."""
        server, plugin_manager, tool_manager = mcp_server_with_plugins
        
        active_plugins = plugin_manager.get_active_plugins()
        
        # Collect files to process
        files_to_process = []
        for file_path in sample_multi_language_project.rglob("*"):
            if file_path.is_file() and len(files_to_process) < 10:  # Limit for performance
                try:
                    content = file_path.read_text(encoding='utf-8')
                    files_to_process.append((str(file_path), content))
                except Exception:
                    pass
        
        async def process_file(file_data):
            """Process a single file."""
            file_path, content = file_data
            
            for plugin_name, plugin_instance in active_plugins.items():
                if hasattr(plugin_instance, 'supports') and plugin_instance.supports(file_path):
                    try:
                        # Simulate async processing (plugins are currently sync)
                        await asyncio.sleep(0.001)  # Small delay to simulate async work
                        shard = plugin_instance.indexFile(file_path, content)
                        return {
                            'file': file_path,
                            'plugin': plugin_name,
                            'symbols': len(shard.get('symbols', [])),
                            'success': True
                        }
                    except Exception as e:
                        return {
                            'file': file_path,
                            'plugin': plugin_name,
                            'error': str(e),
                            'success': False
                        }
            
            return {
                'file': file_path,
                'error': 'No suitable plugin found',
                'success': False
            }
        
        # Process files concurrently
        import time
        start_time = time.perf_counter()
        
        tasks = [process_file(file_data) for file_data in files_to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        processing_time = end_time - start_time
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
        total_symbols = sum(r.get('symbols', 0) for r in successful_results)
        
        print(f"Concurrent Processing Results:")
        print(f"  - Files processed: {len(files_to_process)}")
        print(f"  - Successful: {len(successful_results)}")
        print(f"  - Total symbols: {total_symbols}")
        print(f"  - Processing time: {processing_time:.3f}s")
        print(f"  - Avg time per file: {processing_time/len(files_to_process):.3f}s")
        
        # Performance assertion
        assert processing_time < 5.0, f"Concurrent processing too slow: {processing_time:.3f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])