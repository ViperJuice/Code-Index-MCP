"""
Tests for feature flags management system.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from mcp_server.utils.feature_flags import FeatureManager, FeatureConfig


class TestFeatureManager:
    """Test feature flags manager."""
    
    def setup_method(self):
        """Reset feature manager before each test."""
        self.feature_manager = FeatureManager()
        self.feature_manager._enabled_features.clear()
        self.feature_manager._feature_configs.clear()
        self.feature_manager._initialized = False
    
    def test_initialize_no_features(self):
        """Test initialization with no features enabled."""
        with patch.dict(os.environ, {}, clear=True):
            self.feature_manager.initialize_from_env()
            
            assert self.feature_manager._initialized
            assert len(self.feature_manager._enabled_features) == 0
    
    def test_enable_single_feature(self):
        """Test enabling a single feature."""
        with patch.dict(os.environ, {'MCP_ENABLE_CACHE': 'true'}):
            self.feature_manager.initialize_from_env()
            
            assert self.feature_manager.is_enabled('cache')
            assert 'cache' in self.feature_manager._enabled_features
            assert not self.feature_manager.is_enabled('health')
    
    def test_enable_multiple_features(self):
        """Test enabling multiple features."""
        env_vars = {
            'MCP_ENABLE_CACHE': 'true',
            'MCP_ENABLE_HEALTH': '1',
            'MCP_ENABLE_METRICS': 'yes',
            'MCP_ENABLE_RATE_LIMIT': 'false',
        }
        
        with patch.dict(os.environ, env_vars):
            self.feature_manager.initialize_from_env()
            
            assert self.feature_manager.is_enabled('cache')
            assert self.feature_manager.is_enabled('health')
            assert self.feature_manager.is_enabled('metrics')
            assert not self.feature_manager.is_enabled('rate_limit')
    
    def test_feature_dependencies(self):
        """Test feature dependency resolution."""
        # WebSocket depends on health
        with patch.dict(os.environ, {'MCP_ENABLE_WEBSOCKET': 'true'}):
            self.feature_manager.initialize_from_env()
            
            assert self.feature_manager.is_enabled('websocket')
            assert self.feature_manager.is_enabled('health')  # Auto-enabled
    
    def test_feature_configuration(self):
        """Test feature-specific configuration."""
        env_vars = {
            'MCP_ENABLE_CACHE': 'true',
            'MCP_CACHE_BACKEND': 'redis',
            'MCP_CACHE_MAX_ENTRIES': '5000',
            'MCP_CACHE_TTL': '7200',
        }
        
        with patch.dict(os.environ, env_vars):
            self.feature_manager.initialize_from_env()
            
            cache_config = self.feature_manager.get_config('cache')
            assert cache_config['backend'] == 'redis'
            assert cache_config['max_entries'] == 5000
            assert cache_config['ttl'] == 7200
    
    def test_get_config_value(self):
        """Test getting specific config values."""
        with patch.dict(os.environ, {'MCP_ENABLE_CACHE': 'true', 'MCP_CACHE_BACKEND': 'redis'}):
            self.feature_manager.initialize_from_env()
            
            assert self.feature_manager.get_config_value('cache', 'backend') == 'redis'
            assert self.feature_manager.get_config_value('cache', 'nonexistent', 'default') == 'default'
            assert self.feature_manager.get_config_value('health', 'anything', 'default') == 'default'
    
    def test_unknown_feature(self):
        """Test handling of unknown features."""
        self.feature_manager._enable_feature('unknown_feature')
        assert 'unknown_feature' not in self.feature_manager._enabled_features
    
    def test_get_all_features(self):
        """Test getting all available features."""
        all_features = self.feature_manager.get_all_features()
        
        assert 'cache' in all_features
        assert 'health' in all_features
        assert 'metrics' in all_features
        assert isinstance(all_features['cache'], FeatureConfig)
    
    def test_numeric_config_parsing(self):
        """Test parsing of numeric configuration values."""
        env_vars = {
            'MCP_ENABLE_METRICS': 'true',
            'MCP_METRICS_PORT': '8080',  # Should parse as int
        }
        
        with patch.dict(os.environ, env_vars):
            self.feature_manager.initialize_from_env()
            
            metrics_config = self.feature_manager.get_config('metrics')
            assert metrics_config['port'] == 8080
            assert isinstance(metrics_config['port'], int)
    
    def test_print_feature_status(self, capsys):
        """Test feature status printing."""
        with patch.dict(os.environ, {'MCP_ENABLE_CACHE': 'true'}):
            self.feature_manager.initialize_from_env()
            self.feature_manager.print_feature_status()
            
            captured = capsys.readouterr()
            assert "cache" in captured.out
            assert "✓ ENABLED" in captured.out
            assert "✗ DISABLED" in captured.out