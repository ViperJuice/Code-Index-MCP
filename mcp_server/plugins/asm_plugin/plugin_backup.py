"""Generic Assembly language plugin supporting multiple assembler dialects.

Supports various assembly syntaxes including:
- TASM (Turbo Assembler)
- FASM (Flat Assembler)
- NASM (Netwide Assembler)
- MASM (Microsoft Macro Assembler)
- GAS (GNU Assembler)
- Generic assembly patterns
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

from ..plugin_template import (
    LanguagePluginBase,
    SymbolType,
    ParsedSymbol,
    PluginConfig,
)


class AssemblySymbolType:
    """Symbol types specific to Assembly."""
    LABEL = SymbolType.UNKNOWN  # Using existing enum values
    PROCEDURE = SymbolType.FUNCTION
    MACRO = SymbolType.FUNCTION
    SEGMENT = SymbolType.NAMESPACE
    SECTION = SymbolType.NAMESPACE
    EQUATE = SymbolType.CONSTANT
    STRUCT = SymbolType.STRUCT
    DATA = SymbolType.VARIABLE
    EXTERN = SymbolType.IMPORT
    PUBLIC = SymbolType.VARIABLE


class AssemblyPlugin(LanguagePluginBase):
    """Plugin for indexing generic Assembly files."""
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "assembly"
    
    def get_supported_extensions(self) -> List[str]:
        """Return list of file extensions this plugin supports."""
        return [".asm", ".a", ".inc", ".s", ".S"]
    
    def supports_tree_sitter(self) -> bool:
        """Assembly has limited Tree-sitter support."""
        return False  # Tree-sitter-asm is not reliable for generic assembly
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return regex patterns for different symbol types."""
        return {
            # Data definitions (must come before labels to take precedence)
            AssemblySymbolType.DATA: r'^\s*([\w._]+)\s+(?:db|DB|dw|DW|dd|DD|dq|DQ|dt|DT|resb|RESB|resw|RESW|resd|RESD|resq|RESQ)\s',
            
            # Constants/Equates (must come before macros to avoid confusion)
            AssemblySymbolType.EQUATE: r'^\s*([\w._]+)\s+(?:equ|EQU|=)\s+',
            
            # Procedures/Functions (multiple syntaxes)
            AssemblySymbolType.PROCEDURE: r'(?:^\s*([\w._]+)\s+(?:proc|PROC|procedure|PROCEDURE))|(?:^\s*(?:proc|PROC|procedure|PROCEDURE)\s+([\w._]+))|(?:^\s*([\w._]+)\s*:\s*(?:proc|PROC))',
            
            # Macros (excluding equ which is handled separately)
            AssemblySymbolType.MACRO: r'(?:^\s*([\w._]+)\s+(?:macro|MACRO)(?!\s+(?:equ|EQU)))|(?:^\s*(?:macro|MACRO)\s+([\w._]+))|(?:%macro\s+([\w._]+))',
            
            # Structs
            AssemblySymbolType.STRUCT: r'(?:^\s*([\w._]+)\s+(?:struc|STRUC|struct|STRUCT))|(?:^\s*(?:struc|STRUC|struct|STRUCT)\s+([\w._]+))',
            
            # Segments/Sections
            AssemblySymbolType.SEGMENT: r'(?:^\s*([\w._]+)\s+(?:segment|SEGMENT))|(?:^\s*\.(?:segment|SEGMENT)\s+([\w._]+))|(?:^\s*(?:segment|SEGMENT)\s+([\w._]+))',
            AssemblySymbolType.SECTION: r'(?:^\s*(?:section|SECTION|\.section)\s+\.?([\w._]+))|(?:^\s*\[([\w._]+)\])',
            
            # Labels (various styles) - must come after specific patterns
            AssemblySymbolType.LABEL: r'^\s*([\w._]+)\s*:(?!\s*(?:proc|PROC|macro|MACRO|struc|STRUC))',
            
            # External/Public symbols
            AssemblySymbolType.EXTERN: r'(?:^\s*(?:extern|EXTERN|extrn|EXTRN|external|EXTERNAL)\s+([\w._,\s]+))|(?:^\s*\.(?:extern|EXTERN)\s+([\w._]+))',
            AssemblySymbolType.PUBLIC: r'(?:^\s*(?:public|PUBLIC|global|GLOBAL)\s+([\w._,\s]+))|(?:^\s*\.(?:global|GLOBAL)\s+([\w._]+))',
        }
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about this plugin."""
        info = super().get_plugin_info()
        info.update({
            "supported_assemblers": [
                "TASM (Turbo Assembler)",
                "FASM (Flat Assembler)",
                "NASM (Netwide Assembler)",
                "MASM (Microsoft Macro Assembler)",
                "GAS (GNU Assembler)",
                "Generic Assembly"
            ],
            "features": [
                "Multi-dialect support",
                "Label detection",
                "Procedure/function tracking",
                "Macro definitions",
                "Segment/section awareness",
                "Data declarations",
                "External/public symbols",
                "Comment extraction"
            ]
        })
        return info