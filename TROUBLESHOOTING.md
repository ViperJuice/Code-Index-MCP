# Troubleshooting Guide

## 🤖 AI Agent Instructions
> **AI Agents:** When encountering issues, check this guide first. For new troubleshooting patterns, update `AGENTS.md` with the solution.

## Common Issues and Solutions

### Installation Issues

#### Problem: Tree-sitter build fails
```
ERROR: Failed building wheel for tree-sitter
```
**Solution:**
```bash
# Install build dependencies
sudo apt-get install build-essential python3-dev  # Ubuntu/Debian
brew install python3  # macOS

# Reinstall tree-sitter
pip install --no-binary tree-sitter tree-sitter
```

#### Problem: Missing language parsers
```
FileNotFoundError: Language parser not found
```
**Solution:**
```bash
# Download and install language parsers
python scripts/setup-mcp-index.sh
```

### API and Connection Issues

#### Problem: MCP server won't start
```
Error: Address already in use
```
**Solution:**
```bash
# Check for existing processes
lsof -i :5173
# Kill the process or use a different port
MCP_PORT=5174 python -m mcp_server
```

#### Problem: Voyage AI API errors
```
Error: Invalid API key or rate limit exceeded
```
**Solution:**
1. Verify API key: `echo $VOYAGE_API_KEY`
2. Check rate limits in Voyage AI dashboard
3. Implement exponential backoff (already included)

#### Problem: Qdrant connection failed
```
ConnectionError: Cannot connect to Qdrant
```
**Solution:**
```bash
# Start Qdrant container
docker run -p 6333:6333 qdrant/qdrant

# Verify connection
curl http://localhost:6333/health
```

### Indexing Issues

#### Problem: Slow indexing performance
**Symptoms:** Indexing takes hours for large repos
**Solution:**
1. Enable distributed processing:
   ```bash
   docker-compose -f docker-compose.distributed.yml up -d
   ```
2. Increase worker count:
   ```bash
   WORKER_COUNT=10 python -m mcp_server
   ```
3. Check cache configuration

#### Problem: Out of memory during indexing
**Solution:**
```bash
# Increase memory limits
export INDEXER_BATCH_SIZE=100  # Default: 1000
export MAX_MEMORY_MB=4096      # Default: 2048
```

#### Problem: Symbols not found after indexing
**Checklist:**
1. Verify file was indexed: `SELECT * FROM files WHERE path LIKE '%filename%';`
2. Check language plugin loaded: `python -m mcp_server plugins list`
3. Verify parser working: `python debug_parser.py <file>`

### Search Issues

#### Problem: No semantic search results
**Solution:**
1. Ensure embeddings generated:
   ```sql
   SELECT COUNT(*) FROM embeddings;
   ```
2. Check Voyage AI key configured
3. Verify Qdrant has collections:
   ```bash
   curl http://localhost:6333/collections
   ```

#### Problem: Fuzzy search not working
**Solution:**
```bash
# Rebuild FTS index
python -m mcp_server.cli rebuild-index
```

### Docker/Production Issues

#### Problem: Container keeps restarting
**Check logs:**
```bash
docker logs mcp-server
docker-compose logs -f mcp-server
```
**Common causes:**
- Missing environment variables
- Database connection issues
- Permission problems

#### Problem: High memory usage in production
**Solution:**
1. Enable memory optimization:
   ```yaml
   environment:
     - ENABLE_MEMORY_OPTIMIZATION=true
     - CACHE_SIZE_MB=1024
   ```
2. Use connection pooling
3. Configure cache eviction

### Development Issues

#### Problem: Tests failing with import errors
**Solution:**
```bash
# Install development dependencies
pip install -e ".[dev]"

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### Problem: Plugin not loading
**Checklist:**
1. Plugin in `plugins.yaml`
2. `__init__.py` exports plugin class
3. Plugin implements `IPlugin` interface
4. No syntax errors: `python -m py_compile mcp_server/plugins/*/plugin.py`

## Debugging Tools

### Enable Debug Logging
```bash
export MCP_LOG_LEVEL=DEBUG
export MCP_DEBUG=true
python -m mcp_server
```

### Test Individual Components
```bash
# Test parser
python debug_parser.py <file>

# Test search
python -m mcp_server.tools.search_code "query"

# Test plugin
python -m mcp_server.plugins.<plugin_name> test
```

### Performance Profiling
```bash
# Enable profiling
export ENABLE_PROFILING=true
python -m mcp_server

# View profile results
python -m pstats profile_results.prof
```

## Getting Help

1. Check existing issues: https://github.com/code-index-mcp/issues
2. Enable debug logging and include logs
3. Provide minimal reproduction steps
4. Include system information:
   ```bash
   python --version
   pip freeze | grep -E "(tree-sitter|mcp-server)"
   uname -a
   ```

## FAQ

**Q: How do I reset the index?**
```bash
rm -rf ~/.mcp/cache/index.db
python -m mcp_server.cli rebuild-index
```

**Q: Can I index multiple repositories?**
Yes, use repository management mode:
```bash
export ENABLE_REPOSITORY_MANAGEMENT=true
```

**Q: How do I add a new language?**
See `docs/development/creating-plugins.md`

**Q: Is Windows supported?**
Partially. Use WSL2 for best experience.

## Performance Tuning

### For Large Codebases (>100k files)
```yaml
# docker-compose.production.yml
environment:
  - WORKER_COUNT=20
  - INDEXER_BATCH_SIZE=500
  - CACHE_SIZE_MB=4096
  - ENABLE_DISTRIBUTED=true
```

### For Limited Resources
```yaml
environment:
  - WORKER_COUNT=2
  - INDEXER_BATCH_SIZE=50
  - CACHE_SIZE_MB=512
  - ENABLE_MEMORY_OPTIMIZATION=true
```

For more detailed troubleshooting, see `docs/development/debugging.md`.