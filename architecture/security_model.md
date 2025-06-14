# Security Model

## Overview
The MCP Server follows a zero-trust, defense-in-depth security model with local-first design principles.

## Recent Security Enhancements (June 10, 2025)

### Index Export Security
New security measures for shared index artifacts:

1. **Gitignore-Aware Filtering**
   - Automatic exclusion of gitignored files from index exports
   - Prevents accidental sharing of .env files, API keys, and secrets
   - Configurable exclusion patterns via .mcp-index-ignore

2. **Security Analysis Tools**
   - `analyze_gitignore_security.py`: Identifies sensitive files in current index
   - `secure_index_export.py`: Creates filtered exports excluding sensitive data
   - Audit logging of all excluded files for compliance tracking

3. **Default Security Patterns**
   ```
   *.env
   .env*
   *.key
   *.pem
   *secret*
   *password*
   .aws/*
   .ssh/*
   ```

## Security Principles

1. **Local-First**: Minimize attack surface by operating locally
2. **Least Privilege**: Components have minimal required permissions
3. **Defense in Depth**: Multiple layers of security controls
4. **Secure by Default**: Safe defaults, opt-in for risky features
5. **Zero Trust**: Verify everything, trust nothing

## Authentication & Authorization

### API Authentication
- **Method**: JWT tokens or API keys
- **Token Lifetime**: 24 hours
- **Refresh Strategy**: Sliding window
- **Storage**: Secure keyring, never in code

### Authorization Model
- **Read-Only by Default**: No file system modifications without explicit permission
- **Scoped Access**: Plugins restricted to configured directories
- **Role-Based**: Admin, Developer, Read-Only roles
- **Audit Trail**: All access logged

## Input Validation

### API Layer
- **Request Validation**: Pydantic models for all inputs
- **Path Traversal Prevention**: Canonical path resolution
- **Size Limits**: Max request size 10MB
- **Rate Limiting**: 1000 requests/minute per client

### File System Access
- **Sandboxing**: Plugins confined to workspace
- **Symbolic Link Resolution**: Follow with restrictions
- **File Type Validation**: Whitelist allowed extensions
- **Content Scanning**: Detect malicious patterns

## Code Analysis Security

### Plugin Isolation
- **Process Isolation**: Plugins run in separate processes
- **Resource Limits**: CPU, memory, time limits
- **No Network Access**: Plugins cannot make external calls
- **Capability Model**: Explicit permission grants

### Safe Parsing
- **Timeout Protection**: Max 30s per file parse
- **Memory Limits**: Max 100MB per parse operation
- **Crash Recovery**: Isolated parser crashes don't affect system
- **Input Sanitization**: Remove dangerous constructs

## Data Protection

### At Rest
- **Index Encryption**: Optional AES-256 encryption
- **Secure Storage**: File permissions 600
- **Sensitive Data**: Redact secrets/keys from index
- **Backup Security**: Encrypted backups

### In Transit
- **Local Communication**: Unix sockets preferred
- **API Encryption**: TLS 1.3 for network APIs
- **Cloud Sync**: End-to-end encryption
- **No Telemetry**: No data leaves system without consent

## Secret Management

### Detection
- **Pattern Matching**: Detect common secret patterns
- **Entropy Analysis**: High entropy string detection
- **Known Formats**: API keys, passwords, tokens
- **Custom Rules**: User-defined secret patterns

### Prevention
- **Never Index Secrets**: Skip suspicious content
- **Redaction**: Replace with placeholders
- **Alerts**: Notify on detection
- **Quarantine**: Isolate files with secrets

## Vulnerability Prevention

### Dependency Security
- **Automated Scanning**: Daily vulnerability checks
- **Minimal Dependencies**: Reduce attack surface
- **Vendoring**: Pin and verify critical deps
- **Update Policy**: Security patches within 48h

### Code Injection
- **No Dynamic Execution**: No eval() or exec()
- **Template Sanitization**: Escape all outputs
- **SQL Injection**: Parameterized queries only
- **Command Injection**: No shell command construction

## Access Control

### File System
```python
# Allowed paths configuration
allowed_paths = [
    "/home/user/projects",
    "/workspace"
]

# Denied patterns
denied_patterns = [
    "*.key",
    "*.pem",
    ".env*",
    "*secrets*"
]
```

### API Endpoints
```python
# Role-based endpoint access
endpoints = {
    "/api/search": ["read", "write", "admin"],
    "/api/index": ["write", "admin"],
    "/api/config": ["admin"]
}
```

## Contextual Embeddings Security

### API Key Protection
- **Environment Variables**: Store Claude, Voyage, and Cohere API keys securely
- **Key Rotation**: Regular rotation schedule for API keys
- **Access Control**: Restrict API key access to embedding service only
- **Audit Trail**: Log all API key usage

### Content Security
- **Pre-Processing Validation**: Scan chunks for sensitive data before API calls
- **Prompt Injection Prevention**: Sanitize chunk content to prevent malicious prompts
- **Context Isolation**: Separate context generation per project/workspace
- **Data Minimization**: Only send necessary content to APIs

### Cost & Usage Protection
- **Token Budgets**: Configurable limits per project/user
- **Rate Limiting**: Prevent API abuse and cost overruns
- **Usage Monitoring**: Real-time tracking with alerts
- **Fallback Mechanisms**: Graceful degradation without APIs

### Cache Security
- **Encryption**: AES-256 for cached contexts
- **TTL Management**: Automatic expiration of cached data
- **Access Control**: Restrict cache access by user/project
- **Secure Deletion**: Proper cleanup of expired cache

## Monitoring & Auditing

### Security Events
- Failed authentication attempts
- Unauthorized access attempts
- Suspicious file access patterns
- Rate limit violations
- Plugin crashes or timeouts
- API usage anomalies
- Context generation failures
- Token budget exceeded

### Audit Log Format
```json
{
    "timestamp": "2024-01-01T00:00:00Z",
    "event": "file_access",
    "user": "developer",
    "resource": "/path/to/file",
    "action": "read",
    "result": "allowed",
    "metadata": {}
}
```

## Incident Response

### Detection
- Real-time security event monitoring
- Anomaly detection for unusual patterns
- Health checks for system integrity
- Regular security scans

### Response Plan
1. **Isolate**: Disable affected component
2. **Investigate**: Analyze audit logs
3. **Remediate**: Apply fixes
4. **Recover**: Restore service
5. **Review**: Post-mortem analysis

## Security Checklist

### Development
- [ ] Input validation on all user inputs
- [ ] Output encoding for all outputs
- [ ] Secure defaults in configuration
- [ ] Security tests in CI/CD
- [ ] Dependency vulnerability scanning

### Deployment
- [ ] Minimal permissions
- [ ] Encrypted storage
- [ ] Secure configuration
- [ ] Access logging enabled
- [ ] Monitoring configured
- [ ] API keys secured in environment
- [ ] Context cache encryption enabled
- [ ] Token budgets configured
- [ ] Prompt injection detection active

### Operations
- [ ] Regular security updates
- [ ] Access review quarterly
- [ ] Security training
- [ ] Incident drills
- [ ] Compliance audits