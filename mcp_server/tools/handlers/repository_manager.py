"""
Repository management tool implementation.

Provides tools for managing repositories, including external/reference codebases
with temporary annotation and cleanup capabilities.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from ...storage.sqlite_store import SQLiteStore
from ..registry import ToolRegistry, ToolMetadata, ToolCapability

logger = logging.getLogger(__name__)


async def list_repositories_handler(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    List all repositories with their metadata and statistics.
    
    Args:
        params: Optional filters (type, temporary, language)
        context: Execution context including storage
        
    Returns:
        Repository list with metadata and statistics
    """
    storage = context.get("storage")
    if not storage:
        raise ValueError("Storage not available in context")
    
    # Get filter parameters
    repo_type = params.get("type")  # local, reference, temporary, external
    temporary_only = params.get("temporary_only", False)
    language = params.get("language")
    include_stats = params.get("include_stats", True)
    
    # Build filter
    filters = {}
    if repo_type:
        filters["type"] = repo_type
    if temporary_only:
        filters["temporary"] = True
    if language:
        filters["language"] = language
    
    # Get repositories
    repositories = storage.list_repositories(filter_metadata=filters if filters else None)
    
    # Add statistics if requested
    if include_stats:
        for repo in repositories:
            stats = storage.get_repository_stats(repo["id"])
            repo.update(stats)
    
    # Group by type for better organization
    grouped_repos = {}
    for repo in repositories:
        repo_type = repo.get("metadata", {}).get("type", "unknown")
        if repo_type not in grouped_repos:
            grouped_repos[repo_type] = []
        grouped_repos[repo_type].append(repo)
    
    return {
        "repositories": repositories,
        "grouped_by_type": grouped_repos,
        "total_count": len(repositories),
        "temporary_count": len([r for r in repositories if r.get("metadata", {}).get("temporary", False)]),
        "types": list(grouped_repos.keys())
    }


async def add_reference_repository_handler(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a reference repository for translation/refactoring work.
    
    Args:
        params: Repository details with metadata
        context: Execution context including storage
        
    Returns:
        Repository creation result with guidance
    """
    storage = context.get("storage")
    if not storage:
        raise ValueError("Storage not available in context")
    
    # Extract parameters
    path = params["path"]
    name = params.get("name", Path(path).name)
    language = params.get("language")
    purpose = params.get("purpose", "reference")
    days_to_keep = params.get("days_to_keep", 30)  # Default 30 days
    project_name = params.get("project_name")
    description = params.get("description")
    
    # Calculate cleanup date
    cleanup_after = (datetime.now() + timedelta(days=days_to_keep)).isoformat()
    
    # Create enhanced metadata
    metadata = {
        "type": "reference",
        "language": language,
        "purpose": purpose,
        "project": project_name,
        "description": description,
        "temporary": True,
        "cleanup_after": cleanup_after,
        "days_to_keep": days_to_keep,
        "usage_notes": [
            "This is a reference repository for translation/refactoring",
            f"Will be automatically cleaned up after {cleanup_after}",
            "Use repository-scoped searches to separate from local code",
            "Contains external code that should not be permanently stored"
        ],
        "cleanup_instructions": {
            "automatic": f"Auto-cleanup scheduled for {cleanup_after}",
            "manual": f"Run 'cleanup_repositories' tool to remove before {cleanup_after}",
            "command": f"delete_repository(repository_id={'{repository_id}'}, cascade=True)"
        }
    }
    
    # Add any additional metadata from params
    additional_metadata = params.get("metadata", {})
    metadata.update(additional_metadata)
    
    # Create repository
    repository_id = storage.create_repository(path, name, metadata)
    
    # Get the created repository for return
    created_repo = storage.get_repository(path)
    
    return {
        "repository_id": repository_id,
        "repository": created_repo,
        "guidance": {
            "next_steps": [
                f"Index the repository with: index_file('{path}', recursive=True)",
                "Use repository-scoped searches to find similar patterns",
                "Compare implementations across languages for translation",
                f"Cleanup scheduled for: {cleanup_after}"
            ],
            "search_examples": [
                f"search_code('authentication', repositories=['local', '{name}'])",
                f"search_code('user validation', repository_type='reference')",
                "search_code('password hashing', cross_repository=True)"
            ],
            "cleanup_options": [
                f"Automatic cleanup on: {cleanup_after}",
                "Manual cleanup: cleanup_repositories()",
                f"Specific cleanup: delete_repository({repository_id})"
            ]
        },
        "metadata_summary": {
            "type": metadata["type"],
            "language": metadata["language"],
            "purpose": metadata["purpose"],
            "temporary": metadata["temporary"],
            "cleanup_after": metadata["cleanup_after"],
            "days_remaining": days_to_keep
        }
    }


async def cleanup_repositories_handler(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean up expired repositories or repositories matching criteria.
    
    Args:
        params: Cleanup criteria and options
        context: Execution context including storage
        
    Returns:
        Cleanup results and statistics
    """
    storage = context.get("storage")
    if not storage:
        raise ValueError("Storage not available in context")
    
    # Get cleanup parameters
    cleanup_expired = params.get("cleanup_expired", True)
    repository_ids = params.get("repository_ids", [])
    repository_types = params.get("repository_types", [])
    older_than_days = params.get("older_than_days")
    dry_run = params.get("dry_run", False)
    
    cleanup_results = {
        "expired_cleanup": None,
        "manual_cleanup": [],
        "type_cleanup": [],
        "age_cleanup": [],
        "total_removed": {"repositories": 0, "files": 0, "symbols": 0, "references": 0, "embeddings": 0},
        "dry_run": dry_run
    }
    
    # Clean up expired repositories
    if cleanup_expired:
        if dry_run:
            # Just show what would be cleaned
            temp_repos = storage.get_temporary_repositories()
            current_time = datetime.now()
            expired_repos = []
            
            for repo in temp_repos:
                cleanup_after = repo.get('metadata', {}).get('cleanup_after')
                if cleanup_after:
                    try:
                        cleanup_time = datetime.fromisoformat(cleanup_after)
                        if current_time > cleanup_time:
                            expired_repos.append(repo)
                    except ValueError:
                        continue
            
            cleanup_results["expired_cleanup"] = {
                "would_cleanup": len(expired_repos),
                "repositories": [{"name": r["name"], "path": r["path"]} for r in expired_repos]
            }
        else:
            expired_cleanup = storage.cleanup_expired_repositories()
            cleanup_results["expired_cleanup"] = expired_cleanup
            
            # Add to totals
            for key, value in expired_cleanup["total_deleted"].items():
                cleanup_results["total_removed"][key] += value
    
    # Clean up specific repository IDs
    for repo_id in repository_ids:
        if dry_run:
            repo_stats = storage.get_repository_stats(repo_id)
            cleanup_results["manual_cleanup"].append({
                "repository_id": repo_id,
                "would_delete": repo_stats
            })
        else:
            delete_stats = storage.delete_repository(repo_id, cascade=True)
            cleanup_results["manual_cleanup"].append({
                "repository_id": repo_id,
                "deleted": delete_stats
            })
            
            # Add to totals
            for key, value in delete_stats.items():
                cleanup_results["total_removed"][key] += value
    
    # Clean up by repository type
    for repo_type in repository_types:
        repos = storage.get_repositories_by_type(repo_type)
        for repo in repos:
            if dry_run:
                repo_stats = storage.get_repository_stats(repo["id"])
                cleanup_results["type_cleanup"].append({
                    "repository": repo["name"],
                    "type": repo_type,
                    "would_delete": repo_stats
                })
            else:
                delete_stats = storage.delete_repository(repo["id"], cascade=True)
                cleanup_results["type_cleanup"].append({
                    "repository": repo["name"],
                    "type": repo_type,
                    "deleted": delete_stats
                })
                
                # Add to totals
                for key, value in delete_stats.items():
                    cleanup_results["total_removed"][key] += value
    
    # Clean up by age
    if older_than_days:
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        all_repos = storage.list_repositories()
        
        for repo in all_repos:
            try:
                created_at = datetime.fromisoformat(repo.get('metadata', {}).get('created_at', ''))
                if created_at < cutoff_date:
                    if dry_run:
                        repo_stats = storage.get_repository_stats(repo["id"])
                        cleanup_results["age_cleanup"].append({
                            "repository": repo["name"],
                            "created_at": created_at.isoformat(),
                            "age_days": (datetime.now() - created_at).days,
                            "would_delete": repo_stats
                        })
                    else:
                        delete_stats = storage.delete_repository(repo["id"], cascade=True)
                        cleanup_results["age_cleanup"].append({
                            "repository": repo["name"],
                            "created_at": created_at.isoformat(),
                            "deleted": delete_stats
                        })
                        
                        # Add to totals
                        for key, value in delete_stats.items():
                            cleanup_results["total_removed"][key] += value
            except (ValueError, KeyError):
                continue
    
    return cleanup_results


async def repository_stats_handler(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get detailed statistics for repositories.
    
    Args:
        params: Repository filters and options
        context: Execution context including storage
        
    Returns:
        Detailed repository statistics
    """
    storage = context.get("storage")
    if not storage:
        raise ValueError("Storage not available in context")
    
    repository_id = params.get("repository_id")
    include_breakdown = params.get("include_breakdown", True)
    
    if repository_id:
        # Stats for specific repository
        stats = storage.get_repository_stats(repository_id)
        if include_breakdown:
            # Add detailed breakdown
            stats["breakdown"] = _get_repository_breakdown(storage, repository_id)
        return stats
    else:
        # Stats for all repositories
        all_stats = storage.get_repository_stats()
        
        # Add summary statistics
        summary = {
            "total_repositories": len(all_stats["repositories"]),
            "by_type": {},
            "temporary_count": 0,
            "total_files": 0,
            "total_symbols": 0,
            "total_size": 0,
            "languages": set()
        }
        
        for repo in all_stats["repositories"]:
            repo_type = repo.get("metadata", {}).get("type", "unknown")
            summary["by_type"][repo_type] = summary["by_type"].get(repo_type, 0) + 1
            
            if repo.get("metadata", {}).get("temporary", False):
                summary["temporary_count"] += 1
            
            summary["total_files"] += repo.get("file_count", 0)
            summary["total_symbols"] += repo.get("symbol_count", 0)
            summary["total_size"] += repo.get("total_size", 0) or 0
            
            language = repo.get("metadata", {}).get("language")
            if language:
                summary["languages"].add(language)
        
        summary["languages"] = list(summary["languages"])
        all_stats["summary"] = summary
        
        return all_stats


def _get_repository_breakdown(storage: SQLiteStore, repository_id: int) -> Dict[str, Any]:
    """Get detailed breakdown for a specific repository."""
    # This would include language breakdown, file type analysis, etc.
    # Implementation depends on specific needs
    return {
        "languages": {},
        "file_types": {},
        "largest_files": [],
        "most_symbols": []
    }


# Tool registration schemas
LIST_REPOSITORIES_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["local", "reference", "temporary", "external"],
            "description": "Filter by repository type"
        },
        "temporary_only": {
            "type": "boolean", 
            "default": False,
            "description": "Show only temporary repositories"
        },
        "language": {
            "type": "string",
            "description": "Filter by programming language"
        },
        "include_stats": {
            "type": "boolean",
            "default": True,
            "description": "Include repository statistics"
        }
    }
}

ADD_REFERENCE_REPOSITORY_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the reference repository"
        },
        "name": {
            "type": "string",
            "description": "Repository name (defaults to directory name)"
        },
        "language": {
            "type": "string",
            "description": "Primary programming language"
        },
        "purpose": {
            "type": "string",
            "default": "reference",
            "description": "Purpose (reference, translation, comparison, etc.)"
        },
        "days_to_keep": {
            "type": "integer",
            "default": 30,
            "minimum": 1,
            "maximum": 365,
            "description": "Number of days to keep before auto-cleanup"
        },
        "project_name": {
            "type": "string",
            "description": "Associated project name"
        },
        "description": {
            "type": "string",
            "description": "Repository description"
        },
        "metadata": {
            "type": "object",
            "description": "Additional metadata"
        }
    },
    "required": ["path"]
}

CLEANUP_REPOSITORIES_SCHEMA = {
    "type": "object", 
    "properties": {
        "cleanup_expired": {
            "type": "boolean",
            "default": True,
            "description": "Clean up repositories past their expiration date"
        },
        "repository_ids": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Specific repository IDs to clean up"
        },
        "repository_types": {
            "type": "array",
            "items": {"type": "string", "enum": ["reference", "temporary", "external"]},
            "description": "Repository types to clean up"
        },
        "older_than_days": {
            "type": "integer",
            "minimum": 1,
            "description": "Clean up repositories older than N days"
        },
        "dry_run": {
            "type": "boolean",
            "default": False,
            "description": "Show what would be cleaned without actually deleting"
        }
    }
}

REPOSITORY_STATS_SCHEMA = {
    "type": "object",
    "properties": {
        "repository_id": {
            "type": "integer",
            "description": "Specific repository ID (omit for all repositories)"
        },
        "include_breakdown": {
            "type": "boolean",
            "default": True,
            "description": "Include detailed breakdown of repository contents"
        }
    }
}


def register_tools(registry: ToolRegistry) -> None:
    """Register repository management tools with the registry."""
    
    # List repositories tool
    registry.register(
        name="list_repositories",
        handler=list_repositories_handler,
        schema=LIST_REPOSITORIES_SCHEMA,
        metadata=ToolMetadata(
            name="list_repositories",
            description="List all repositories with filtering and statistics",
            version="1.0.0",
            capabilities=[ToolCapability.ANALYZE],
            tags=["repository", "management", "statistics"],
            author="Code-Index-MCP"
        )
    )
    
    # Add reference repository tool
    registry.register(
        name="add_reference_repository",
        handler=add_reference_repository_handler,
        schema=ADD_REFERENCE_REPOSITORY_SCHEMA,
        metadata=ToolMetadata(
            name="add_reference_repository", 
            description="Add external repository for translation/refactoring with automatic cleanup",
            version="1.0.0",
            capabilities=[ToolCapability.MODIFY],
            tags=["repository", "reference", "translation", "temporary"],
            author="Code-Index-MCP"
        )
    )
    
    # Cleanup repositories tool
    registry.register(
        name="cleanup_repositories",
        handler=cleanup_repositories_handler,
        schema=CLEANUP_REPOSITORIES_SCHEMA,
        metadata=ToolMetadata(
            name="cleanup_repositories",
            description="Clean up temporary and expired repositories",
            version="1.0.0", 
            capabilities=[ToolCapability.MODIFY],
            tags=["repository", "cleanup", "maintenance"],
            author="Code-Index-MCP"
        )
    )
    
    # Repository statistics tool
    registry.register(
        name="repository_stats",
        handler=repository_stats_handler,
        schema=REPOSITORY_STATS_SCHEMA,
        metadata=ToolMetadata(
            name="repository_stats",
            description="Get detailed statistics for repositories",
            version="1.0.0",
            capabilities=[ToolCapability.ANALYZE],
            tags=["repository", "statistics", "analysis"],
            author="Code-Index-MCP"
        )
    )