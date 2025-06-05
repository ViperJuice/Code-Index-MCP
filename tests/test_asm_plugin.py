"""Test suite for Assembly x86_64 plugin."""

import pytest
from pathlib import Path
from mcp_server.plugins.asm_plugin import AssemblyPlugin


@pytest.fixture
def asm_plugin():
    """Create an Assembly plugin instance."""
    return Plugin()


@pytest.fixture
def intel_syntax_code():
    """Sample Intel syntax assembly code."""
    return """
; Simple bootloader code
[bits 16]
[org 0x7c00]

global _start
extern printf

section .text

; Entry point
_start:
    push bp
    mov bp, sp
    
    ; Print message
    mov si, boot_msg
    call print_string
    
    ; Halt
    cli
    hlt
    jmp $

; Function to print a string
; Input: SI = string pointer
print_string:
    push ax
    push si
.loop:
    lodsb
    test al, al
    jz .done
    mov ah, 0x0e
    int 0x10
    jmp .loop
.done:
    pop si
    pop ax
    ret

section .data
    boot_msg db "Booting system...", 0x0d, 0x0a, 0
    msg_len equ $ - boot_msg

section .bss
    buffer resb 512

; Boot signature
times 510-($-$$) db 0
dw 0xaa55
"""


@pytest.fixture
def att_syntax_code():
    """Sample AT&T syntax assembly code."""
    return """
# System call wrapper
.section .text
.globl sys_write
.type sys_write, @function

sys_write:
    pushq %rbp
    movq %rsp, %rbp
    
    movq $1, %rax       # syscall number
    syscall
    
    leave
    ret

.globl main
.type main, @function
main:
    # Print hello world
    movq $1, %rdi       # stdout
    leaq message(%rip), %rsi
    movq $msg_len, %rdx
    call sys_write
    
    # Exit
    movq $60, %rax
    xorq %rdi, %rdi
    syscall

.section .data
message:
    .ascii "Hello, World!\\n"
    .set msg_len, . - message

.section .bss
    .comm buffer, 1024, 32
"""


def test_plugin_initialization(asm_plugin):
    """Test plugin initialization."""
    assert asm_plugin.lang == "assembly"
    assert asm_plugin._intel_patterns is not None
    assert asm_plugin._att_patterns is not None


def test_supports_asm_files(asm_plugin):
    """Test file extension support."""
    assert asm_plugin.supports("test.asm")
    assert asm_plugin.supports("kernel.s")
    assert asm_plugin.supports("boot.S")
    assert asm_plugin.supports("macros.nasm")
    assert asm_plugin.supports("defines.inc")
    assert not asm_plugin.supports("test.c")
    assert not asm_plugin.supports("script.py")


def test_intel_syntax_detection(asm_plugin, intel_syntax_code):
    """Test Intel syntax detection."""
    syntax = asm_plugin._detect_syntax(intel_syntax_code)
    assert syntax == "intel"


def test_att_syntax_detection(asm_plugin, att_syntax_code):
    """Test AT&T syntax detection."""
    syntax = asm_plugin._detect_syntax(att_syntax_code)
    assert syntax == "att"


def test_index_intel_syntax(asm_plugin, intel_syntax_code):
    """Test indexing Intel syntax assembly."""
    shard = asm_plugin.indexFile("boot.asm", intel_syntax_code)
    
    assert shard["file"] == "boot.asm"
    assert shard["language"] == "assembly"
    
    symbols = {s["symbol"]: s for s in shard["symbols"]}
    
    # Check function symbols
    assert "_start" in symbols
    assert symbols["_start"]["kind"] == "function"
    assert symbols["_start"]["line"] == 12
    
    assert "print_string" in symbols
    assert symbols["print_string"]["kind"] == "function"
    
    # Check data symbols
    assert "boot_msg" in symbols
    assert symbols["boot_msg"]["kind"] == "data"
    
    # Check constant
    assert "msg_len" in symbols
    assert symbols["msg_len"]["kind"] == "equ"
    
    # Check sections
    section_symbols = [s for s in shard["symbols"] if s["kind"] == "section"]
    section_names = [s["symbol"] for s in section_symbols]
    assert ".text" in section_names
    assert ".data" in section_names
    assert ".bss" in section_names
    
    # Check global symbol
    global_symbols = [s for s in shard["symbols"] if s["symbol"] == "_start"]
    assert len(global_symbols) > 0


def test_index_att_syntax(asm_plugin, att_syntax_code):
    """Test indexing AT&T syntax assembly."""
    shard = asm_plugin.indexFile("syscall.s", att_syntax_code)
    
    assert shard["file"] == "syscall.s"
    assert shard["language"] == "assembly"
    
    symbols = {s["symbol"]: s for s in shard["symbols"]}
    
    # Check function symbols
    assert "sys_write" in symbols
    assert symbols["sys_write"]["kind"] == "function"
    
    assert "main" in symbols
    assert symbols["main"]["kind"] == "function"
    
    # Check data symbol
    assert "message" in symbols
    assert symbols["message"]["kind"] == "label" or symbols["message"]["kind"] == "data"
    
    # Check constant
    assert "msg_len" in symbols
    assert symbols["msg_len"]["kind"] == "equ"
    
    # Check global declarations
    global_symbols = [s for s in shard["symbols"] if s["kind"] == "global"]
    global_names = [s["symbol"] for s in global_symbols]
    assert "sys_write" in global_names or "sys_write" in symbols
    assert "main" in global_names or "main" in symbols


def test_macro_extraction(asm_plugin):
    """Test macro extraction."""
    code = """
%macro SYSCALL 1
    mov rax, %1
    syscall
%endmacro

%macro PUSH_ALL 0
    push rax
    push rbx
    push rcx
%endmacro
"""
    shard = asm_plugin.indexFile("macros.asm", code)
    
    symbols = {s["symbol"]: s for s in shard["symbols"]}
    
    assert "SYSCALL" in symbols
    assert symbols["SYSCALL"]["kind"] == "macro"
    assert symbols["SYSCALL"]["param_count"] == "1"
    
    assert "PUSH_ALL" in symbols
    assert symbols["PUSH_ALL"]["kind"] == "macro"
    assert symbols["PUSH_ALL"]["param_count"] == "0"


def test_struct_extraction(asm_plugin):
    """Test structure extraction."""
    code = """
struc Point
    .x: resd 1
    .y: resd 1
    .size:
endstruc

STRUC Rectangle
    .top_left:  resb Point.size
    .width:     resd 1
    .height:    resd 1
ENDSTRUC
"""
    shard = asm_plugin.indexFile("structs.asm", code)
    
    symbols = {s["symbol"]: s for s in shard["symbols"]}
    
    assert "Point" in symbols
    assert symbols["Point"]["kind"] == "struc"
    
    assert "Rectangle" in symbols
    assert symbols["Rectangle"]["kind"] == "struc"


def test_documentation_extraction(asm_plugin):
    """Test documentation comment extraction."""
    code = """
; Initialize the system
; This function sets up segments and stack
init_system:
    xor ax, ax
    mov ds, ax
    ret

# Calculate checksum
# Input: SI = buffer, CX = length
# Output: AX = checksum
calc_checksum:
    xor ax, ax
.loop:
    add al, [si]
    inc si
    loop .loop
    ret
"""
    shard = asm_plugin.indexFile("docs.asm", code)
    
    symbols = {s["symbol"]: s for s in shard["symbols"]}
    
    assert "init_system" in symbols
    assert symbols["init_system"]["docstring"] == "Initialize the system This function sets up segments and stack"
    
    assert "calc_checksum" in symbols
    assert "Calculate checksum" in symbols["calc_checksum"]["docstring"]
    assert "Input:" in symbols["calc_checksum"]["docstring"]
    assert "Output:" in symbols["calc_checksum"]["docstring"]


def test_real_file_indexing(asm_plugin):
    """Test indexing real assembly files."""
    test_dir = Path(__file__).parent.parent / "mcp_server/plugins/asm_plugin/test_data"
    
    if test_dir.exists():
        for asm_file in test_dir.glob("*.asm"):
            content = asm_file.read_text(encoding='utf-8')
            shard = asm_plugin.indexFile(str(asm_file), content)
            
            assert shard["file"] == str(asm_file)
            assert shard["language"] == "assembly"
            assert len(shard["symbols"]) > 0
            
        for s_file in test_dir.glob("*.s"):
            content = s_file.read_text(encoding='utf-8')
            shard = asm_plugin.indexFile(str(s_file), content)
            
            assert shard["file"] == str(s_file)
            assert shard["language"] == "assembly"
            assert len(shard["symbols"]) > 0


def test_function_detection_heuristics(asm_plugin):
    """Test function detection heuristics."""
    code = """
_start:
    push rbp
    mov rbp, rsp
    call main
    mov rax, 60
    xor rdi, rdi
    syscall

handle_interrupt:
    push rax
    push rbx
    ; Handle interrupt
    pop rbx
    pop rax
    iret

data_label:
    db "Not a function", 0

init_memory:
    ; Initialize memory subsystem
    xor rax, rax
    ret
"""
    shard = asm_plugin.indexFile("funcs.asm", code)
    
    symbols = {s["symbol"]: s for s in shard["symbols"]}
    
    # These should be detected as functions
    assert symbols["_start"]["kind"] == "function"
    assert symbols["handle_interrupt"]["kind"] == "function"
    assert symbols["init_memory"]["kind"] == "function"
    
    # This should remain a label
    assert symbols["data_label"]["kind"] == "label" or symbols["data_label"]["kind"] == "data"


def test_search_functionality(asm_plugin, intel_syntax_code):
    """Test search functionality."""
    # Index some code first
    asm_plugin.indexFile("test.asm", intel_syntax_code)
    
    # Search for content
    results = list(asm_plugin.search("print"))
    assert len(results) > 0
    
    results = list(asm_plugin.search("boot"))
    assert len(results) > 0


def test_get_definition(asm_plugin, intel_syntax_code):
    """Test getting symbol definitions."""
    asm_plugin.indexFile("test.asm", intel_syntax_code)
    
    definition = asm_plugin.getDefinition("print_string")
    assert definition is not None
    assert definition["symbol"] == "print_string"
    assert definition["kind"] == "function"
    assert definition["language"] == "assembly"


def test_find_references(asm_plugin):
    """Test finding symbol references."""
    code = """
global main
extern printf

main:
    call helper_func
    mov rax, 1
    call helper_func
    ret

helper_func:
    push rbp
    mov rbp, rsp
    leave
    ret

other_func:
    call helper_func
    ret
"""
    asm_plugin.indexFile("refs.asm", code)
    
    refs = list(asm_plugin.findReferences("helper_func"))
    assert len(refs) >= 3  # Definition + at least 3 calls