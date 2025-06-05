# Translation & Refactoring Workflow Guide

This guide demonstrates how to use Code-Index-MCP's enhanced repository management for cross-language translation and refactoring projects.

## 🎯 Overview

The enhanced repository system allows you to:
- **Index external codebases** as reference material
- **Search across multiple repositories** for pattern discovery
- **Leverage vector similarity** across languages for translation
- **Automatically clean up** temporary repositories when done
- **Maintain clear separation** between local and reference code

## 🔄 Complete Translation Workflow

### **Scenario: Python → Rust Web Service Translation**

You're translating a Python FastAPI authentication service to Rust using Axum framework.

#### **Step 1: Add Reference Repository**

```bash
# Add Rust examples repository for 30 days
add_reference_repository({
  "path": "/external/rust-web-examples",
  "name": "Rust Web Examples",
  "language": "rust",
  "purpose": "python_to_rust_translation",
  "days_to_keep": 30,
  "project_name": "auth_service_migration",
  "description": "Reference implementations for web service patterns in Rust"
})
```

**Response includes cleanup guidance:**
```json
{
  "repository_id": 2,
  "guidance": {
    "cleanup_options": [
      "Automatic cleanup on: 2025-02-03T10:30:00",
      "Manual cleanup: cleanup_repositories()",
      "Specific cleanup: delete_repository(2)"
    ]
  },
  "metadata_summary": {
    "type": "reference",
    "language": "rust", 
    "temporary": true,
    "cleanup_after": "2025-02-03T10:30:00",
    "days_remaining": 30
  }
}
```

#### **Step 2: Index Reference Repository**

```bash
# Index the Rust examples with repository metadata
index_file({
  "path": "/external/rust-web-examples",
  "recursive": true,
  "repository_metadata": {
    "type": "reference",
    "language": "rust",
    "temporary": true,
    "purpose": "translation_guide"
  }
})
```

#### **Step 3: Cross-Repository Pattern Discovery**

**Find authentication patterns across both codebases:**
```json
{
  "request_type": "symbol_search",
  "target": {"query": "user authentication middleware"},
  "repository_filter": {
    "repositories": ["local", "Rust Web Examples"], 
    "group_by_repository": true
  },
  "context_spec": {"depth": "comprehensive"}
}
```

**Results grouped by repository:**
```json
{
  "results_by_repository": {
    "local": [
      {
        "file": "/src/auth.py",
        "function": "authenticate_user",
        "language": "python",
        "similarity": 0.92
      }
    ],
    "Rust Web Examples": [
      {
        "file": "/examples/auth/middleware.rs", 
        "function": "authenticate_middleware",
        "language": "rust",
        "similarity": 0.89
      }
    ]
  }
}
```

#### **Step 4: Deep Pattern Comparison**

**Get comprehensive context for translation:**
```json
{
  "request_type": "edit_preparation",
  "target": {"symbol": "authenticate_user"},
  "repository_filter": {"cross_repository": true},
  "context_spec": {
    "depth": "edit_ready",
    "include_related": ["dependencies", "tests", "error_handling"],
    "reference_languages": ["rust"]
  }
}
```

**Response optimized for translation:**
```json
{
  "primary_implementation": {
    "repository": "local",
    "language": "python",
    "code": "def authenticate_user(token: str) -> Optional[User]: ...",
    "dependencies": ["jwt", "bcrypt"],
    "error_patterns": ["raises AuthError", "returns None"]
  },
  "reference_implementations": [
    {
      "repository": "Rust Web Examples",
      "language": "rust", 
      "code": "async fn authenticate_user(token: &str) -> Result<User, AuthError> ...",
      "dependencies": ["jsonwebtoken", "bcrypt"],
      "error_patterns": ["Result<T, AuthError>", "anyhow::Error"]
    }
  ],
  "translation_hints": [
    "Python Optional[User] → Rust Result<User, AuthError>",
    "Python exceptions → Rust Result types",
    "Python JWT decode → Rust jsonwebtoken crate"
  ]
}
```

#### **Step 5: Progressive Translation**

Continue pattern-by-pattern:

```bash
# Database patterns
search_code({
  "query": "database connection pooling",
  "repository_filter": {"group_by_repository": true}
})

# Error handling patterns  
search_code({
  "query": "error middleware exception handling",
  "repository_filter": {"repository_types": ["local", "reference"]}
})

# Testing patterns
search_code({
  "query": "authentication tests mocking",
  "repository_filter": {"cross_repository": true}
})
```

#### **Step 6: Monitor Repository Status**

**Check what's indexed:**
```bash
list_repositories({
  "include_stats": true
})
```

**Response shows current state:**
```json
{
  "repositories": [
    {
      "name": "local",
      "type": "local", 
      "file_count": 45,
      "symbol_count": 234,
      "temporary": false
    },
    {
      "name": "Rust Web Examples",
      "type": "reference",
      "file_count": 78,
      "symbol_count": 456, 
      "temporary": true,
      "cleanup_after": "2025-02-03T10:30:00",
      "days_remaining": 28
    }
  ],
  "temporary_count": 1
}
```

#### **Step 7: Cleanup When Complete**

**Option A: Automatic cleanup (recommended)**
- Repository auto-deletes on expiration date
- No manual intervention needed

**Option B: Manual cleanup**
```bash
# Clean up all expired repositories
cleanup_repositories({
  "cleanup_expired": true
})

# Or clean up specific repository
cleanup_repositories({
  "repository_ids": [2]
})

# Or dry run to see what would be cleaned
cleanup_repositories({
  "cleanup_expired": true,
  "dry_run": true
})
```

## 🛠 Advanced Usage Patterns

### **Multi-Reference Translation**

For complex translations, add multiple reference repositories:

```bash
# Add official Rust examples
add_reference_repository({
  "path": "/external/rust-official-examples",
  "language": "rust",
  "purpose": "official_patterns",
  "days_to_keep": 45
})

# Add production Rust codebase
add_reference_repository({
  "path": "/external/production-rust-api", 
  "language": "rust",
  "purpose": "production_patterns",
  "days_to_keep": 60
})

# Search across all references
search_code({
  "query": "middleware error handling",
  "repository_filter": {
    "repository_types": ["reference"],
    "group_by_repository": true
  }
})
```

### **Language-Specific Search**

```bash
# Find only Rust patterns
search_code({
  "query": "async database transactions",
  "repository_filter": {
    "repositories": ["rust_examples", "production_rust"]
  }
})

# Compare Python vs Rust approaches
search_code({
  "query": "request validation",
  "repository_filter": {
    "cross_repository": true,
    "group_by_repository": true
  }
})
```

### **Cleanup Strategies**

**Time-based cleanup:**
```bash
cleanup_repositories({
  "older_than_days": 30
})
```

**Type-based cleanup:**
```bash
cleanup_repositories({
  "repository_types": ["reference", "temporary"]
})
```

**Project-based cleanup:**
```bash
# Filter by metadata in list_repositories, then cleanup specific IDs
cleanup_repositories({
  "repository_ids": [2, 3, 4]
})
```

## 📊 Repository Statistics

**Track usage and size:**
```bash
repository_stats({
  "include_breakdown": true
})
```

**Response shows detailed analysis:**
```json
{
  "summary": {
    "total_repositories": 3,
    "by_type": {"local": 1, "reference": 2},
    "temporary_count": 2,
    "total_files": 156,
    "total_symbols": 890,
    "total_size": "15.2MB",
    "languages": ["python", "rust"]
  },
  "repositories": [
    {
      "name": "local",
      "file_count": 45,
      "symbol_count": 234,
      "total_size": "2.1MB",
      "metadata": {"type": "local"}
    },
    {
      "name": "Rust Web Examples", 
      "file_count": 78,
      "symbol_count": 456,
      "total_size": "8.7MB",
      "metadata": {
        "type": "reference",
        "temporary": true,
        "cleanup_after": "2025-02-03T10:30:00"
      }
    }
  ]
}
```

## 🔄 Git Workflow Integration

### **What Gets Committed to Git**

✅ **Included in Git (uploaded as artifact):**
- `code_index.db` - Contains ALL repositories (local + reference)
- Repository metadata with clear temporary annotations
- Cleanup dates and repository types

✅ **Benefits:**
- Team members can see translation progress
- Reference patterns available for review
- Clear separation via repository metadata
- Automatic cleanup prevents permanent pollution

### **Team Collaboration**

When team members pull your branch:

1. **They see your progress:**
   ```bash
   list_repositories()
   # Shows: local code + temporarily added reference repositories
   ```

2. **They can continue translation:**
   ```bash
   search_code({
     "query": "error handling patterns",
     "repository_filter": {"group_by_repository": true}
   })
   ```

3. **Automatic cleanup happens:**
   - Reference repositories auto-delete on expiration
   - No manual intervention needed

### **Production Deployment**

Before deploying:

```bash
# Clean up all temporary repositories
cleanup_repositories({
  "repository_types": ["reference", "temporary"]
})

# Verify only local code remains
list_repositories()
# Should show only local repositories
```

## 💡 Best Practices

### **Repository Naming**
- Use descriptive names: `"Rust Web Examples"`, `"Django Auth Patterns"`
- Include language: `"golang-microservices-reference"`
- Include purpose: `"authentication-migration-reference"`

### **Cleanup Timing**
- **Short projects (1-2 weeks)**: `days_to_keep: 14`
- **Medium projects (1 month)**: `days_to_keep: 30` 
- **Large migrations (2-3 months)**: `days_to_keep: 90`

### **Search Strategy**
1. **Start broad**: `"authentication"` across all repositories
2. **Get specific**: `"JWT token validation"` in reference repos
3. **Compare patterns**: Group by repository for side-by-side comparison
4. **Deep dive**: Use `edit_preparation` for implementation details

### **Vector Similarity Benefits**
- **Semantic matching**: `"user login"` finds `authenticate_user`, `signin_handler`, `verify_credentials`
- **Cross-language patterns**: Python `@login_required` ↔ Rust `#[auth_required]`
- **Concept discovery**: Find similar error handling across different languages

## 🚨 Troubleshooting

### **Repository Not Found**
```bash
# Check if repository exists
list_repositories({"temporary_only": true})

# Re-add if needed
add_reference_repository({...})
```

### **Search Returns Mixed Results**
```bash
# Use repository filtering
search_code({
  "query": "authentication",
  "repository_filter": {"repositories": ["local"]}  # Local only
})
```

### **Database Size Too Large**
```bash
# Check size breakdown
repository_stats()

# Clean up largest temporary repositories
cleanup_repositories({
  "repository_types": ["reference"]
})
```

### **Expired Repository Still Present**
```bash
# Force cleanup
cleanup_repositories({
  "cleanup_expired": true
})

# Manual deletion
cleanup_repositories({
  "repository_ids": [<repo_id>]
})
```

---

This workflow enables **intelligent cross-language translation** while maintaining **clean separation** and **automatic cleanup** of temporary reference repositories.