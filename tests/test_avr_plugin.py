"""Tests for the AVR Assembly plugin."""

import pytest
from pathlib import Path

from mcp_server.plugins.avr_plugin import AVRPlugin


@pytest.fixture
def avr_plugin():
    """Create an AVR plugin instance."""
    return AVRPlugin()


@pytest.fixture
def sample_avr_code():
    """Sample AVR assembly code."""
    return """; AVR Assembly Sample
.include "m328pdef.inc"

; I/O Register definitions
.equ LED_PORT = PORTB
.equ LED_DDR = DDRB
.equ LED_PIN = 5

; Register aliases
.def temp = r16
.def counter = r17

; Interrupt vectors
.org 0x0000
    rjmp RESET
.org 0x0020
    rjmp TIMER0_OVF_handler

.cseg
RESET:
    ; Initialize stack
    ldi temp, HIGH(RAMEND)
    out SPH, temp
    ldi temp, LOW(RAMEND)
    out SPL, temp
    
    ; Initialize LED
    sbi LED_DDR, LED_PIN
    
    ; Enable interrupts
    sei
    rjmp main

main:
    nop
    rjmp main

TIMER0_OVF_handler:
    in r18, SREG
    ; Toggle LED
    sbic PINB, LED_PIN
    rjmp led_off
    sbi LED_PORT, LED_PIN
    rjmp done
led_off:
    cbi LED_PORT, LED_PIN
done:
    out SREG, r18
    reti

.macro delay_ms
    ldi r24, low(@0)
    ldi r25, high(@0)
    rcall delay_routine
.endm

.dseg
blink_count: .byte 1

.eseg
config_byte: .db 0xFF
"""


def test_avr_plugin_initialization(avr_plugin):
    """Test plugin initialization."""
    assert avr_plugin.get_language() == "avr"
    assert ".s" in avr_plugin.get_supported_extensions()
    assert ".S" in avr_plugin.get_supported_extensions()
    assert ".avr" in avr_plugin.get_supported_extensions()
    assert not avr_plugin.supports_tree_sitter()


def test_avr_file_support(avr_plugin):
    """Test file extension support."""
    assert avr_plugin.supports("test.s")
    assert avr_plugin.supports("test.S")
    assert avr_plugin.supports("test.avr")
    assert not avr_plugin.supports("test.py")
    assert not avr_plugin.supports("test.c")


def test_avr_symbol_extraction(avr_plugin, sample_avr_code):
    """Test symbol extraction from AVR code."""
    result = avr_plugin.indexFile("test.s", sample_avr_code)
    
    assert result["language"] == "avr"
    assert result["file"] == "test.s"
    
    symbols = result["symbols"]
    symbol_names = [s["symbol"] for s in symbols]
    
    # Check I/O register definitions
    assert "LED_PORT" in symbol_names
    assert "LED_DDR" in symbol_names
    assert "LED_PIN" in symbol_names
    
    # Check register aliases
    assert "temp" in symbol_names
    assert "counter" in symbol_names
    
    # Check functions
    assert "RESET" in symbol_names
    assert "main" in symbol_names
    assert "TIMER0_OVF_handler" in symbol_names
    
    # Check interrupt vector
    assert "RESET_handler" in symbol_names
    assert "TIMER0_OVF_handler" in symbol_names
    
    # Check macro
    assert "delay_ms" in symbol_names
    
    # Check data
    assert "blink_count" in symbol_names
    assert "config_byte" in symbol_names


def test_avr_symbol_types(avr_plugin, sample_avr_code):
    """Test correct symbol type identification."""
    result = avr_plugin.indexFile("test.s", sample_avr_code)
    symbols = {s["symbol"]: s for s in result["symbols"]}
    
    # Check constant types (I/O registers and constants)
    assert symbols["LED_PORT"]["kind"] == "constant"
    assert symbols["LED_PIN"]["kind"] == "constant"
    
    # Check register aliases
    assert symbols["temp"]["kind"] == "constant"
    assert "register_alias" in symbols["temp"].get("modifiers", [])
    
    # Check function types
    assert symbols["RESET"]["kind"] == "function"
    assert symbols["main"]["kind"] == "function"
    assert symbols["TIMER0_OVF_handler"]["kind"] == "function"
    
    # Check macro type
    assert symbols["delay_ms"]["kind"] == "module"


def test_avr_interrupt_detection(avr_plugin, sample_avr_code):
    """Test interrupt vector and handler detection."""
    result = avr_plugin.indexFile("test.s", sample_avr_code)
    symbols = {s["symbol"]: s for s in result["symbols"]}
    
    # Check interrupt vectors
    assert "RESET_handler" in symbols
    reset_vector = symbols["RESET_handler"]
    assert reset_vector["kind"] == "function"
    assert "interrupt" in reset_vector.get("modifiers", [])
    assert "vector" in reset_vector.get("modifiers", [])
    assert reset_vector["metadata"]["vector_address"] == "0x0000"
    
    # Check interrupt handler
    timer_handler = symbols["TIMER0_OVF_handler"]
    assert timer_handler["kind"] == "function"


def test_avr_register_resolution(avr_plugin):
    """Test AVR register resolution."""
    # Test general purpose registers
    result = avr_plugin.getDefinition("r16")
    assert result is not None
    assert result["kind"] == "register"
    assert "R16" in result["doc"]
    
    # Test pointer registers
    result = avr_plugin.getDefinition("X")
    assert result is not None
    assert "r27:r26" in result["doc"]
    
    result = avr_plugin.getDefinition("SP")
    assert result is not None
    assert "Stack Pointer" in result["doc"]
    
    # Test status register
    result = avr_plugin.getDefinition("SREG")
    assert result is not None
    assert "Status Register" in result["doc"]


def test_avr_io_register_resolution(avr_plugin):
    """Test AVR I/O register knowledge."""
    # Test port registers
    result = avr_plugin.getDefinition("PORTB")
    assert result is not None
    assert result["kind"] == "io_register"
    assert "Port B Data Register" in result["doc"]
    
    # Test timer registers
    result = avr_plugin.getDefinition("TCNT0")
    assert result is not None
    assert "Timer/Counter0" in result["doc"]
    
    # Test USART registers
    result = avr_plugin.getDefinition("UDR0")
    assert result is not None
    assert "USART" in result["doc"]


def test_avr_section_tracking(avr_plugin):
    """Test section tracking in AVR files."""
    code = """
.text
func1:
    ret

.data
var1: .byte 10

.eeprom
eeprom_data: .db 0xFF

.bss
buffer: .byte 100

.text
func2:
    ret
"""
    result = avr_plugin.indexFile("test.s", code)
    symbols = {s["symbol"]: s for s in result["symbols"]}
    
    # Check that symbols are properly categorized by section
    assert symbols["func1"]["metadata"]["section"] == "text"
    assert symbols["func2"]["metadata"]["section"] == "text"
    
    # Note: data labels need proper directives on next line to be detected


def test_avr_io_register_detection(avr_plugin, sample_avr_code):
    """Test I/O register constant detection."""
    result = avr_plugin.indexFile("test.s", sample_avr_code)
    symbols = {s["symbol"]: s for s in result["symbols"]}
    
    # LED_PORT should be detected as I/O register
    led_port = symbols["LED_PORT"]
    assert led_port["kind"] == "constant"
    assert "io_register" in led_port.get("modifiers", [])
    assert led_port["metadata"]["is_io_register"] is True


def test_avr_plugin_info(avr_plugin):
    """Test plugin info method."""
    info = avr_plugin.get_plugin_info()
    
    assert info["name"] == "AVRPlugin"
    assert info["language"] == "avr"
    assert info["description"] == "AVR Assembly language support with regex-based parsing"
    assert "features" in info
    assert "supported_sections" in info
    assert info["architecture"] == "AVR 8-bit microcontroller"
    assert "common_mcus" in info
    assert "ATmega328P" in info["common_mcus"]