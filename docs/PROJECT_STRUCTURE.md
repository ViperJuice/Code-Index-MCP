# Project Structure
Updated: 2025-01-06

## Overview
This document describes the organized structure of the Code-Index-MCP project after the root directory consolidation.

## Root Directory
The root directory has been streamlined to contain only essential files:

### MCP Core Files (Must Stay in Root)
- `mcp_server/` - Core MCP server implementation
- `mcp-index-kit/` - MCP indexing toolkit
- `.mcp-index/` - MCP index data
- `.mcp-index.json` - MCP index configuration
- `.mcp.json` - MCP server configuration
- `.mcp.json.example` - MCP config example
- `.mcp-index-ignore` - MCP ignore patterns

### AI & Architecture (Must Stay in Root)
- `ai_docs/` - AI framework documentation
- `architecture/` - System architecture docs and diagrams
- `.claude/` - Claude AI configuration
- `.claude.json` - Claude config file
- `.cursor/` - Cursor IDE configuration
- `AGENTS.md` - AI agent instructions
- `CLAUDE.md` - Claude navigation stub

### Essential Documentation
- `README.md` - Project overview
- `LICENSE` - MIT license
- `CHANGELOG.md` - Version history
- `CODE_OF_CONDUCT.md` - Community standards
- `CONTRIBUTING.md` - Contribution guidelines
- `ROADMAP.md` - Development roadmap
- `SECURITY.md` - Security policy
- `TROUBLESHOOTING.md` - Common issues

### Python Configuration
- `requirements.txt` - Python dependencies
- `requirements-production.txt` - Production dependencies
- `pyproject.toml` - Python project config
- `pytest.ini` - Pytest configuration
- `tox.ini` - Testing configuration

### Build & Deploy
- `Makefile` - Build automation
- `docker-compose.yml` - Main Docker composition
- `docker-compose.mcp.yml` - MCP-specific Docker config
- `plugins.yaml` - Plugin configuration

### Essential Scripts
- `dev.sh` - Development helper script
- `docker-setup.sh` - Docker initialization
- `setup-documentation.sh` - Documentation setup

## Organized Directories

### `/scripts/`
Organized scripts by function:
```
scripts/
├── cli/
│   ├── mcp_cli.py              # MCP command-line interface
│   └── mcp_server_cli.py       # Server CLI
├── development/
│   ├── scaffold_code.py        # Code scaffolding
│   └── scaffold_mcp.sh         # MCP scaffolding
├── testing/
│   └── simple_test.py          # Simple test runner
└── utilities/                  # Various utility scripts
```

### `/docker/`
Docker-related files:
```
docker/
├── compose/
│   ├── development/
│   │   ├── docker-compose.dev.yml
│   │   └── docker-compose.development.yml
│   └── production/
│       ├── docker-compose.production.yml
│       └── docker-compose.monitoring.yml
└── dockerfiles/
    └── [Various Dockerfiles]
```

### `/tests/`
Test organization:
```
tests/
├── fixtures/
│   ├── complete_behavior/      # Complete behavior test files
│   ├── files/                  # Test file samples
│   ├── repos/                  # Test repositories
│   └── data/                   # Test data files
├── results/                    # Test output and results
├── coverage/                   # Coverage reports
├── post_migration/             # Migration validation tests
└── [Test modules]
```

### `/data/`
Data and index storage:
```
data/
├── indexes/
│   └── vector_index.qdrant/    # Vector search index
└── databases/
    └── [SQLite databases]
```

### `/monitoring/`
Monitoring configuration:
```
monitoring/
├── config/
│   └── prometheus.yml          # Prometheus configuration
├── grafana/                    # Grafana dashboards
└── prometheus/                 # Prometheus rules
```

### `/docs/`
Documentation:
```
docs/
├── api/                        # API documentation
├── configuration/              # Configuration guides
├── development/                # Development guides
├── guides/                     # User guides
├── history/                    # Historical docs
├── implementation/             # Implementation details
├── performance/                # Performance reports
├── plugins/                    # Plugin documentation
├── reports/                    # Various reports
├── status/                     # Status updates
├── templates/                  # Document templates
├── tools/                      # Tool documentation
└── validation/                 # Validation reports
```

## File Movement Summary

### Scripts Moved
- `mcp_cli.py` → `scripts/cli/`
- `mcp_server_cli.py` → `scripts/cli/`
- `scaffold_code.py` → `scripts/development/`
- `scaffold_mcp.sh` → `scripts/development/`
- `simple_test.py` → `scripts/testing/`

### Docker Files Moved
- `docker-compose.dev.yml` → `docker/compose/development/`
- `docker-compose.development.yml` → `docker/compose/development/`
- `docker-compose.production.yml` → `docker/compose/production/`
- `docker-compose.monitoring.yml` → `docker/compose/production/`

### Configuration Moved
- `prometheus.yml` → `monitoring/config/`

### Test Directories Moved
- `test_complete_behavior/` → `tests/fixtures/complete_behavior/`
- `test_files/` → `tests/fixtures/files/`
- `test_repos/` → `tests/fixtures/repos/`
- `test_data/` → `tests/fixtures/data/`
- `test_results/` → `tests/results/`
- `htmlcov/` → `tests/coverage/`

### Data Moved
- `vector_index.qdrant/` → `data/indexes/`

## Updated References

### Makefile
- Docker compose paths updated to reference new locations
- Example: `-f docker/compose/development/docker-compose.dev.yml`

### docker-compose.yml
- Prometheus config path updated: `./monitoring/config/prometheus.yml`

### .gitignore
- Updated paths for moved directories
- Added new test result locations

### Test Files
- Updated hardcoded paths in test files
- Example: `test_repos/` → `tests/fixtures/repos/`

## Benefits of New Structure

1. **Cleaner Root Directory**: Reduced from 44+ files to ~30 essential files
2. **Logical Organization**: Related files grouped together
3. **MCP Compliance**: Preserves standard MCP server structure
4. **Easy Navigation**: Clear directory hierarchy
5. **Better Maintenance**: Easier to find and manage files

## Migration Validation

A post-migration test script is available at:
`tests/post_migration/test_mcp_functionality.py`

This script verifies:
- All moved files exist in their new locations
- MCP server functionality remains intact
- File references are properly updated
- No functionality has been broken