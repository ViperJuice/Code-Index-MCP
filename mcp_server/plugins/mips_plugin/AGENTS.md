# MIPS Assembly Plugin Agent Instructions

## Overview
This plugin provides support for MIPS Assembly language files (.s, .S, .mips) using regex-based parsing since Tree-sitter doesn't support MIPS assembly.

## Key Features
1. **Symbol Detection**:
   - Functions and labels (ending with `:`)
   - Data segment variables (.word, .byte, .half, .space, .ascii, .asciiz)
   - Constants (.equ or `=`)
   - Macros (.macro)
   - System call wrappers

2. **Section Awareness**:
   - Tracks current section (.text, .data, .bss, .rodata)
   - Properly categorizes symbols based on section context

3. **MIPS-Specific Support**:
   - Register alias resolution ($zero, $at, $v0-$v1, $a0-$a3, etc.)
   - System call recognition
   - Global function detection (.globl directive)

## Implementation Notes
- No Tree-sitter support - uses regex patterns exclusively
- Provides context-aware symbol extraction
- Handles MIPS-specific conventions (e.g., main entry point)
- Supports instruction search when `opts.instructions = True`

## Testing
Use the test data in `test_data/sample.s` which demonstrates:
- Function definitions
- Data declarations
- Macros
- System calls
- Comments and proper MIPS syntax

## Agent Guidelines
- When working with MIPS files, remember this is assembly language
- Labels ending with `:` are significant
- Section directives change parsing context
- Register names can use aliases or numeric form
- System calls are important for MIPS programming