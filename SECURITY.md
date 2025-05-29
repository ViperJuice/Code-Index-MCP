# Security Policy

## Supported Versions

We support security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

1. **DO NOT** open a public issue
2. Email security@code-index-mcp.com with details
3. Include steps to reproduce if possible
4. We'll respond within 48 hours

## Security Measures

### Code Security
- Input validation on all API endpoints
- Path traversal prevention
- SQL injection prevention via parameterized queries
- XSS protection in any web interfaces

### Secret Detection
- Automatic scanning for API keys, tokens, and credentials
- Redaction of detected secrets in logs and outputs
- `.gitignore` patterns respected

### Authentication & Authorization
- API key authentication for production use
- Rate limiting to prevent abuse
- Request validation and sanitization

### Plugin Security
- Plugins run in isolated environments
- Resource limits enforced (CPU, memory)
- No access to system files outside project directory
- Dangerous operations blocked (eval, exec, etc.)

### Data Protection
- Local-first design - no data leaves your machine by default
- Optional encryption at rest
- Secure deletion of temporary files
- No telemetry or usage tracking

## Security Checklist

Before deployment:
- [ ] Change default API keys
- [ ] Enable HTTPS in production
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerting
- [ ] Review file permissions
- [ ] Enable audit logging
- [ ] Test input validation
- [ ] Scan for vulnerabilities

## Dependencies

We regularly update dependencies to patch security vulnerabilities. Run:
```bash
pip list --outdated
pip-audit
```

## Contact

Security Team: security@code-index-mcp.com
PGP Key: [Available on request]