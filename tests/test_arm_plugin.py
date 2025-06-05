"""
Tests for ARM Assembly Language Plugin

Generated on: 2025-06-04
"""

import pytest
from pathlib import Path
import tempfile

from mcp_server.plugins.arm_plugin.plugin import plugin


class TestARMAssemblyPlugin:
    """Test cases for ARM Assembly plugin."""
    
    @pytest.fixture
    def arm_plugin(self):
        """Provide ARM plugin instance for testing."""
        return plugin()
    
    @pytest.fixture
    def sample_arm_code(self):
        """Provide sample ARM assembly code for testing."""
        return """@ ARM Assembly Example
.text
.global main
.type main, %function

main:
    push {fp, lr}          @ Save frame pointer and link register
    add fp, sp, #4         @ Set up frame pointer
    
    @ Initialize counter
    mov r0, #0
    
loop:
    add r0, r0, #1         @ Increment counter
    cmp r0, #10            @ Compare with 10
    blt loop               @ Branch if less than
    
    @ Return value in r0
    sub sp, fp, #4
    pop {fp, pc}           @ Restore and return

.data
counter:
    .word 0
    
.section .rodata
message:
    .asciz "Hello, ARM!"
"""
    
    @pytest.fixture
    def sample_thumb_code(self):
        """Provide sample Thumb code for testing."""
        return """.thumb
.syntax unified

.global delay
.type delay, %function
delay:
    @ Simple delay loop
    subs r0, r0, #1
    bne delay
    bx lr

.global led_toggle
.type led_toggle, %function  
led_toggle:
    push {r4, lr}
    ldr r4, =0x40020000    @ GPIO base
    ldr r0, [r4, #0x14]    @ Read ODR
    eor r0, r0, #(1<<5)    @ Toggle bit 5
    str r0, [r4, #0x14]    @ Write back
    pop {r4, pc}
"""
    
    @pytest.fixture
    def sample_aarch64_code(self):
        """Provide sample AArch64 code for testing."""
        return """// AArch64 Assembly
.text
.global vector_add
.type vector_add, %function

vector_add:
    // x0 = dest, x1 = src1, x2 = src2, x3 = count
    cbz x3, .Ldone
    
.Lloop:
    ld1 {v0.4s}, [x1], #16
    ld1 {v1.4s}, [x2], #16
    fadd v2.4s, v0.4s, v1.4s
    st1 {v2.4s}, [x0], #16
    
    sub x3, x3, #4
    cbnz x3, .Lloop
    
.Ldone:
    ret

.macro SAVE_REGS
    stp x29, x30, [sp, #-16]!
    mov x29, sp
.endm
"""
    
    def test_plugin_initialization(self, arm_plugin):
        """Test plugin can be initialized."""
        assert arm_plugin.lang == "arm"
        assert arm_plugin.file_extensions == [".s", ".S", ".arm", ".asm"]
    
    def test_supports_method(self, arm_plugin):
        """Test file support detection."""
        assert arm_plugin.supports("test.s") is True
        assert arm_plugin.supports("test.S") is True
        assert arm_plugin.supports("test.arm") is True
        assert arm_plugin.supports("test.asm") is True
        assert arm_plugin.supports("test.py") is False
    
    def test_index_arm_file(self, arm_plugin, sample_arm_code, tmp_path):
        """Test indexing an ARM assembly file."""
        test_file = tmp_path / "test.s"
        test_file.write_text(sample_arm_code)
        
        result = arm_plugin.indexFile(str(test_file), sample_arm_code)
        
        assert result["language"] == "arm"
        assert result["file"] == str(test_file)
        assert "symbols" in result
        assert isinstance(result["symbols"], list)
    
    def test_symbol_extraction(self, arm_plugin, sample_arm_code):
        """Test symbol extraction from ARM code."""
        result = arm_plugin.indexFile("test.s", sample_arm_code)
        symbols = result["symbols"]
        
        # Check that symbols were extracted
        assert len(symbols) > 0
        
        # Find specific symbols
        symbol_names = {s["symbol"] for s in symbols}
        assert "main" in symbol_names
        
        # Check symbol structure - main can be detected as global, function, or label
        main_symbol = next(s for s in symbols if s["symbol"] == "main")
        assert main_symbol["kind"] in ["function", "label", "global"]
    
    def test_iplugin_interface(self, arm_plugin):
        """Test IPlugin interface methods."""
        # Test getDefinition
        definition = arm_plugin.getDefinition("main")
        assert definition is None  # Current implementation returns None
        
        # Test findReferences
        references = list(arm_plugin.findReferences("main"))
        assert len(references) == 0  # Current implementation returns empty
        
        # Test search
        results = list(arm_plugin.search("mov"))
        assert len(results) == 0  # Current implementation returns empty
    
    def test_directive_parsing(self, arm_plugin):
        """Test parsing of ARM directives."""
        directive_code = """.text
.global my_function
.type my_function, %function

.macro MY_MACRO arg1, arg2
    add \\arg1, \\arg1, \\arg2
.endm

my_function:
    mov r0, #42
    bx lr
"""
        result = arm_plugin.indexFile("directives.s", directive_code)
        symbols = result["symbols"]
        
        # Check for symbols
        symbol_names = {s["symbol"] for s in symbols}
        assert "my_function" in symbol_names
        assert "MY_MACRO" in symbol_names
    
    def test_validate_syntax(self, arm_plugin, sample_arm_code):
        """Test syntax validation."""
        # Valid code should pass
        valid, error = arm_plugin.validate_syntax(sample_arm_code)
        assert valid is True
        assert error is None
        
        # Invalid code with unmatched brackets
        invalid_code = """ldr r0, [r1, #4
        str r0, [r2], #8]"""
        valid, error = arm_plugin.validate_syntax(invalid_code)
        assert valid is False
        assert "brackets" in error.lower()
    
    def test_empty_file(self, arm_plugin):
        """Test parsing empty file."""
        result = arm_plugin.indexFile("empty.s", "")
        assert result["symbols"] == []
        assert result["language"] == "arm"
    
    def test_comment_handling(self, arm_plugin):
        """Test that comments are properly ignored."""
        comment_code = """@ This is a comment
# This is also a comment
// C-style comment
/* Multi-line
   comment */
main:   @ Function start
    mov r0, #0  @ Initialize
"""
        result = arm_plugin.indexFile("comments.s", comment_code)
        symbols = result["symbols"]
        
        # Should only find the main symbol
        assert len(symbols) == 1
        assert symbols[0]["symbol"] == "main"
    
    def test_get_symbol_types(self, arm_plugin):
        """Test getting supported symbol types."""
        types = arm_plugin.get_symbol_types()
        assert isinstance(types, list)
        assert len(types) > 0
        
        expected_types = ["label", "function", "macro", "directive", "data", "global"]
        for expected in expected_types:
            assert expected in types
    
    def test_get_instruction_set_info(self, arm_plugin):
        """Test getting instruction set information."""
        info = arm_plugin.get_instruction_set_info()
        
        assert "architectures" in info
        assert "arm" in info["architectures"]
        assert "thumb" in info["architectures"]
        assert "aarch64" in info["architectures"]
        
        assert "instruction_categories" in info
        assert "data_processing" in info["instruction_categories"]
        assert "branch" in info["instruction_categories"]
        assert "simd" in info["instruction_categories"]
        
        assert "register_types" in info
        assert "general" in info["register_types"]
        assert "simd" in info["register_types"]
    
    def test_complex_file_parsing(self, arm_plugin):
        """Test parsing a complex ARM assembly file."""
        # Load one of our test data files
        test_file = Path(__file__).parent.parent / "mcp_server" / "plugins" / "arm_plugin" / "test_data" / "embedded_system.s"
        
        if test_file.exists():
            content = test_file.read_text()
            result = arm_plugin.indexFile(str(test_file), content)
            
            # Should extract many symbols
            assert len(result["symbols"]) > 5
            
            # Verify it's ARM language
            assert result["language"] == "arm"