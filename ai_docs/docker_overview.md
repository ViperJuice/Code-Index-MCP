# Docker AI Context
Last Updated: 2025-01-06

## Framework Overview
Docker is a containerization platform that packages applications and their dependencies into portable containers. It ensures consistent environments across development, testing, and production.

## Current Version & Features
- **Latest Stable**: Docker Engine 24.0+ (as of 2025)
- **Docker Compose**: v2.20+
- **BuildKit**: Default builder with advanced caching
- **Multi-platform**: ARM64 and AMD64 support

## Key Concepts for AI Agents
1. **Images**: Immutable templates containing application code and dependencies
2. **Containers**: Running instances of images
3. **Dockerfile**: Script defining how to build an image
4. **Volumes**: Persistent data storage
5. **Networks**: Container communication

## Common Patterns in This Project

### Multi-Stage Builds
```dockerfile
# Build stage
FROM python:3.11-slim as builder
# Install build dependencies
# Build application

# Runtime stage  
FROM python:3.11-slim
# Copy only necessary files from builder
# Minimal runtime dependencies
```

### Development vs Production
- **Development**: Volume mounts for code, debug tools, hot reload
- **Production**: Optimized images, security hardening, minimal size

### Docker Compose Patterns
```yaml
services:
  app:
    build: .
    volumes:
      - .:/app  # Development only
    environment:
      - ENV_VAR=${ENV_VAR}
```

## Integration with Project
- See `docker/` directory for all Docker configurations
- Three variants: minimal, standard, full (see README.md)
- MCP runs via stdio, not network ports
- Automatic setup scripts in `scripts/`

## Best Practices
1. **Layer Caching**: Order Dockerfile commands from least to most frequently changing
2. **Security**: Run as non-root user, scan for vulnerabilities
3. **Size Optimization**: Multi-stage builds, minimal base images
4. **Build Args**: Use for build-time configuration
5. **.dockerignore**: Exclude unnecessary files from context

## Common Issues and Solutions
1. **Permission Errors**: Match container user UID with host
2. **Volume Mount Issues**: Use absolute paths, check Docker Desktop settings
3. **Build Cache**: Use `--no-cache` for clean builds
4. **Network Issues**: Check firewall, use custom networks

## Performance Considerations
- BuildKit parallel builds
- Layer caching strategies
- Minimal image sizes
- Efficient COPY operations

## Security Best Practices
- Non-root users in containers
- Read-only root filesystem
- Minimal attack surface
- Regular vulnerability scanning
- No secrets in images

## References
- Official Docs: https://docs.docker.com/
- Best Practices: https://docs.docker.com/develop/dev-best-practices/
- Security: https://docs.docker.com/engine/security/
- Compose Spec: https://compose-spec.io/

## AI Agent Notes
- Always use multi-stage builds for production
- Test both development and production configurations
- Document any special build requirements
- Keep images as small as possible
- Use official base images when available

---
*Updated via documentation analysis on 2025-01-06*