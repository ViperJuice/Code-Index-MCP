# GitHub Actions AI Context
Last Updated: 2025-01-06

## Framework Overview
GitHub Actions is a CI/CD platform that automates build, test, and deployment pipelines directly in GitHub repositories. It uses YAML workflow files to define automation triggered by repository events.

## Core Concepts
- **Workflows**: Automated processes defined in `.github/workflows/`
- **Jobs**: Units of work that run on runners
- **Steps**: Individual tasks within jobs
- **Actions**: Reusable units of code
- **Runners**: Compute environments (GitHub-hosted or self-hosted)
- **Events**: Triggers for workflows (push, PR, schedule, etc.)

## Workflow Structure
```yaml
name: CI/CD Pipeline
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

env:
  PYTHON_VERSION: '3.11'

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -e .
      
      - name: Run tests
        run: pytest --cov=mcp_server
```

## Common Patterns in This Project

### Artifact Management
```yaml
- name: Build indexes
  run: python scripts/cli/mcp_cli.py index build

- name: Upload artifacts
  uses: actions/upload-artifact@v3
  with:
    name: index-artifacts
    path: .mcp-index/
    retention-days: 30

- name: Download artifacts
  uses: actions/download-artifact@v3
  with:
    name: index-artifacts
```

### Docker Build and Push
```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Login to GitHub Container Registry
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- name: Build and push
  uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: ghcr.io/${{ github.repository }}:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

## Integration with Project
- Workflows in `.github/workflows/`
- Artifact system for index sharing
- Docker image publishing
- Automated testing and linting
- Release automation

## Key Features Used

### Matrix Builds
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python: ['3.9', '3.10', '3.11']
```

### Conditional Execution
```yaml
- name: Deploy
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  run: ./deploy.sh
```

### Secrets and Variables
```yaml
env:
  API_KEY: ${{ secrets.VOYAGE_AI_API_KEY }}
  
- name: Use variable
  run: echo "Running on ${{ vars.ENVIRONMENT }}"
```

### Caching
```yaml
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

## Best Practices
1. **Security**: Never hardcode secrets, use GitHub Secrets
2. **Efficiency**: Use caching for dependencies
3. **Parallelism**: Split jobs for parallel execution
4. **Reusability**: Create composite actions for common tasks
5. **Fail Fast**: Stop on first error in matrix builds

## Common Workflow Types

### CI Pipeline
```yaml
name: CI
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make lint

  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make build
```

### Release Workflow
```yaml
name: Release
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
```

## Performance Optimization
- Use GitHub-hosted runners for standard tasks
- Self-hosted runners for specialized hardware
- Parallel jobs with `needs` dependencies
- Artifact caching between jobs
- Docker layer caching

## Common Issues and Solutions
1. **Permissions**: Set appropriate GITHUB_TOKEN permissions
2. **Timeouts**: Default 6 hours, increase if needed
3. **Rate Limits**: Use GITHUB_TOKEN for API calls
4. **Large Files**: Use Git LFS or external storage
5. **Secrets**: Rotate regularly, use environments

## Debugging
```yaml
- name: Debug context
  run: |
    echo "Event: ${{ github.event_name }}"
    echo "Ref: ${{ github.ref }}"
    echo "SHA: ${{ github.sha }}"
    
- name: Enable debug logging
  run: echo "ACTIONS_STEP_DEBUG=true" >> $GITHUB_ENV
```

## References
- Official Docs: https://docs.github.com/en/actions
- Workflow Syntax: https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions
- Marketplace: https://github.com/marketplace?type=actions
- Best Practices: https://docs.github.com/en/actions/guides/best-practices-for-github-actions

## AI Agent Notes
- Always use latest action versions (e.g., `@v4`)
- Test workflows in feature branches first
- Use workflow dispatch for manual testing
- Keep workflows DRY with reusable workflows
- Monitor usage to avoid hitting limits
- Use concurrency groups to prevent duplicate runs

---
*Updated via documentation analysis on 2025-01-06*