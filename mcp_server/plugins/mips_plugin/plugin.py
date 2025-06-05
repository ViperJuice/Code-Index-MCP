"""MIPS Assembly language plugin for code indexing.

This plugin provides support for MIPS assembly files (.s, .S, .mips) using regex-based parsing.
It supports labels, functions, data declarations, and syscalls.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from ...plugin_base import IPlugin, IndexShard, SymbolDef, Reference, SearchResult, SearchOpts
from ..plugin_template import LanguagePluginBase, SymbolType, ParsedSymbol


class MIPSPlugin(LanguagePluginBase):
    """Plugin for MIPS Assembly language support."""
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "mips"
    
    def get_supported_extensions(self) -> List[str]:
        """Return list of file extensions this plugin supports."""
        return [".s", ".S", ".mips"]
    
    def supports_tree_sitter(self) -> bool:
        """MIPS doesn't have Tree-sitter support, using regex only."""
        return False
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return regex patterns for different symbol types in MIPS assembly."""
        return {
            # Function/procedure labels (typically ending with :)
            SymbolType.FUNCTION: r'^([a-zA-Z_]\w*):\s*(?:#.*)?$',
            
            # Data segment labels
            SymbolType.VARIABLE: r'^\s*([a-zA-Z_]\w*):\s*\.(?:word|byte|half|space|ascii|asciiz)\s+',
            
            # Constants (using .equ or =)
            SymbolType.CONSTANT: r'^\s*([a-zA-Z_]\w*)\s*(?:\.equ|=)\s*',
            
            # Macros
            SymbolType.MODULE: r'^\s*\.macro\s+([a-zA-Z_]\w*)',
        }
    
    def _extract_symbols_regex(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using MIPS-specific regex patterns."""
        symbols = []
        lines = content.splitlines()
        
        # Track current section
        current_section = "text"  # Default to text section
        in_macro = False
        macro_name = None
        
        for line_no, line in enumerate(lines, 1):
            # Skip empty lines and pure comments
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('#'):
                continue
            
            # Track section changes
            if re.match(r'^\s*\.(?:text|data|bss|rodata)\b', line):
                section_match = re.match(r'^\s*\.(text|data|bss|rodata)\b', line)
                if section_match:
                    current_section = section_match.group(1)
                continue
            
            # Check for macro definitions
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
            
            # Check for end of macro
            if in_macro and re.match(r'^\s*\.endm(?:acro)?\b', line):
                in_macro = False
                macro_name = None
                continue
            
            # Function/procedure labels (in text section)
            if current_section == "text":
                # Check for function entry points
                func_match = re.match(r'^([a-zA-Z_]\w*):\s*(?:#.*)?$', line)
                if func_match:
                    func_name = func_match.group(1)
                    
                    # Check if this is a global function
                    is_global = False
                    for i in range(max(0, line_no - 5), min(len(lines), line_no + 5)):
                        if i < len(lines) and re.match(rf'^\s*\.glob[al]*\s+{re.escape(func_name)}\b', lines[i]):
                            is_global = True
                            break
                    
                    # Special handling for main and other common entry points
                    if func_name in ["main", "__start", "_start"]:
                        is_global = True
                    
                    symbols.append(ParsedSymbol(
                        name=func_name,
                        symbol_type=SymbolType.FUNCTION,
                        line=line_no,
                        column=0,
                        signature=line.strip(),
                        scope="global" if is_global else "local",
                        modifiers={"global"} if is_global else set(),
                        metadata={
                            "section": current_section,
                            "is_entry_point": func_name in ["main", "__start", "_start"]
                        }
                    ))
            
            # Data labels (in data/bss sections)
            elif current_section in ["data", "bss", "rodata"]:
                data_match = re.match(r'^\s*([a-zA-Z_]\w*):\s*\.(?:word|byte|half|space|ascii|asciiz)\s+(.*)$', line)
                if data_match:
                    var_name = data_match.group(1)
                    var_type = re.search(r'\.(word|byte|half|space|ascii|asciiz)', line).group(1)
                    
                    symbol_type = SymbolType.CONSTANT if current_section == "rodata" else SymbolType.VARIABLE
                    
                    symbols.append(ParsedSymbol(
                        name=var_name,
                        symbol_type=symbol_type,
                        line=line_no,
                        column=0,
                        signature=line.strip(),
                        scope="global",
                        modifiers={var_type, current_section},
                        metadata={
                            "section": current_section,
                            "data_type": var_type
                        }
                    ))
            
            # Constants using .equ
            const_match = re.match(r'^\s*([a-zA-Z_]\w*)\s*(?:\.equ|=)\s*(.+)$', line)
            if const_match:
                const_name = const_match.group(1)
                const_value = const_match.group(2).strip()
                
                symbols.append(ParsedSymbol(
                    name=const_name,
                    symbol_type=SymbolType.CONSTANT,
                    line=line_no,
                    column=line.index(const_name),
                    signature=line.strip(),
                    scope="global",
                    modifiers={"constant"},
                    metadata={
                        "value": const_value,
                        "section": current_section
                    }
                ))
            
            # System call labels (special handling)
            syscall_match = re.match(r'^\s*([a-zA-Z_]\w*)_syscall:\s*(?:#.*)?$', line)
            if syscall_match:
                syscall_name = syscall_match.group(1)
                symbols.append(ParsedSymbol(
                    name=f"{syscall_name}_syscall",
                    symbol_type=SymbolType.FUNCTION,
                    line=line_no,
                    column=0,
                    signature=line.strip(),
                    scope="global",
                    modifiers={"syscall"},
                    metadata={
                        "section": current_section,
                        "is_syscall": True
                    }
                ))
        
        return symbols
    
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get the definition of a MIPS symbol with context."""
        # First try the base implementation
        result = super().getDefinition(symbol)
        if result:
            return result
        
        # MIPS-specific symbol resolution for register aliases
        register_aliases = {
            "$zero": "$0", "$at": "$1", "$v0": "$2", "$v1": "$3",
            "$a0": "$4", "$a1": "$5", "$a2": "$6", "$a3": "$7",
            "$t0": "$8", "$t1": "$9", "$t2": "$10", "$t3": "$11",
            "$t4": "$12", "$t5": "$13", "$t6": "$14", "$t7": "$15",
            "$s0": "$16", "$s1": "$17", "$s2": "$18", "$s3": "$19",
            "$s4": "$20", "$s5": "$21", "$s6": "$22", "$s7": "$23",
            "$t8": "$24", "$t9": "$25", "$k0": "$26", "$k1": "$27",
            "$gp": "$28", "$sp": "$29", "$fp": "$30", "$ra": "$31"
        }
        
        if symbol in register_aliases:
            return {
                "symbol": symbol,
                "kind": "register",
                "language": "mips",
                "signature": f"{symbol} (alias for {register_aliases[symbol]})",
                "doc": f"MIPS register {symbol} maps to {register_aliases[symbol]}",
                "defined_in": "MIPS Architecture",
                "line": 0,
                "span": (0, 0)
            }
        
        return None
    
    def search(self, query: str, opts: SearchOpts | None = None) -> list[SearchResult]:
        """Search for MIPS-specific patterns."""
        opts = opts or {}
        results = super().search(query, opts)
        
        # Add MIPS instruction search capability
        if opts.get("instructions", False):
            # Common MIPS instructions pattern
            instruction_pattern = rf'\b{re.escape(query)}\b\s+\$?\w+'
            
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
        """Get MIPS plugin information."""
        info = super().get_plugin_info()
        info.update({
            "description": "MIPS Assembly language support with regex-based parsing",
            "features": [
                "Function and label detection",
                "Data segment variable tracking",
                "Macro definition support",
                "System call recognition",
                "Register alias resolution",
                "Section-aware parsing (.text, .data, .bss, .rodata)"
            ],
            "supported_sections": ["text", "data", "bss", "rodata"],
            "register_support": True
        })
        return info