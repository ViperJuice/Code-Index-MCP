# Security Policy

## 🤖 AI Agent Instructions
> **AI Agents:** For security-related changes, update `AGENTS.md` with security considerations and guidelines.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Code-Index-MCP, please follow these steps:

1. **DO NOT** create a public GitHub issue
2. Send details to: security@code-index-mcp.dev (placeholder - update with actual contact)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if applicable)

## Security Features

### Authentication & Authorization
- JWT-based authentication for API endpoints
- Role-based access control (RBAC)
- API key management for external services

### Data Protection
- Encrypted storage for sensitive configuration
- Secure handling of API keys (Voyage AI, OpenAI, etc.)
- No storage of source code content, only metadata

### Network Security
- HTTPS-only communication in production
- Rate limiting on all endpoints
- CORS configuration for web clients

### Container Security
- Non-root user execution
- Minimal base images
- Regular dependency updates
- Security scanning in CI/CD

## Security Best Practices

### For Developers
1. Never commit secrets or API keys
2. Use environment variables for sensitive data
3. Regular dependency updates (`pip-audit`)
4. Follow secure coding guidelines

### For Deployment
1. Use strong `SECRET_KEY` values
2. Enable all security middleware
3. Configure proper CORS origins
4. Regular security audits

### For AI Agents
1. Never expose or log sensitive data
2. Validate all file paths before access
3. Sanitize user inputs
4. Follow principle of least privilege

## Security Checklist

- [ ] All API keys in environment variables
- [ ] Strong SECRET_KEY configured
- [ ] HTTPS enabled in production
- [ ] Rate limiting configured
- [ ] CORS properly restricted
- [ ] Authentication required for sensitive endpoints
- [ ] Regular security updates applied
- [ ] Logs sanitized of sensitive data

## Known Security Considerations

1. **File System Access**: The indexer requires read access to codebases
   - Mitigated by: Path validation, sandboxing options

2. **External API Integration**: Voyage AI and other services
   - Mitigated by: Secure key storage, request validation

3. **Database Access**: SQLite/PostgreSQL connections
   - Mitigated by: Parameterized queries, connection encryption

## Compliance

This project follows security best practices aligned with:
- OWASP Top 10
- CWE/SANS Top 25
- Security-focused development lifecycle

For additional security resources, see `docs/api/security/` directory.