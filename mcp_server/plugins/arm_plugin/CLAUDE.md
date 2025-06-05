# ARM Assembly Plugin Instructions

This file contains instructions for Claude when working with the ARM Assembly plugin.

## Plugin Overview
- **Language**: ARM Assembly
- **Extensions**: .s, .S, .arm, .asm
- **Plugin Directory**: `mcp_server/plugins/arm_plugin/`

## Implementation Notes
1. The plugin uses SmartParser for symbol extraction with regex fallback
2. Tree-sitter support: Pending (will integrate tree-sitter-arm64)
3. Supports these symbol types: label, function, macro, directive, data, global
4. Provides comprehensive ARM architecture analysis
5. Tracks register usage and instruction statistics

## Key Features
- Multi-architecture support (ARM, Thumb, AArch64)
- Embedded framework detection
- Instruction set categorization
- Register usage analysis
- Syntax validation

## Do Not Modify
This file should not be modified directly. Updates should be added to AGENTS.md.