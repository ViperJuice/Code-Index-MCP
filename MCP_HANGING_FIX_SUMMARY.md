# MCP Search Tool Hanging Fix Summary

## Problem
The MCP search_code tool was hanging when called through the MCP protocol, causing Claude to get stuck.

## Root Causes

1. **Async Context Deadlock**: The dispatcher's `_load_all_plugins()` method was using `asyncio.run()` within an already running async context, causing a deadlock.

2. **Signal Timeout Issues**: The signal-based timeout mechanism only works in the main thread, but MCP tools run in async contexts.

## Solutions Implemented

### 1. Fixed AsyncIO Deadlock in Plugin Loading
- Modified `dispatcher_enhanced.py` to detect if already in async context
- Falls back to synchronous plugin creation when in async context
- Prevents `asyncio.run()` from being called within existing event loop

### 2. Added Timeout Protection to Search Operations
- Added `asyncio.wait_for()` with 10-second timeout to all search operations
- Handles timeouts gracefully with error messages
- Prevents indefinite hanging

### 3. Enhanced Error Handling
- All search paths now have proper exception handling
- Fallback mechanisms ensure search doesn't completely fail
- Clear error messages returned to user

## Test Results

After fixes:
- Search queries complete in 0.01-0.02 seconds
- No hanging or timeouts
- BM25 search works reliably as fallback
- All MCP query types functional

## Files Modified

1. `/workspaces/Code-Index-MCP/scripts/cli/mcp_server_cli.py`
   - Added timeout protection to search_code tool
   - Enhanced error handling for all search paths

2. `/workspaces/Code-Index-MCP/mcp_server/dispatcher/dispatcher_enhanced.py`
   - Fixed async context detection in `_load_all_plugins()`
   - Prevents asyncio.run() deadlock

## Verification

Run the following to verify the fix:
```bash
python scripts/verify_mcp_no_hang.py
```

All searches should complete within seconds without hanging.