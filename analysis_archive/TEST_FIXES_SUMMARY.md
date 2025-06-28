# Test Failures Root Cause Analysis and Fixes

## Summary of Issues Found and Fixed

### 1. Import Path Issues
- **Problem**: `PluginFactory` was being imported from `mcp_server.plugin_system.plugin_factory` but actually exists in `mcp_server.plugins.plugin_factory`
- **Fixed in**: `tests/base_test.py`
- **Solution**: Changed import to `from mcp_server.plugins.plugin_factory import PluginFactory`

### 2. Class Name Mismatches
- **Problem**: Test imported `PlaintextPlugin` but the actual class name is `PlainTextPlugin` (capital T)
- **Fixed in**: `tests/test_document_error_recovery.py`
- **Solution**: Changed import to `PlainTextPlugin` and updated initialization to include required `language_config` parameter

### 3. Missing Exports
- **Problem**: `PluginInstance` was not exported from `mcp_server.plugin_system.__init__.py`
- **Fixed in**: `mcp_server/plugin_system/__init__.py`
- **Solution**: Added `PluginInstance` to both the import list and `__all__` export list

### 4. Class Instantiation Issues
- **Problem**: `PluginFactory` is a class with only class methods, but tests were trying to instantiate it with `PluginFactory()`
- **Fixed in**: 
  - `tests/test_document_error_recovery.py`
  - `tests/root_tests/test_document_basic_validation.py`
- **Solution**: Removed instantiation, pass the class itself or use `EnhancedDispatcher` which properly handles the factory

### 5. Method Signature Issues
- **Problem**: `store_file()` method was being called with extra positional arguments that don't exist in the signature
- **Fixed in**: `mcp_server/plugins/typescript_plugin/plugin.py`
- **Solution**: Removed extra positional argument and moved hash to metadata dict

### 6. Missing Exception Classes
- **Problem**: Test imported `DocumentProcessingError` which doesn't exist
- **Fixed in**: `tests/test_document_error_recovery.py`
- **Solution**: Changed to import `MCPError` instead

### 7. Method Call Issues
- **Problem**: `indexFile()` method expects both `path` and `content` parameters, but tests were only passing `path`
- **Fixed in**: `tests/test_document_error_recovery.py` (multiple locations)
- **Solution**: Added code to read file content before calling `indexFile()`

## Remaining Issues to Address

1. **Module Structure**: Many tests are in `tests/root_tests/` directory which may not be properly discovered by pytest
2. **Additional store_file() calls**: Need to check and fix similar issues in other plugin files
3. **Test failures**: Some tests may still fail due to business logic issues rather than import/signature problems

## Recommendations

1. Run a full test suite to identify remaining import and signature issues
2. Consider moving tests from `tests/root_tests/` back to `tests/` directory
3. Update all plugins to use the correct `store_file()` signature
4. Add type hints and better documentation to prevent these issues in the future