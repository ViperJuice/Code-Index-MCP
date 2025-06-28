"""
Tests for Multi-Repository Manager

These tests verify the functionality of the multi-repository search system
including registration, cross-repository search, and health monitoring.
"""

import pytest
import tempfile
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from mcp_server.storage.multi_repo_manager import (
    MultiRepositoryManager,
    RepositoryInfo,
    CrossRepoSearchResult,
    get_multi_repo_manager
)
from mcp_server.storage.repository_registry import RepositoryRegistry


class TestMultiRepositoryManager:
    """Test multi-repository management functionality."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create temporary registry path."""
        temp_dir = tempfile.mkdtemp()
        registry_path = Path(temp_dir) / "test_registry.json"
        yield registry_path
        shutil.rmtree(temp_dir)
        
    @pytest.fixture
    def manager(self, temp_registry):
        """Create a test manager instance."""
        return MultiRepositoryManager(
            central_index_path=temp_registry,
            max_workers=2
        )
        
    @pytest.fixture
    def mock_repo_info(self):
        """Create mock repository info."""
        return RepositoryInfo(
            repository_id="test_repo_123",
            name="test-repo",
            path=Path("/test/repo"),
            index_path=Path("/test/repo/.mcp-index/index.db"),
            language_stats={"python": 50, "javascript": 30},
            total_files=80,
            total_symbols=500,
            indexed_at=datetime.now(),
            active=True,
            priority=1
        )
        
    def test_initialization(self, manager, temp_registry):
        """Test manager initialization."""
        assert manager.central_index_path == temp_registry
        assert manager.max_workers == 2
        assert isinstance(manager.registry, RepositoryRegistry)
        assert len(manager._connections) == 0
        
    def test_default_registry_path(self):
        """Test default registry path generation."""
        manager = MultiRepositoryManager()
        expected = Path.home() / '.mcp' / 'repository_registry.json'
        assert manager.central_index_path == expected
        
    def test_repository_registration(self, manager):
        """Test registering a repository."""
        # Create mock repository with index
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            index_dir = repo_path / '.mcp-index'
            index_dir.mkdir()
            index_path = index_dir / 'index.db'
            
            # Create minimal SQLite index
            conn = sqlite3.connect(str(index_path))
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE files (
                    id INTEGER PRIMARY KEY,
                    path TEXT,
                    language TEXT,
                    is_deleted INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE symbols (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    is_deleted INTEGER DEFAULT 0
                )
            """)
            cursor.execute("INSERT INTO files (path, language) VALUES ('test.py', 'python')")
            cursor.execute("INSERT INTO symbols (name) VALUES ('test_function')")
            conn.commit()
            conn.close()
            
            # Register repository
            with patch.object(manager, '_generate_repository_id', return_value='test_id_123'):
                repo_info = manager.register_repository(
                    repository_path=repo_path,
                    name="Test Repo",
                    priority=2
                )
                
            assert repo_info.repository_id == 'test_id_123'
            assert repo_info.name == "Test Repo"
            assert repo_info.path == repo_path
            assert repo_info.priority == 2
            assert repo_info.total_files == 1
            assert repo_info.total_symbols == 1
            assert 'python' in repo_info.language_stats
            
    def test_repository_listing(self, manager, mock_repo_info):
        """Test listing repositories."""
        # Add repositories to registry
        manager.registry.register(mock_repo_info)
        
        # Create another repo with lower priority
        repo2 = RepositoryInfo(
            repository_id="test_repo_456",
            name="low-priority-repo",
            path=Path("/test/repo2"),
            index_path=Path("/test/repo2/.mcp-index/index.db"),
            language_stats={"go": 20},
            total_files=20,
            total_symbols=100,
            indexed_at=datetime.now(),
            active=True,
            priority=0
        )
        manager.registry.register(repo2)
        
        # List all repositories
        repos = manager.list_repositories()
        
        assert len(repos) == 2
        # Should be sorted by priority descending
        assert repos[0].priority == 1
        assert repos[1].priority == 0
        
        # Test active_only filter
        manager.registry.update_status("test_repo_456", active=False)
        active_repos = manager.list_repositories(active_only=True)
        assert len(active_repos) == 1
        assert active_repos[0].repository_id == "test_repo_123"
        
    @pytest.mark.asyncio
    async def test_symbol_search(self, manager, mock_repo_info):
        """Test cross-repository symbol search."""
        # Register repository
        manager.registry.register(mock_repo_info)
        
        # Mock the search method
        mock_results = [
            {
                'name': 'test_function',
                'type': 'function',
                'language': 'python',
                'file_path': 'test.py',
                'line': 10
            }
        ]
        
        with patch.object(manager, '_get_connection') as mock_get_conn:
            mock_store = Mock()
            mock_store.search_symbols.return_value = mock_results
            mock_get_conn.return_value = mock_store
            
            # Perform search
            results = await manager.search_symbol(
                query="test",
                language="python",
                limit=10
            )
            
        assert len(results) == 1
        result = results[0]
        assert result.repository_id == "test_repo_123"
        assert result.repository_name == "test-repo"
        assert len(result.results) == 1
        assert result.results[0]['symbol'] == 'test_function'
        assert result.error is None
        
    @pytest.mark.asyncio
    async def test_parallel_search(self, manager):
        """Test parallel search across multiple repositories."""
        # Register multiple repositories
        repos = []
        for i in range(3):
            repo = RepositoryInfo(
                repository_id=f"repo_{i}",
                name=f"Repo {i}",
                path=Path(f"/test/repo{i}"),
                index_path=Path(f"/test/repo{i}/.mcp-index/index.db"),
                language_stats={"python": 10},
                total_files=10,
                total_symbols=50,
                indexed_at=datetime.now(),
                priority=i
            )
            repos.append(repo)
            manager.registry.register(repo)
            
        # Mock connections and results
        with patch.object(manager, '_get_connection') as mock_get_conn:
            mock_stores = []
            for i in range(3):
                mock_store = Mock()
                mock_store.search_symbols.return_value = [
                    {
                        'name': f'function_{i}',
                        'type': 'function',
                        'language': 'python',
                        'file_path': f'file{i}.py',
                        'line': i * 10
                    }
                ]
                mock_stores.append(mock_store)
                
            mock_get_conn.side_effect = mock_stores
            
            # Perform parallel search
            results = await manager.search_symbol("function", limit=10)
            
        assert len(results) == 3
        # Results should be sorted by priority descending
        assert results[0].repository_id == "repo_2"
        assert results[1].repository_id == "repo_1"
        assert results[2].repository_id == "repo_0"
        
    def test_health_check(self, manager, mock_repo_info):
        """Test repository health check."""
        # Register repository
        manager.registry.register(mock_repo_info)
        
        # Mock path existence
        with patch.object(Path, 'exists') as mock_exists:
            # First call for index_path, second for repo path
            mock_exists.side_effect = [True, True]
            
            with patch.object(manager, '_get_connection', return_value=Mock()):
                health = manager.health_check()
                
        assert health['healthy'] == 1
        assert health['unhealthy'] == 0
        assert len(health['repositories']) == 1
        
        repo_health = health['repositories'][0]
        assert repo_health['repository_id'] == "test_repo_123"
        assert repo_health['status'] == 'healthy'
        assert len(repo_health['issues']) == 0
        
    def test_health_check_unhealthy(self, manager, mock_repo_info):
        """Test health check with unhealthy repository."""
        # Register repository
        manager.registry.register(mock_repo_info)
        
        # Mock missing index file
        with patch.object(Path, 'exists', return_value=False):
            health = manager.health_check()
            
        assert health['healthy'] == 0
        assert health['unhealthy'] == 1
        
        repo_health = health['repositories'][0]
        assert repo_health['status'] == 'unhealthy'
        assert 'Index file not found' in repo_health['issues']
        assert 'Repository path not found' in repo_health['issues']
        
    def test_statistics(self, manager):
        """Test statistics gathering."""
        # Register multiple repositories
        repos = [
            RepositoryInfo(
                repository_id="repo1",
                name="Python Repo",
                path=Path("/test/repo1"),
                index_path=Path("/test/repo1/.mcp-index/index.db"),
                language_stats={"python": 100, "javascript": 20},
                total_files=120,
                total_symbols=600,
                indexed_at=datetime.now()
            ),
            RepositoryInfo(
                repository_id="repo2",
                name="JS Repo",
                path=Path("/test/repo2"),
                index_path=Path("/test/repo2/.mcp-index/index.db"),
                language_stats={"javascript": 80, "typescript": 40},
                total_files=120,
                total_symbols=400,
                indexed_at=datetime.now()
            )
        ]
        
        for repo in repos:
            manager.registry.register(repo)
            
        stats = manager.get_statistics()
        
        assert stats['repositories']['total'] == 2
        assert stats['repositories']['active'] == 2
        assert stats['repositories']['total_files'] == 240
        assert stats['repositories']['total_symbols'] == 1000
        
        assert stats['languages']['python'] == 100
        assert stats['languages']['javascript'] == 100  # 20 + 80
        assert stats['languages']['typescript'] == 40
        
    def test_connection_caching(self, manager, mock_repo_info):
        """Test connection caching."""
        manager.registry.register(mock_repo_info)
        
        with patch('mcp_server.storage.multi_repo_manager.SQLiteStore') as mock_store_class:
            mock_store = Mock()
            mock_store_class.return_value = mock_store
            
            # First call should create connection
            conn1 = manager._get_connection("test_repo_123")
            assert conn1 == mock_store
            assert "test_repo_123" in manager._connections
            
            # Second call should return cached
            conn2 = manager._get_connection("test_repo_123")
            assert conn2 == conn1
            
            # Should only create one instance
            mock_store_class.assert_called_once()
            
    def test_optimize_indexes(self, manager, mock_repo_info):
        """Test index optimization."""
        manager.registry.register(mock_repo_info)
        
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            with patch.object(Path, 'exists', return_value=True):
                manager.optimize_indexes()
                
            # Should run VACUUM and ANALYZE
            mock_cursor.execute.assert_any_call("VACUUM")
            mock_cursor.execute.assert_any_call("ANALYZE")
            mock_conn.close.assert_called_once()
            
    def test_close(self, manager, mock_repo_info):
        """Test manager cleanup."""
        manager.registry.register(mock_repo_info)
        
        # Add a mock connection
        mock_conn = Mock()
        manager._connections["test_repo_123"] = mock_conn
        
        # Close manager
        manager.close()
        
        # Should close all connections
        mock_conn.close.assert_called_once()
        assert len(manager._connections) == 0
        
    def test_search_error_handling(self, manager, mock_repo_info):
        """Test error handling during search."""
        manager.registry.register(mock_repo_info)
        
        # Mock connection failure
        with patch.object(manager, '_get_connection', side_effect=Exception("Connection failed")):
            # Use synchronous version for testing
            result = manager._search_repository(
                "test_repo_123",
                "test",
                None,
                10
            )
            
        # Should return None on connection failure
        assert result is None


class TestRepositoryRegistry:
    """Test repository registry functionality."""
    
    @pytest.fixture
    def temp_registry_path(self):
        """Create temporary registry path."""
        temp_dir = tempfile.mkdtemp()
        registry_path = Path(temp_dir) / "test_registry.json"
        yield registry_path
        shutil.rmtree(temp_dir)
        
    @pytest.fixture
    def registry(self, temp_registry_path):
        """Create test registry instance."""
        return RepositoryRegistry(temp_registry_path)
        
    def test_save_and_load(self, registry, temp_registry_path):
        """Test saving and loading registry."""
        # Create repository info
        repo_info = RepositoryInfo(
            repository_id="test_123",
            name="Test Repo",
            path=Path("/test/repo"),
            index_path=Path("/test/repo/.mcp-index/index.db"),
            language_stats={"python": 50},
            total_files=50,
            total_symbols=200,
            indexed_at=datetime.now()
        )
        
        # Register and save
        registry.register(repo_info)
        
        # Create new registry instance to test loading
        new_registry = RepositoryRegistry(temp_registry_path)
        
        # Should load the saved repository
        loaded = new_registry.get("test_123")
        assert loaded is not None
        assert loaded.name == "Test Repo"
        assert loaded.language_stats["python"] == 50
        
    def test_find_by_path(self, registry):
        """Test finding repository by path."""
        repo_path = Path("/test/my-repo")
        
        repo_info = RepositoryInfo(
            repository_id="path_test",
            name="Path Test",
            path=repo_path,
            index_path=repo_path / ".mcp-index/index.db",
            language_stats={},
            total_files=0,
            total_symbols=0,
            indexed_at=datetime.now()
        )
        
        registry.register(repo_info)
        
        # Find by path
        found_id = registry.find_by_path(repo_path)
        assert found_id == "path_test"
        
        # Non-existent path
        assert registry.find_by_path(Path("/non/existent")) is None
        
    def test_cleanup(self, registry):
        """Test registry cleanup of invalid entries."""
        # Register repository with non-existent index
        repo_info = RepositoryInfo(
            repository_id="invalid_repo",
            name="Invalid",
            path=Path("/fake/path"),
            index_path=Path("/fake/path/.mcp-index/index.db"),
            language_stats={},
            total_files=0,
            total_symbols=0,
            indexed_at=datetime.now()
        )
        
        registry.register(repo_info)
        
        # Run cleanup
        removed = registry.cleanup()
        
        assert removed == 1
        assert registry.get("invalid_repo") is None


class TestSingletonManager:
    """Test singleton manager functionality."""
    
    def test_singleton_instance(self):
        """Test that get_multi_repo_manager returns singleton."""
        # Clear any existing instance
        import mcp_server.storage.multi_repo_manager as module
        module._manager_instance = None
        
        try:
            manager1 = get_multi_repo_manager()
            manager2 = get_multi_repo_manager()
            
            assert manager1 is manager2
        finally:
            # Clean up
            module._manager_instance = None