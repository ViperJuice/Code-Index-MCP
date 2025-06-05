+++
title = "Advanced Markdown Features"
author = "Test Suite"
date = 2024-12-18T10:00:00Z
draft = false
categories = ["documentation", "testing"]
summary = "Comprehensive test of advanced Markdown features including TOML front matter"
+++

# Advanced Markdown Test Document

This document tests complex Markdown features and edge cases.

## Table of Contents

- [Advanced Code Blocks](#advanced-code-blocks)
- [Complex Tables](#complex-tables)
- [Advanced Task Lists](#advanced-task-lists)
- [Mathematical Expressions](#mathematical-expressions)
- [Cross-References](#cross-references)

## Advanced Code Blocks

### Code with Metadata

```python {linenos=table,hl_lines=[2,"5-7"],linenostart=199}
def complex_function(data: Dict[str, Any]) -> Optional[List[str]]:
    """Process complex data with type hints."""
    if not data:
        return None
    
    results = []
    for key, value in data.items():
        if isinstance(value, (str, int, float)):
            results.append(f"{key}: {value}")
    
    return results if results else None
```

### Diff Code Block

```diff
  function oldFunction() {
-   return "old implementation";
+   return "new implementation";
  }
  
+ function newFeature() {
+   return "brand new feature";
+ }
```

### YAML Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: production
data:
  database_url: "postgresql://user:pass@localhost/db"
  redis_url: "redis://localhost:6379"
  log_level: "info"
  features:
    - authentication
    - caching
    - monitoring
```

## Complex Tables

### Table with Code and Links

| Command | Description | Example | Documentation |
|---------|-------------|---------|---------------|
| `git clone` | Clone repository | `git clone https://github.com/user/repo.git` | [Git Clone Docs](https://git-scm.com/docs/git-clone) |
| `docker run` | Run container | `docker run -p 8080:80 nginx` | [Docker Run Reference](https://docs.docker.com/engine/reference/commandline/run/) |
| `kubectl apply` | Apply K8s config | `kubectl apply -f deployment.yaml` | [Kubectl Apply](https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#apply) |

### Nested Table Content

| Feature | Implementation | Status | Notes |
|---------|----------------|--------|-------|
| Authentication | OAuth 2.0 + JWT | ✅ Complete | Supports multiple providers:<br/>• GitHub<br/>• Google<br/>• SAML |
| Caching | Redis + Memory | 🚧 In Progress | • L1: Memory cache (1000 items)<br/>• L2: Redis cache (TTL: 1h)<br/>• Cache invalidation strategy |
| Monitoring | Prometheus + Grafana | ❌ Planned | • Metrics collection<br/>• Custom dashboards<br/>• Alerting rules |

## Advanced Task Lists

### Nested Task List with Mixed States

- [x] **Phase 1: Foundation**
  - [x] Set up development environment
    - [x] Install dependencies
    - [x] Configure IDE settings
    - [x] Set up Git hooks
  - [x] Create project structure
  - [x] Write initial documentation
- [ ] **Phase 2: Core Features**
  - [x] User authentication system
    - [x] Login/logout functionality
    - [x] Password reset flow
    - [ ] Multi-factor authentication
      - [x] TOTP support
      - [ ] SMS verification
      - [ ] Hardware key support
  - [ ] Data processing pipeline
    - [x] Input validation
    - [ ] Data transformation
    - [ ] Output formatting
- [ ] **Phase 3: Advanced Features**
  - [ ] Real-time notifications
  - [ ] Advanced analytics
  - [ ] API rate limiting

### Task List with Priorities

- [x] 🔥 **Critical**: Fix security vulnerability
- [ ] ⚡ **High**: Implement caching layer
- [ ] 📊 **Medium**: Add analytics dashboard
- [ ] 🎨 **Low**: Update UI colors
- [X] ✅ **Done**: Complete user registration

## Mathematical Expressions

### Complex Mathematical Formulas

The Schrödinger equation in quantum mechanics:

$$i\hbar\frac{\partial}{\partial t}|\psi(t)\rangle = \hat{H}|\psi(t)\rangle$$

Matrix operations for neural networks:

$$
\mathbf{h}^{(l+1)} = \sigma\left(\mathbf{W}^{(l)}\mathbf{h}^{(l)} + \mathbf{b}^{(l)}\right)
$$

Where:
- $\mathbf{h}^{(l)}$ is the hidden state at layer $l$
- $\mathbf{W}^{(l)}$ is the weight matrix
- $\mathbf{b}^{(l)}$ is the bias vector
- $\sigma$ is the activation function

### Inline Mathematical Expressions

The time complexity is $O(n \log n)$ and space complexity is $O(n)$. The probability density function is given by $f(x) = \frac{1}{\sigma\sqrt{2\pi}}e^{-\frac{1}{2}\left(\frac{x-\mu}{\sigma}\right)^2}$.

## Cross-References and Wiki Links

### Internal References

See the [[Configuration Guide]] for setup instructions.

For advanced usage, check [[API Documentation|our comprehensive API docs]].

The [[Database Schema]] contains all table definitions.

### Reference Links with Descriptions

This document references several external resources[^external] and internal guides[^internal].

Check out the [official documentation][official-docs] for more details.

[official-docs]: https://docs.example.com "Official Documentation - Everything you need to know"

### Image References

![Architecture Diagram][arch-diagram]

![Performance Chart][perf-chart]

[arch-diagram]: ./diagrams/architecture.svg "System Architecture Overview"
[perf-chart]: ./charts/performance-2024.png "Performance Metrics for 2024"

## Footnotes with Rich Content

This section demonstrates advanced footnote usage[^advanced-footnote].

Complex calculations require careful consideration[^math-note].

[^external]: External resources include:
    - [MDN Web Docs](https://developer.mozilla.org/)
    - [Stack Overflow](https://stackoverflow.com/)
    - [GitHub Guides](https://guides.github.com/)

[^internal]: Internal documentation includes:
    - Setup guides
    - API references  
    - Troubleshooting docs
    - Best practices

[^advanced-footnote]: This footnote contains multiple paragraphs and even code:
    
    ```bash
    # Example command
    ./deploy.sh --environment production --confirm
    ```
    
    And continues with more text explaining the deployment process.

[^math-note]: Mathematical formulas in footnotes: $\sum_{i=1}^{n} x_i = \frac{n(n+1)}{2}$

## Complex Code Examples

### Multi-language Code Comparison

Python implementation:
```python
from typing import List, Dict, Optional
import asyncio

async def process_data(items: List[Dict]) -> Optional[List[str]]:
    """Asynchronously process a list of data items."""
    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, str)]

async def process_item(item: Dict) -> str:
    # Simulate async processing
    await asyncio.sleep(0.1)
    return f"Processed: {item.get('name', 'unknown')}"
```

JavaScript equivalent:
```javascript
/**
 * Asynchronously process a list of data items
 * @param {Array<Object>} items - Array of data items to process
 * @returns {Promise<Array<string>>} Array of processed results
 */
async function processData(items) {
    const tasks = items.map(item => processItem(item));
    const results = await Promise.allSettled(tasks);
    return results
        .filter(result => result.status === 'fulfilled')
        .map(result => result.value);
}

async function processItem(item) {
    // Simulate async processing
    await new Promise(resolve => setTimeout(resolve, 100));
    return `Processed: ${item.name || 'unknown'}`;
}
```

## Advanced Blockquotes

> **Important Note**: This is a complex blockquote with multiple elements.
> 
> It contains:
> - Multiple paragraphs
> - Lists within quotes
> - Even code: `const important = true;`
> 
> > **Nested Quote**: Sometimes you need to quote within a quote.
> > 
> > This creates a nested structure that should be properly parsed.
> 
> Back to the main quote with a [link](https://example.com) and **emphasis**.

## HTML and MDX Components

<div class="warning-box">
  <h3>⚠️ Warning</h3>
  <p>This section uses HTML elements mixed with Markdown.</p>
</div>

<details>
<summary><strong>Click to expand advanced configuration</strong></summary>

```yaml
advanced_config:
  database:
    pool_size: 20
    timeout: 30s
    ssl_mode: require
  cache:
    backend: redis
    clusters:
      - host: redis-1.example.com
        port: 6379
      - host: redis-2.example.com
        port: 6379
  monitoring:
    enabled: true
    interval: 30s
    endpoints:
      - /health
      - /metrics
      - /ready
```

</details>

---

## Document Metadata

**Document Version**: 2.1.0  
**Last Updated**: 2024-12-18  
**Authors**: Test Suite, Documentation Team  
**Tags**: #markdown #testing #documentation #advanced-features

---

*This document serves as a comprehensive test case for advanced Markdown parsing capabilities, including TOML front matter, complex tables, nested task lists, mathematical expressions, and mixed content types.*