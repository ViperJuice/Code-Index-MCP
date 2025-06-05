"""AVR Assembly language plugin for code indexing.

This plugin provides support for AVR assembly files (.s, .S, .avr) using regex-based parsing.
It supports labels, interrupt vectors, macros, and I/O register definitions.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from ...plugin_base import IPlugin, IndexShard, SymbolDef, Reference, SearchResult, SearchOpts
from ..plugin_template import LanguagePluginBase, SymbolType, ParsedSymbol


class AVRPlugin(LanguagePluginBase):
    """Plugin for AVR Assembly language support."""
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "avr"
    
    def get_supported_extensions(self) -> List[str]:
        """Return list of file extensions this plugin supports."""
        return [".s", ".S", ".avr"]
    
    def supports_tree_sitter(self) -> bool:
        """AVR doesn't have Tree-sitter support, using regex only."""
        return False
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return regex patterns for different symbol types in AVR assembly."""
        return {
            # Function/procedure labels
            SymbolType.FUNCTION: r'^([a-zA-Z_]\w*):\s*(?:;.*)?$',
            
            # Data definitions
            SymbolType.VARIABLE: r'^\s*([a-zA-Z_]\w*):\s*\.(?:byte|word|dw|db|ds)\s+',
            
            # Constants and I/O register definitions
            SymbolType.CONSTANT: r'^\s*\.(?:equ|set|def)\s+([a-zA-Z_]\w*)\s*=',
            
            # Macros
            SymbolType.MODULE: r'^\s*\.macro\s+([a-zA-Z_]\w*)',
            
            # Interrupt vectors (special handling)
            SymbolType.DECORATOR: r'^\s*\.org\s+(?:0x[0-9a-fA-F]+|\d+)\s*(?:;.*)?$',
        }
    
    def _extract_symbols_regex(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using AVR-specific regex patterns."""
        symbols = []
        lines = content.splitlines()
        
        # Track current context
        in_macro = False
        macro_name = None
        current_section = "text"
        interrupt_vectors = {}
        
        # Common AVR interrupt vector addresses
        avr_interrupts = {
            0x0000: "RESET",
            0x0002: "INT0", 
            0x0004: "INT1",
            0x0006: "PCINT0",
            0x0008: "PCINT1", 
            0x000A: "PCINT2",
            0x000C: "WDT",
            0x000E: "TIMER2_COMPA",
            0x0010: "TIMER2_COMPB",
            0x0012: "TIMER2_OVF",
            0x0014: "TIMER1_CAPT",
            0x0016: "TIMER1_COMPA",
            0x0018: "TIMER1_COMPB",
            0x001A: "TIMER1_OVF",
            0x001C: "TIMER0_COMPA",
            0x001E: "TIMER0_COMPB",
            0x0020: "TIMER0_OVF",
            0x0022: "SPI_STC",
            0x0024: "USART_RX",
            0x0026: "USART_UDRE",
            0x0028: "USART_TX",
            0x002A: "ADC",
            0x002C: "EE_READY",
            0x002E: "ANALOG_COMP",
            0x0030: "TWI",
            0x0032: "SPM_READY"
        }
        
        for line_no, line in enumerate(lines, 1):
            # Skip empty lines and pure comments
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith(';'):
                continue
            
            # Track section changes
            if re.match(r'^\s*\.(?:text|data|bss|eeprom|cseg|dseg|eseg)\b', line):
                section_match = re.match(r'^\s*\.(text|data|bss|eeprom|cseg|dseg|eseg)\b', line)
                if section_match:
                    section_name = section_match.group(1)
                    # Map AVR-specific section names to generic ones
                    if section_name == 'cseg':
                        current_section = 'text'
                    elif section_name == 'dseg':
                        current_section = 'data'  
                    elif section_name == 'eseg':
                        current_section = 'eeprom'
                    else:
                        current_section = section_name
                continue
            
            # Check for interrupt vector definitions
            org_match = re.match(r'^\s*\.org\s+(0x[0-9a-fA-F]+|\d+)\s*(?:;.*)?$', line)
            if org_match:
                # Look ahead for interrupt handler
                if line_no < len(lines):
                    next_line = lines[line_no].strip()
                    if re.match(r'^\s*(?:rjmp|jmp)\s+(\w+)', next_line):
                        handler_match = re.match(r'^\s*(?:rjmp|jmp)\s+(\w+)', next_line)
                        if handler_match:
                            handler_name = handler_match.group(1)
                            address = org_match.group(1)
                            # Convert address to integer
                            addr_int = int(address, 16) if address.startswith('0x') else int(address)
                            
                            # Check if this is a known interrupt vector
                            vector_name = avr_interrupts.get(addr_int, f"VECTOR_{address}")
                            
                            symbols.append(ParsedSymbol(
                                name=f"{vector_name}_handler",
                                symbol_type=SymbolType.FUNCTION,
                                line=line_no,
                                column=0,
                                signature=f".org {address} ; {vector_name}",
                                scope="global",
                                modifiers={"interrupt", "vector"},
                                metadata={
                                    "vector_address": address,
                                    "vector_name": vector_name,
                                    "handler": handler_name
                                }
                            ))
            
            # I/O register definitions
            io_reg_match = re.match(r'^\s*\.(?:equ|set)\s+([a-zA-Z_]\w*)\s*=\s*(.+)', line)
            if io_reg_match:
                reg_name = io_reg_match.group(1)
                reg_value = io_reg_match.group(2)
                
                # Detect if this is an I/O register based on common patterns
                is_io_reg = any(pattern in reg_name.upper() for pattern in 
                              ["PORT", "DDR", "PIN", "TIMER", "UART", "SPI", "TWI", "ADC"])
                
                symbols.append(ParsedSymbol(
                    name=reg_name,
                    symbol_type=SymbolType.CONSTANT,
                    line=line_no,
                    column=line.index(reg_name),
                    signature=line.strip(),
                    scope="global",
                    modifiers={"io_register"} if is_io_reg else {"constant"},
                    metadata={
                        "value": reg_value,
                        "is_io_register": is_io_reg
                    }
                ))
            
            # Macro definitions
            macro_match = re.match(r'^\s*\.macro\s+([a-zA-Z_]\w*)', line)
            if macro_match:
                in_macro = True
                macro_name = macro_match.group(1)
                symbols.append(ParsedSymbol(
                    name=macro_name,
                    symbol_type=SymbolType.MODULE,
                    line=line_no,
                    column=line.index(macro_name),
                    signature=line.strip(),
                    scope="global",
                    modifiers={"macro"},
                    metadata={"section": current_section}
                ))
                continue
            
            # End of macro
            if in_macro and re.match(r'^\s*\.endm(?:acro)?\b', line):
                in_macro = False
                macro_name = None
                continue
            
            # Labels (functions and data)
            func_match = re.match(r'^([a-zA-Z_]\w*):\s*', line)
            if func_match and current_section == "text":
                func_name = func_match.group(1)
                
                # Check if this is a global function
                is_global = False
                is_interrupt = False
                
                # Look for .global directive
                for i in range(max(0, line_no - 5), min(len(lines), line_no + 5)):
                    if i < len(lines):
                        if re.match(rf'^\s*\.glob[al]*\s+{re.escape(func_name)}\b', lines[i]):
                            is_global = True
                        # Check if this is an interrupt handler
                        if "_isr" in func_name.lower() or "_handler" in func_name.lower():
                            is_interrupt = True
                
                # Special handling for main and init
                if func_name in ["main", "init", "__init"]:
                    is_global = True
                
                modifiers = set()
                if is_global:
                    modifiers.add("global")
                if is_interrupt:
                    modifiers.add("interrupt")
                
                symbols.append(ParsedSymbol(
                    name=func_name,
                    symbol_type=SymbolType.FUNCTION,
                    line=line_no,
                    column=0,
                    signature=line.strip(),
                    scope="global" if is_global else "local",
                    modifiers=modifiers,
                    metadata={
                        "section": current_section,
                        "is_interrupt_handler": is_interrupt
                    }
                ))
            
            # Data labels
            elif func_match and current_section in ["data", "bss", "eeprom"]:
                data_name = func_match.group(1)
                
                # Check if directive is on same line
                same_line_match = re.search(r'\.\s*(byte|word|dw|db|ds)\s+', line)
                if same_line_match:
                    data_type = same_line_match.group(1)
                    symbols.append(ParsedSymbol(
                        name=data_name,
                        symbol_type=SymbolType.VARIABLE,
                        line=line_no,
                        column=0,
                        signature=line.strip(),
                        scope="global",
                        modifiers={data_type, current_section},
                        metadata={
                            "section": current_section,
                            "data_type": data_type
                        }
                    ))
                else:
                    # Look ahead for data directive on next line
                    if line_no < len(lines):
                        next_line = lines[line_no].strip()
                        data_directive_match = re.match(r'^\s*\.(?:byte|word|dw|db|ds)\s+(.*)$', next_line)
                        if data_directive_match:
                            data_type = re.search(r'\.(byte|word|dw|db|ds)', next_line).group(1)
                            
                            symbols.append(ParsedSymbol(
                                name=data_name,
                                symbol_type=SymbolType.VARIABLE,
                                line=line_no,
                                column=0,
                                signature=f"{data_name}: .{data_type}",
                                scope="global",
                                modifiers={data_type, current_section},
                                metadata={
                                    "section": current_section,
                                    "data_type": data_type
                                }
                            ))
            
            # Register aliases using .def
            def_match = re.match(r'^\s*\.def\s+([a-zA-Z_]\w*)\s*=\s*(r\d+)', line)
            if def_match:
                alias_name = def_match.group(1)
                register = def_match.group(2)
                
                symbols.append(ParsedSymbol(
                    name=alias_name,
                    symbol_type=SymbolType.CONSTANT,
                    line=line_no,
                    column=line.index(alias_name),
                    signature=line.strip(),
                    scope="global",
                    modifiers={"register_alias"},
                    metadata={
                        "register": register,
                        "is_register_alias": True
                    }
                ))
        
        return symbols
    
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get the definition of an AVR symbol with context."""
        # First try the base implementation
        result = super().getDefinition(symbol)
        if result:
            return result
        
        # AVR-specific register information
        avr_registers = {
            # Working registers
            **{f"r{i}": f"General purpose register R{i}" for i in range(32)},
            # Special registers
            "X": "X pointer (r27:r26)",
            "Y": "Y pointer (r29:r28)",
            "Z": "Z pointer (r31:r30)",
            "SP": "Stack Pointer",
            "SPH": "Stack Pointer High",
            "SPL": "Stack Pointer Low",
            "SREG": "Status Register"
        }
        
        # Common I/O registers (ATmega328P example)
        avr_io_registers = {
            "PORTB": "Port B Data Register",
            "DDRB": "Port B Data Direction Register",
            "PINB": "Port B Input Pins",
            "PORTC": "Port C Data Register",
            "DDRC": "Port C Data Direction Register",
            "PINC": "Port C Input Pins",
            "PORTD": "Port D Data Register",
            "DDRD": "Port D Data Direction Register",
            "PIND": "Port D Input Pins",
            "TCCR0A": "Timer/Counter0 Control Register A",
            "TCCR0B": "Timer/Counter0 Control Register B",
            "TCNT0": "Timer/Counter0",
            "OCR0A": "Timer/Counter0 Output Compare Register A",
            "OCR0B": "Timer/Counter0 Output Compare Register B",
            "TIMSK0": "Timer/Counter0 Interrupt Mask Register",
            "TIFR0": "Timer/Counter0 Interrupt Flag Register",
            "UDR0": "USART I/O Data Register",
            "UCSR0A": "USART Control and Status Register A",
            "UCSR0B": "USART Control and Status Register B",
            "UCSR0C": "USART Control and Status Register C",
            "UBRR0H": "USART Baud Rate Register High",
            "UBRR0L": "USART Baud Rate Register Low"
        }
        
        symbol_upper = symbol.upper()
        
        if symbol in avr_registers:
            return {
                "symbol": symbol,
                "kind": "register",
                "language": "avr",
                "signature": f"{symbol} - AVR Register",
                "doc": avr_registers[symbol],
                "defined_in": "AVR Architecture",
                "line": 0,
                "span": (0, 0)
            }
        
        if symbol_upper in avr_io_registers:
            return {
                "symbol": symbol,
                "kind": "io_register",
                "language": "avr",
                "signature": f"{symbol} - I/O Register",
                "doc": avr_io_registers[symbol_upper],
                "defined_in": "AVR I/O Space",
                "line": 0,
                "span": (0, 0)
            }
        
        return None
    
    def search(self, query: str, opts: SearchOpts | None = None) -> list[SearchResult]:
        """Search for AVR-specific patterns."""
        opts = opts or {}
        results = super().search(query, opts)
        
        # Add AVR instruction search capability
        if opts.get("instructions", False):
            # Common AVR instructions pattern
            instruction_pattern = rf'\b{re.escape(query)}\b\s+[rR]\d+|[XYZ]|SP[HL]?'
            
            for path in Path(".").rglob("*.s"):
                if not path.is_file():
                    continue
                try:
                    content = path.read_text(encoding='utf-8')
                    lines = content.splitlines()
                    
                    for line_no, line in enumerate(lines, 1):
                        if re.search(instruction_pattern, line, re.IGNORECASE):
                            results.append({
                                "file": str(path),
                                "line": line_no,
                                "snippet": line.strip()
                            })
                except Exception:
                    continue
        
        return results
    
    def get_plugin_info(self) -> Dict[str, any]:
        """Get AVR plugin information."""
        info = super().get_plugin_info()
        info.update({
            "description": "AVR Assembly language support with regex-based parsing",
            "features": [
                "Function and label detection",
                "Interrupt vector recognition",
                "I/O register definitions",
                "Macro definition support",
                "Register alias tracking (.def)",
                "Section-aware parsing (.text, .data, .bss, .eeprom)",
                "AVR-specific register knowledge"
            ],
            "supported_sections": ["text", "data", "bss", "eeprom"],
            "architecture": "AVR 8-bit microcontroller",
            "common_mcus": ["ATmega328P", "ATmega2560", "ATtiny85", "ATmega32U4"]
        })
        return info