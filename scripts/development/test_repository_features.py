#!/usr/bin/env python3
"""
Health check script for repository management features.

Tests the basic functionality of the enhanced repository management system
in the development environment.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

async def test_repository_management():
    """Test the repository management features."""
    try:
        from mcp_server.storage.sqlite_store import SQLiteStore
        from mcp_server.tools.handlers.repository_manager import (
            add_reference_repository_handler,
            list_repositories_handler,
            cleanup_repositories_handler,
            repository_stats_handler
        )
        
        print("🧪 Testing repository management features...")
        
        # Initialize storage
        storage = SQLiteStore("test_repo_management.db")
        context = {"storage": storage}
        
        # Test 1: Add a reference repository
        print("\n1. Testing add_reference_repository...")
        add_params = {
            "path": "/external_repos/test_repo",
            "name": "Test Repository",
            "language": "python",
            "purpose": "testing",
            "days_to_keep": 1,  # Very short for testing
            "project_name": "test_project"
        }
        
        result = await add_reference_repository_handler(add_params, context)
        assert result["repository_id"] is not None
        assert result["metadata_summary"]["type"] == "reference"
        assert result["metadata_summary"]["temporary"] == True
        print("   ✅ Successfully added reference repository")
        
        # Test 2: List repositories
        print("\n2. Testing list_repositories...")
        list_result = await list_repositories_handler({"include_stats": True}, context)
        assert len(list_result["repositories"]) > 0
        assert list_result["temporary_count"] > 0
        print(f"   ✅ Found {len(list_result['repositories'])} repositories")
        
        # Test 3: Repository stats
        print("\n3. Testing repository_stats...")
        stats_result = await repository_stats_handler({}, context)
        assert "repositories" in stats_result
        assert stats_result["summary"]["total_repositories"] > 0
        print(f"   ✅ Repository stats: {stats_result['summary']['total_repositories']} repos")
        
        # Test 4: Cleanup (dry run)
        print("\n4. Testing cleanup_repositories (dry run)...")
        cleanup_result = await cleanup_repositories_handler({"dry_run": True}, context)
        print(f"   ✅ Dry run complete - would clean {len(cleanup_result.get('expired_cleanup', {}).get('repositories', []))} expired repos")
        
        # Test 5: Database integrity
        print("\n5. Testing database integrity...")
        repos = storage.list_repositories()
        for repo in repos:
            assert "metadata" in repo
            metadata = repo["metadata"]
            assert "type" in metadata
            assert "created_at" in metadata
        print("   ✅ Database integrity check passed")
        
        print("\n🎉 All repository management tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Repository management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up test database
        test_db = Path("test_repo_management.db")
        if test_db.exists():
            test_db.unlink()

async def test_mcp_protocol_integration():
    """Test MCP protocol integration with repository features."""
    try:
        from mcp_server.protocol.methods import handle_initialize
        
        print("\n🔌 Testing MCP protocol integration...")
        
        # Test initialization with repository management instructions
        init_result = await handle_initialize(
            protocolVersion="2024-11-05",
            capabilities={"tools": {}},
            clientInfo={"name": "test-client", "version": "1.0"}
        )
        
        assert "instructions" in init_result
        instructions = init_result["instructions"]
        assert "add_reference_repository" in instructions
        assert "cleanup_repositories" in instructions
        assert "Translation/Refactoring Workflow" in instructions
        
        print("   ✅ MCP protocol includes repository management instructions")
        return True
        
    except Exception as e:
        print(f"\n❌ MCP protocol integration test failed: {e}")
        return False

def test_docker_environment():
    """Test Docker environment setup."""
    print("\n🐳 Testing Docker environment...")
    
    # Check if external repos directory exists
    external_repos = Path("/external_repos")
    if external_repos.exists():
        print("   ✅ External repositories mount point exists")
    else:
        print("   ⚠️  External repositories mount point not found (may not be in container)")
    
    # Check if data directory exists
    data_dir = Path("/app/data")
    if data_dir.exists():
        print("   ✅ Data directory exists")
    else:
        print("   ⚠️  Data directory not found")
    
    # Check environment variables
    import os
    env_vars = [
        "DATABASE_URL",
        "ENABLE_REPOSITORY_MANAGEMENT", 
        "REPOSITORY_AUTO_CLEANUP",
        "DEFAULT_REPOSITORY_TTL_DAYS"
    ]
    
    for var in env_vars:
        if os.getenv(var):
            print(f"   ✅ {var} = {os.getenv(var)}")
        else:
            print(f"   ⚠️  {var} not set")
    
    return True

async def main():
    """Run all tests."""
    print("🔍 Code-Index-MCP Repository Management Health Check")
    print("=" * 55)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Repository management features
    if await test_repository_management():
        tests_passed += 1
    
    # Test 2: MCP protocol integration
    if await test_mcp_protocol_integration():
        tests_passed += 1
    
    # Test 3: Docker environment
    if test_docker_environment():
        tests_passed += 1
    
    print("\n" + "=" * 55)
    print(f"📊 Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Repository management is ready for use.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))