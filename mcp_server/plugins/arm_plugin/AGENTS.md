# ARM Assembly Plugin Agent Instructions

## Overview
This plugin provides comprehensive support for ARM Assembly language files with extensions: .s, .S, .arm, .asm

## Capabilities
- Symbol extraction: label, function, macro, directive, data, global
- Tree-sitter support: Pending (will use tree-sitter-arm64 when available)
- Framework detection: arduino, stm32, nrf, rtos, linux, bare_metal, android, ios, kernel, bootloader
- Architecture detection: ARM, Thumb, AArch64
- Instruction set analysis: Data processing, multiply, load/store, branch, SIMD/NEON, Thumb-specific
- Register usage tracking: General purpose, AArch64, SIMD, special registers

## Special Features
- ARM and Thumb instruction set support
- 32-bit and 64-bit ARM architecture support
- Label and function detection with context analysis
- Directive parsing (.global, .text, .data, .macro, etc.)
- Register usage analysis for optimization insights
- Conditional execution pattern recognition
- SIMD/NEON instruction support
- Embedded system framework detection

## Usage Instructions
When working with ARM Assembly files:
1. Use appropriate symbol extraction for labels, functions, macros, and directives
2. Handle comment styles: @ or # for single-line, /* ... */ for multi-line
3. Consider architecture-specific instructions (ARM vs Thumb vs AArch64)
4. Track register usage for performance analysis
5. Detect embedded frameworks and platforms
6. Analyze instruction patterns for optimization opportunities

## Common Patterns
- Function prologue: `push {fp, lr}` or `stp x29, x30, [sp, #-16]!`
- Function epilogue: `pop {fp, pc}` or `ldp x29, x30, [sp], #16`
- Interrupt handlers: Often prefixed with `IRQ_` or `_Handler`
- Vector tables: Look for `.word` directives in sequence
- Boot code: Usually contains `_start` or `Reset_Handler`

## Testing
Run tests with: `pytest tests/test_arm_plugin.py`

## Architecture-Specific Notes
### ARM (32-bit)
- Registers: r0-r15, with special names (sp, lr, pc)
- Conditional execution on most instructions
- Barrel shifter available on many operations

### Thumb
- Compact 16-bit instruction encoding
- Limited register access (r0-r7 for most operations)
- IT blocks for conditional execution

### AArch64 (64-bit)
- Registers: x0-x30 (64-bit), w0-w30 (32-bit)
- No conditional execution (except branches)
- More regular instruction encoding