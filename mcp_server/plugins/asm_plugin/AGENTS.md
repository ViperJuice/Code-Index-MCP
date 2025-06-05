# Assembly x86_64 Plugin

This plugin provides comprehensive indexing and analysis for Assembly language files in both Intel and AT&T syntax.

## Features

### Syntax Support
- **Intel Syntax**: NASM, MASM, FASM style
- **AT&T Syntax**: GAS (GNU Assembler) style
- **Automatic syntax detection** based on file content

### Symbol Extraction
1. **Functions/Procedures**
   - Label-based function detection
   - PROC/ENDP declarations
   - Function prologue/epilogue analysis
   - Documentation comment extraction

2. **Labels**
   - Jump targets
   - Data labels
   - Local labels

3. **Data Declarations**
   - Intel: `db`, `dw`, `dd`, `dq`, `dt`
   - Intel: `resb`, `resw`, `resd`, `resq`
   - AT&T: `.byte`, `.short`, `.int`, `.long`, `.quad`
   - String declarations (`.ascii`, `.asciz`, `.string`)

4. **Sections**
   - `.text`, `.data`, `.bss`, `.rodata`
   - Custom section declarations

5. **Macros**
   - NASM-style `%macro` definitions
   - Parameter count tracking

6. **Global/External Symbols**
   - `global`/`extern` declarations (Intel)
   - `.globl`/`.global` directives (AT&T)

7. **Constants/Equates**
   - `equ` definitions
   - `.set` directives
   - Direct assignments (`=`)

8. **Structures**
   - `struc`/`endstruc` definitions

## File Extensions
- `.asm` - Generic assembly files
- `.s` - Unix/Linux assembly (lowercase)
- `.S` - Unix/Linux assembly with C preprocessor
- `.nasm` - NASM-specific files
- `.inc` - Include files

## Use Cases
- **Operating System Development**: Kernel code, bootloaders, device drivers
- **System Programming**: Low-level utilities, BIOS/UEFI code
- **Performance-Critical Code**: Hand-optimized routines
- **Reverse Engineering**: Disassembled code analysis
- **Embedded Systems**: Microcontroller firmware

## Advanced Features

### Function Detection Heuristics
The plugin uses multiple strategies to distinguish functions from regular labels:
- Documentation comments containing "function", "proc", "routine", "handler"
- Common function name prefixes: `_start`, `main`, `init_`, `handle_`, `do_`, `sys_`
- Function prologue detection: `push rbp`, `enter`, `sub rsp, X`
- Function epilogue detection: `ret`, `retn`, `leave`, `iret`

### Section Context Tracking
Symbols are tagged with their containing section for better organization.

### Documentation Extraction
Comments preceding symbols (using `;` or `#`) are extracted as documentation.

## Example Analysis

### Intel Syntax (NASM)
```asm
section .text
global _start

; Entry point for the program
_start:
    push rbp
    mov rbp, rsp
    
    ; Call main function
    call main
    
    ; Exit system call
    mov eax, 60
    xor edi, edi
    syscall

; Main program logic
main:
    ; Function implementation
    ret

section .data
    message db "Hello, World!", 0x0A
    msg_len equ $ - message
```

### AT&T Syntax (GAS)
```asm
.section .text
.globl _start
.type _start, @function

_start:
    pushq %rbp
    movq %rsp, %rbp
    
    call main
    
    movl $60, %eax
    xorl %edi, %edi
    syscall

.type main, @function
main:
    ret

.section .data
message:
    .ascii "Hello, World!\n"
    .set msg_len, . - message
```

## Performance
- Efficient regex-based parsing
- Pre-indexing for fast searches
- Caching of parsed results
- Support for large assembly files (kernels, etc.)

## Future Enhancements
- Tree-sitter integration when `tree-sitter-x86-asm` becomes available
- Instruction-level analysis
- Register usage tracking
- Call graph generation
- Cross-reference analysis for jump targets