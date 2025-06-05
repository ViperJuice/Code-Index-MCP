"""
Tests for enhanced settings management.
"""
import os
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from mcp_server.config.enhanced_settings import EnhancedSettings


class TestEnhancedSettings:
    """Test enhanced settings configuration."""
    
    def test_default_settings(self):
        """Test default settings values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = EnhancedSettings.from_env()
            
            assert settings.transport_type == 'stdio'
            assert settings.debug is False
            assert settings.log_level == 'INFO'
            assert settings.auto_index is False
            assert settings.disable_resources is False
            assert settings.cache_enabled is False
    
    def test_env_var_parsing(self):
        """Test parsing settings from environment variables."""
        env_vars = {
            'MCP_TRANSPORT': 'websocket',
            'MCP_DEBUG': 'true',
            'MCP_LOG_LEVEL': 'DEBUG',
            'MCP_AUTO_INDEX': '1',
            'MCP_DISABLE_RESOURCES': 'yes',
            'MCP_ENABLE_CACHE': 'true',
            'MCP_CACHE_BACKEND': 'redis',
            'MCP_CACHE_MAX_ENTRIES': '2000',
        }
        
        with patch.dict(os.environ, env_vars):
            settings = EnhancedSettings.from_env()
            
            assert settings.transport_type == 'websocket'
            assert settings.debug is True
            assert settings.log_level == 'DEBUG'
            assert settings.auto_index is True
            assert settings.disable_resources is True
            assert settings.cache_enabled is True
            assert settings.cache_backend == 'redis'
            assert settings.cache_max_entries == 2000
    
    def test_auto_index_patterns(self):
        """Test auto-index pattern configuration."""
        env_vars = {
            'MCP_AUTO_INDEX_PATTERNS': '*.py,*.js,*.go',
            'MCP_AUTO_INDEX_EXCLUDE': '.git,.venv,node_modules,__pycache__',
            'MCP_AUTO_INDEX_MAX_FILES': '500',
        }
        
        with patch.dict(os.environ, env_vars):
            settings = EnhancedSettings.from_env()
            
            assert settings.auto_index_patterns == ['*.py', '*.js', '*.go']
            assert '.git' in settings.auto_index_exclude
            assert 'node_modules' in settings.auto_index_exclude
            assert settings.auto_index_max_files == 500
    
    def test_load_from_config_file(self):
        """Test loading settings from a configuration file."""
        config_data = {
            'transport_type': 'websocket',
            'debug': True,
            'cache_enabled': True,
            'cache_backend': 'redis',
            'health_check_interval': 60,
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            with patch.dict(os.environ, {'MCP_CONFIG_FILE': config_file}):
                settings = EnhancedSettings.from_env()
                
                assert settings.transport_type == 'websocket'
                assert settings.debug is True
                assert settings.cache_enabled is True
                assert settings.cache_backend == 'redis'
                assert settings.health_check_interval == 60
        finally:
            Path(config_file).unlink()
    
    def test_env_overrides_config_file(self):
        """Test that environment variables override config file."""
        config_data = {
            'cache_backend': 'memory',
            'debug': False,
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            env_vars = {
                'MCP_CONFIG_FILE': config_file,
                'MCP_CACHE_BACKEND': 'redis',  # Override config file
                'MCP_ENABLE_CACHE': 'true',
            }
            
            with patch.dict(os.environ, env_vars):
                settings = EnhancedSettings.from_env()
                
                assert settings.cache_backend == 'redis'  # From env
                assert settings.debug is False  # From config file
        finally:
            Path(config_file).unlink()
    
    def test_save_to_file(self):
        """Test saving settings to a file."""
        settings = EnhancedSettings()
        settings.cache_enabled = True
        settings.cache_backend = 'redis'
        settings.debug = True
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = f.name
        
        try:
            settings.save_to_file(config_file)
            
            # Load and verify
            with open(config_file, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data['cache_enabled'] is True
            assert saved_data['cache_backend'] == 'redis'
            assert saved_data['debug'] is True
        finally:
            Path(config_file).unlink()
    
    def test_validation(self):
        """Test settings validation."""
        settings = EnhancedSettings()
        
        # Valid settings
        warnings = settings.validate()
        assert len(warnings) == 0
        
        # Invalid transport
        settings.transport_type = 'invalid'
        warnings = settings.validate()
        assert any('transport type' in w for w in warnings)
        
        # Invalid log level
        settings.transport_type = 'stdio'
        settings.log_level = 'INVALID'
        warnings = settings.validate()
        assert any('log level' in w for w in warnings)
        
        # Invalid cache backend
        settings.log_level = 'INFO'
        settings.cache_enabled = True
        settings.cache_backend = 'invalid'
        warnings = settings.validate()
        assert any('cache backend' in w for w in warnings)
        
        # Invalid numeric values
        settings.cache_backend = 'memory'
        settings.cache_max_entries = -1
        warnings = settings.validate()
        assert any('cache_max_entries' in w for w in warnings)
    
    def test_websocket_port_validation(self):
        """Test WebSocket port validation."""
        settings = EnhancedSettings()
        settings.websocket_enabled = True
        
        # Valid port
        settings.websocket_port = 8080
        warnings = settings.validate()
        assert not any('WebSocket port' in w for w in warnings)
        
        # Invalid ports
        for invalid_port in [0, -1, 70000]:
            settings.websocket_port = invalid_port
            warnings = settings.validate()
            assert any('WebSocket port' in w for w in warnings)
    
    def test_print_summary(self, capsys):
        """Test configuration summary printing."""
        settings = EnhancedSettings()
        settings.auto_index = True
        settings.cache_enabled = True
        settings.cache_backend = 'redis'
        settings.disable_resources = True
        
        settings.print_summary()
        
        captured = capsys.readouterr()
        assert "Transport: stdio" in captured.out
        assert "Auto-indexing: ENABLED" in captured.out
        assert "Claude Code Mode: YES" in captured.out
        assert "Cache: ENABLED (redis)" in captured.out
    
    def test_boolean_parsing(self):
        """Test various boolean value parsing."""
        true_values = ['true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES']
        false_values = ['false', 'False', 'FALSE', '0', 'no', 'No', 'NO', '']
        
        for true_val in true_values:
            with patch.dict(os.environ, {'MCP_DEBUG': true_val}):
                settings = EnhancedSettings.from_env()
                assert settings.debug is True
        
        for false_val in false_values:
            with patch.dict(os.environ, {'MCP_DEBUG': false_val}):
                settings = EnhancedSettings.from_env()
                assert settings.debug is False