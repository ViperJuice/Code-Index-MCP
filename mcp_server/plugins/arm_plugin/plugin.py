"""
ARM Assembly Language Plugin for Code-Index-MCP

Provides comprehensive language-specific parsing and analysis for ARM assembly files.
Supports both ARM and Thumb instruction sets, 32-bit and 64-bit architectures.
"""

from typing import Dict, List, Optional, Set, Tuple, Any, Iterable
import re
import logging
from pathlib import Path

from mcp_server.plugin_base import (
    IPlugin, 
    IndexShard, 
    SymbolDef, 
    Reference, 
    SearchResult, 
    SearchOpts
)
from mcp_server.utils.smart_parser import SmartParser

logger = logging.getLogger(__name__)


class ARMAssemblyPlugin(IPlugin):
    """Language plugin for ARM Assembly files."""
    
    lang = "arm"
    file_extensions = [".s", ".S", ".arm", ".asm"]
    
    # ARM-specific instruction patterns
    ARM_INSTRUCTIONS = {
        # Data processing
        "data_processing": r"\b(add|sub|rsb|adc|sbc|rsc|and|orr|eor|bic|mov|mvn|lsl|lsr|asr|ror|rrx|cmp|cmn|tst|teq)\b",
        # Multiply
        "multiply": r"\b(mul|mla|mls|umull|umlal|smull|smlal)\b",
        # Load/Store
        "load_store": r"\b(ldr|str|ldm|stm|push|pop|ldrb|strb|ldrh|strh|ldrd|strd)\b",
        # Branch
        "branch": r"\b(b|bl|bx|blx|beq|bne|bcs|bcc|bmi|bpl|bvs|bvc|bhi|bls|bge|blt|bgt|ble|bal)\b",
        # SIMD/NEON
        "simd": r"\b(vadd|vsub|vmul|vdiv|vld1|vst1|vmov|vcmp|vcvt)\b",
        # Thumb-specific
        "thumb": r"\b(cbz|cbnz|it|ite|itt|itet|itttt)\b"
    }
    
    # Directive patterns
    DIRECTIVES = {
        "section": r"^\s*\.(text|data|bss|rodata|section)\b",
        "global": r"^\s*\.(global|globl|extern)\s+(\w+)",
        "function": r"^\s*\.(func|function|type)\s+(\w+)",
        "data": r"^\s*\.(byte|hword|word|long|quad|ascii|asciz|string)\b",
        "align": r"^\s*\.(align|balign|p2align)\b",
        "macro": r"^\s*\.(macro|endm)\b",
        "conditional": r"^\s*\.(if|ifdef|ifndef|else|elif|endif)\b",
        "include": r"^\s*\.(include|incbin)\s+[\"<]([^\">\s]+)[\">\s]"
    }
    
    # Register patterns
    REGISTERS = {
        "general": r"\b(r[0-9]|r1[0-5]|sp|lr|pc|ip|fp)\b",
        "aarch64": r"\b(x[0-9]|x[12][0-9]|x30|w[0-9]|w[12][0-9]|w30|sp|xzr|wzr)\b",
        "simd": r"\b(s[0-9]|s[12][0-9]|s3[01]|d[0-9]|d[12][0-9]|d3[01]|q[0-9]|q1[0-5])\b",
        "special": r"\b(cpsr|spsr|fpscr|fpcr|fpsr)\b"
    }
    
    def __init__(self):
        """Initialize the ARM Assembly plugin."""
        # Note: SmartParser may not have ARM support, so we'll handle that gracefully
        try:
            self.parser = SmartParser(language="arm")
        except Exception:
            self.parser = None
    
    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the given file."""
        path = Path(path) if isinstance(path, str) else path
        return path.suffix.lower() in self.file_extensions
    
    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Parse an ARM assembly file and extract relevant information."""
        file_path = str(path)
        try:
            # Extract symbols
            symbols = self._extract_symbols(content, file_path)
            
            # Convert to IndexShard format
            return {
                "file": file_path,
                "symbols": symbols,
                "language": self.lang
            }
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return {
                "file": file_path,
                "symbols": [],
                "language": self.lang
            }
    
    def _extract_symbols(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract symbols from ARM assembly code."""
        symbols = []
        lines = content.split('\n')
        
        for line_no, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith(('@', '#', '//', '/*')):
                continue
                
            # Extract labels (function/data symbols)
            label_match = re.match(r'^(\w+):', line)
            if label_match:
                symbol_name = label_match.group(1)
                symbol_type = self._determine_symbol_type(lines, line_no)
                symbols.append({
                    "symbol": symbol_name,
                    "kind": symbol_type,
                    "signature": line.strip(),
                    "line": line_no,
                    "span": (line_no, line_no),
                    "docstring": None,
                    "scope": None,
                    "modifiers": [],
                    "metadata": {}
                })
            
            # Extract global symbols
            global_match = re.match(self.DIRECTIVES["global"], line)
            if global_match:
                symbol_name = global_match.group(2)
                symbols.append({
                    "symbol": symbol_name,
                    "kind": "global",
                    "signature": line.strip(),
                    "line": line_no,
                    "span": (line_no, line_no),
                    "docstring": None,
                    "scope": None,
                    "modifiers": [],
                    "metadata": {}
                })
            
            # Extract function directives
            func_match = re.match(self.DIRECTIVES["function"], line)
            if func_match:
                symbol_name = func_match.group(2)
                symbols.append({
                    "symbol": symbol_name,
                    "kind": "function",
                    "signature": line.strip(),
                    "line": line_no,
                    "span": (line_no, line_no),
                    "docstring": None,
                    "scope": None,
                    "modifiers": [],
                    "metadata": {}
                })
            
            # Extract macro definitions
            if re.match(r'^\s*\.macro\s+(\w+)', line):
                macro_match = re.match(r'^\s*\.macro\s+(\w+)', line)
                if macro_match:
                    symbols.append({
                        "symbol": macro_match.group(1),
                        "kind": "macro",
                        "signature": line.strip(),
                        "line": line_no,
                        "span": (line_no, line_no),
                        "docstring": None,
                        "scope": None,
                        "modifiers": [],
                        "metadata": {}
                    })
        
        return symbols
    
    def _determine_symbol_type(self, lines: List[str], line_no: int) -> str:
        """Determine the type of a label based on context."""
        # Look at the next few lines for clues
        for i in range(line_no, min(line_no + 5, len(lines))):
            if i < len(lines):
                line = lines[i].strip()
                # Check for function indicators
                if any(re.search(pattern, line) for pattern in [
                    self.ARM_INSTRUCTIONS["branch"],
                    r'\bpush\b.*\{.*lr.*\}',  # Function prologue
                    r'\.type.*function'
                ]):
                    return "function"
                # Check for data indicators
                if re.search(self.DIRECTIVES["data"], line):
                    return "data"
        
        return "label"
    
    def _extract_imports(self, content: str) -> List[Dict[str, str]]:
        """Extract include directives from ARM assembly code."""
        imports = []
        
        for line in content.split('\n'):
            include_match = re.match(self.DIRECTIVES["include"], line)
            if include_match:
                imports.append({
                    "type": "include",
                    "path": include_match.group(1),
                    "line": line.strip()
                })
        
        return imports
    
    def _detect_frameworks(self, content: str, file_path: str) -> List[str]:
        """Detect embedded frameworks or platforms used."""
        detected = []
        
        # Common embedded frameworks/platforms
        frameworks = {
            "arduino": [r"arduino", r"pinMode", r"digitalWrite"],
            "stm32": [r"stm32", r"STM32", r"HAL_"],
            "nrf": [r"nrf5", r"nRF", r"Nordic"],
            "rtos": [r"FreeRTOS", r"RTOS", r"xTask"],
            "linux": [r"linux", r"syscall", r"\.section.*\.note\.GNU-stack"],
            "bare_metal": [r"vector.*table", r"_start", r"reset.*handler"],
            "android": [r"android", r"dalvik", r"art_"],
            "ios": [r"darwin", r"mach", r"objc_"]
        }
        
        content_lower = content.lower()
        for framework, patterns in frameworks.items():
            if any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns):
                detected.append(framework)
        
        # Detect by file path
        path_lower = file_path.lower()
        if "kernel" in path_lower or "driver" in path_lower:
            detected.append("kernel")
        if "boot" in path_lower:
            detected.append("bootloader")
        
        return list(set(detected))
    
    def _analyze_register_usage(self, content: str) -> Dict[str, int]:
        """Analyze register usage in the code."""
        usage = {}
        
        for reg_type, pattern in self.REGISTERS.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                reg_name = match.lower()
                usage[reg_name] = usage.get(reg_name, 0) + 1
        
        return usage
    
    def _analyze_instructions(self, content: str) -> Dict[str, int]:
        """Analyze instruction usage statistics."""
        stats = {}
        
        for category, pattern in self.ARM_INSTRUCTIONS.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            stats[category] = len(matches)
            
            # Count individual instructions
            for match in matches:
                inst = match.lower()
                stats[f"inst_{inst}"] = stats.get(f"inst_{inst}", 0) + 1
        
        return stats
    
    def _detect_architecture(self, content: str) -> str:
        """Detect ARM architecture version."""
        # Check for explicit architecture directives
        arch_patterns = [
            (r"\.arch\s+(armv\d+\w*)", "explicit"),
            (r"\.cpu\s+(\w+)", "cpu"),
            (r"\.fpu\s+(\w+)", "fpu")
        ]
        
        for pattern, _ in arch_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Detect by instruction usage
        if re.search(self.REGISTERS["aarch64"], content):
            return "aarch64"
        elif re.search(self.ARM_INSTRUCTIONS["thumb"], content):
            return "thumb"
        elif re.search(self.ARM_INSTRUCTIONS["simd"], content):
            return "armv7-neon"
        else:
            return "arm"
    
    def _create_empty_result(self, file_path: str) -> Dict:
        """Create an empty result structure."""
        return {
            "symbols": [],
            "imports": [],
            "frameworks": [],
            "language": self.language,
            "file_path": file_path,
            "metadata": {
                "register_usage": {},
                "instruction_stats": {},
                "architecture": "unknown"
            }
        }
    
    def validate_syntax(self, content: str) -> Tuple[bool, Optional[str]]:
        """Validate ARM assembly syntax."""
        try:
            lines = content.split('\n')
            errors = []
            
            for line_no, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith(('@', '#', '//', '/*')):
                    continue
                
                # Check for common syntax errors
                if ':' in line and not re.match(r'^\w+:', line):
                    if not line.startswith('.'):  # Not a directive
                        errors.append(f"Line {line_no}: Invalid label format")
                
                # Check for unmatched brackets
                if line.count('[') != line.count(']'):
                    errors.append(f"Line {line_no}: Unmatched brackets")
                
                # Check for unmatched braces
                if line.count('{') != line.count('}'):
                    errors.append(f"Line {line_no}: Unmatched braces")
            
            if errors:
                return False, "\n".join(errors)
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def get_symbol_types(self) -> List[str]:
        """Return the types of symbols this plugin can extract."""
        return ["label", "function", "macro", "directive", "data", "global"]
    
    def get_instruction_set_info(self) -> Dict[str, Any]:
        """Return information about supported instruction sets."""
        return {
            "architectures": ["arm", "thumb", "aarch64"],
            "instruction_categories": list(self.ARM_INSTRUCTIONS.keys()),
            "register_types": list(self.REGISTERS.keys()),
            "directives": list(self.DIRECTIVES.keys())
        }
    
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get the definition of a symbol."""
        # This is a simplified implementation - in practice would search indexed files
        return None
    
    def findReferences(self, symbol: str) -> Iterable[Reference]:
        """Find all references to a symbol."""
        # This is a simplified implementation - in practice would search indexed files
        return []
    
    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        """Search for code patterns."""
        # This is a simplified implementation - in practice would search indexed content
        return []


# Plugin registration
plugin = ARMAssemblyPlugin