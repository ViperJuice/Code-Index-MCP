"""Tests for the MIPS Assembly plugin."""

import pytest
from pathlib import Path

from mcp_server.plugins.mips_plugin import MIPSPlugin


@pytest.fixture
def mips_plugin():
    """Create a MIPS plugin instance."""
    return MIPSPlugin()


@pytest.fixture
def sample_mips_code():
    """Sample MIPS assembly code."""
    return """# MIPS Assembly Sample
.data
    prompt:     .asciiz "Enter a number: "
    result_msg: .asciiz "Result: "
    number1:    .word 42
    number2:    .word 17
    
    # Constants
    MAX_VALUE = 100
    MIN_VALUE = 0

.text
.globl main

main:
    # Print prompt
    li $v0, 4
    la $a0, prompt
    syscall
    
    # Call add function
    jal add_numbers
    
    # Exit
    li $v0, 10
    syscall

add_numbers:
    add $v0, $a0, $a1
    jr $ra

.macro print_int %value
    li $v0, 1
    move $a0, %value
    syscall
.endm

open_file_syscall:
    li $v0, 13
    syscall
    jr $ra
"""


def test_mips_plugin_initialization(mips_plugin):
    """Test plugin initialization."""
    assert mips_plugin.get_language() == "mips"
    assert ".s" in mips_plugin.get_supported_extensions()
    assert ".S" in mips_plugin.get_supported_extensions()
    assert ".mips" in mips_plugin.get_supported_extensions()
    assert not mips_plugin.supports_tree_sitter()


def test_mips_file_support(mips_plugin):
    """Test file extension support."""
    assert mips_plugin.supports("test.s")
    assert mips_plugin.supports("test.S")
    assert mips_plugin.supports("test.mips")
    assert not mips_plugin.supports("test.py")
    assert not mips_plugin.supports("test.c")


def test_mips_symbol_extraction(mips_plugin, sample_mips_code):
    """Test symbol extraction from MIPS code."""
    result = mips_plugin.indexFile("test.s", sample_mips_code)
    
    assert result["language"] == "mips"
    assert result["file"] == "test.s"
    
    symbols = result["symbols"]
    symbol_names = [s["symbol"] for s in symbols]
    
    # Check data symbols
    assert "prompt" in symbol_names
    assert "result_msg" in symbol_names
    assert "number1" in symbol_names
    assert "number2" in symbol_names
    
    # Check constants
    assert "MAX_VALUE" in symbol_names
    assert "MIN_VALUE" in symbol_names
    
    # Check functions
    assert "main" in symbol_names
    assert "add_numbers" in symbol_names
    assert "open_file_syscall" in symbol_names
    
    # Check macro
    assert "print_int" in symbol_names


def test_mips_symbol_types(mips_plugin, sample_mips_code):
    """Test correct symbol type identification."""
    result = mips_plugin.indexFile("test.s", sample_mips_code)
    symbols = {s["symbol"]: s for s in result["symbols"]}
    
    # Check function types
    assert symbols["main"]["kind"] == "function"
    assert symbols["add_numbers"]["kind"] == "function"
    assert symbols["open_file_syscall"]["kind"] == "function"
    
    # Check variable types
    assert symbols["prompt"]["kind"] == "variable"
    assert symbols["number1"]["kind"] == "variable"
    
    # Check constant types
    assert symbols["MAX_VALUE"]["kind"] == "constant"
    assert symbols["MIN_VALUE"]["kind"] == "constant"
    
    # Check macro type
    assert symbols["print_int"]["kind"] == "module"


def test_mips_global_function_detection(mips_plugin, sample_mips_code):
    """Test detection of global functions."""
    result = mips_plugin.indexFile("test.s", sample_mips_code)
    symbols = {s["symbol"]: s for s in result["symbols"]}
    
    # main should be detected as global
    main_symbol = symbols["main"]
    assert main_symbol["scope"] == "global"
    assert "global" in main_symbol.get("modifiers", [])


def test_mips_register_resolution(mips_plugin):
    """Test MIPS register alias resolution."""
    # Test some common register aliases
    result = mips_plugin.getDefinition("$zero")
    assert result is not None
    assert result["kind"] == "register"
    assert "$0" in result["signature"]
    
    result = mips_plugin.getDefinition("$sp")
    assert result is not None
    assert "$29" in result["signature"]
    
    result = mips_plugin.getDefinition("$ra")
    assert result is not None
    assert "$31" in result["signature"]


def test_mips_section_tracking(mips_plugin):
    """Test section tracking in MIPS files."""
    code = """
.data
var1: .word 10

.text
func1:
    nop
    jr $ra

.bss
buffer: .space 100

.text
func2:
    nop
    jr $ra
"""
    result = mips_plugin.indexFile("test.s", code)
    symbols = {s["symbol"]: s for s in result["symbols"]}
    
    # Check that symbols are properly categorized by section
    assert symbols["var1"]["metadata"]["section"] == "data"
    assert symbols["func1"]["metadata"]["section"] == "text"
    assert symbols["buffer"]["metadata"]["section"] == "bss"
    assert symbols["func2"]["metadata"]["section"] == "text"


def test_mips_syscall_detection(mips_plugin, sample_mips_code):
    """Test syscall function detection."""
    result = mips_plugin.indexFile("test.s", sample_mips_code)
    symbols = {s["symbol"]: s for s in result["symbols"]}
    
    # Check syscall function
    assert "open_file_syscall" in symbols
    syscall_func = symbols["open_file_syscall"]
    assert syscall_func["kind"] == "function"
    assert "syscall" in syscall_func.get("modifiers", [])


def test_mips_plugin_info(mips_plugin):
    """Test plugin info method."""
    info = mips_plugin.get_plugin_info()
    
    assert info["name"] == "MIPSPlugin"
    assert info["language"] == "mips"
    assert info["description"] == "MIPS Assembly language support with regex-based parsing"
    assert "features" in info
    assert "supported_sections" in info
    assert info["register_support"] is True