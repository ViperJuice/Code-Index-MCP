"""
Comprehensive Markdown language plugin using hybrid approach.

This plugin provides advanced Markdown parsing with support for:
- GitHub-flavored Markdown (GFM)
- Front matter extraction (YAML, TOML, JSON)
- MDX with JSX components
- Code fence language detection
- Link and image reference extraction
- Table structure parsing
- Task list detection (GitHub-style checkboxes)
- Math formula detection (LaTeX)
- Wiki-style link detection
- Documentation analysis features
"""

import re
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from ..hybrid_plugin_base import HybridPluginBase
from ..regex_plugin_base import RegexPattern
from ..plugin_template import SymbolType, ParsedSymbol


class Plugin(HybridPluginBase):
    """Comprehensive Markdown plugin with advanced parsing capabilities."""
    
    def __init__(self, config=None, **kwargs):
        """Initialize the Markdown plugin with enhanced features."""
        super().__init__(config, **kwargs)
        
        # Additional symbol types for Markdown
        self.markdown_symbol_types = {
            'heading': SymbolType.CLASS,
            'code_block': SymbolType.FUNCTION,
            'link': SymbolType.IMPORT,
            'image': SymbolType.PROPERTY,
            'table': SymbolType.STRUCT,
            'task_list': SymbolType.ENUM,
            'front_matter': SymbolType.MODULE,
            'math_formula': SymbolType.CONSTANT,
            'reference_definition': SymbolType.VARIABLE,
            'jsx_component': SymbolType.INTERFACE,
            'wiki_link': SymbolType.NAMESPACE
        }
        
        # Compile additional regex patterns
        self._compile_markdown_patterns()
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "markdown"
    
    def get_supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return ['.md', '.markdown', '.mdx', '.mkd']
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return comprehensive symbol patterns for Markdown fallback."""
        return {
            # Headers as classes
            SymbolType.CLASS: r"^(#{1,6})\s+(.+)$",
            
            # Code blocks as functions
            SymbolType.FUNCTION: r"^```(\w*)(?:\s*{([^}]*)})?\s*$",
            
            # Reference definitions as variables
            SymbolType.VARIABLE: r"^\[([^\]]+)\]:\s*(.+)$",
            
            # Links as imports
            SymbolType.IMPORT: r"\[([^\]]+)\]\(([^)]+)\)",
            
            # Images as properties
            SymbolType.PROPERTY: r"!\[([^\]]*)\]\(([^)]+)\)",
            
            # Tables as structs
            SymbolType.STRUCT: r"^\|(.+\|)+\s*$",
            
            # Task lists as enums
            SymbolType.ENUM: r"^\s*[-*+]\s+\[([ x])\]\s+(.+)$",
            
            # Math formulas as constants
            SymbolType.CONSTANT: r"\$\$([^$]+)\$\$|\$([^$]+)\$",
            
            # Wiki links as namespaces
            SymbolType.NAMESPACE: r"\[\[([^\]]+)\]\]",
            
            # Front matter as modules
            SymbolType.MODULE: r"^---\s*$",
            
            # JSX components as interfaces (for MDX)
            SymbolType.INTERFACE: r"<([A-Z][a-zA-Z0-9]*)[^>]*>"
        }
    
    def get_tree_sitter_node_types(self) -> Dict[SymbolType, List[str]]:
        """Return Tree-sitter node types for comprehensive Markdown extraction."""
        return {
            # Headers
            SymbolType.CLASS: ['atx_heading', 'setext_heading'],
            
            # Code blocks
            SymbolType.FUNCTION: ['fenced_code_block', 'indented_code_block'],
            
            # Reference definitions
            SymbolType.VARIABLE: ['link_reference_definition', 'image_reference_definition'],
            
            # Links
            SymbolType.IMPORT: ['link', 'autolink'],
            
            # Images
            SymbolType.PROPERTY: ['image'],
            
            # Tables
            SymbolType.STRUCT: ['table', 'table_row'],
            
            # Task lists
            SymbolType.ENUM: ['task_list_item'],
            
            # Math blocks
            SymbolType.CONSTANT: ['math_block', 'inline_math'],
            
            # Wiki links (if supported by parser)
            SymbolType.NAMESPACE: ['wiki_link'],
            
            # Front matter
            SymbolType.MODULE: ['yaml_front_matter', 'toml_front_matter'],
            
            # JSX elements (for MDX)
            SymbolType.INTERFACE: ['jsx_element', 'jsx_self_closing_element']
        }
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        """Return comprehensive regex patterns for Markdown fallback."""
        return [
            # Headers
            RegexPattern(
                pattern=r"^(#{1,6})\s+(.+)$",
                symbol_type=SymbolType.CLASS,
                name_group=2,
                flags=re.MULTILINE
            ),
            
            # Code blocks with language
            RegexPattern(
                pattern=r"^```(\w*)(?:\s*{([^}]*)})?\s*$",
                symbol_type=SymbolType.FUNCTION,
                name_group=1,
                signature_group=2,
                flags=re.MULTILINE
            ),
            
            # Reference definitions
            RegexPattern(
                pattern=r"^\[([^\]]+)\]:\s*(.+)$",
                symbol_type=SymbolType.VARIABLE,
                name_group=1,
                signature_group=2,
                flags=re.MULTILINE
            ),
            
            # Links
            RegexPattern(
                pattern=r"\[([^\]]+)\]\(([^)]+)\)",
                symbol_type=SymbolType.IMPORT,
                name_group=1,
                signature_group=2
            ),
            
            # Images
            RegexPattern(
                pattern=r"!\[([^\]]*)\]\(([^)]+)\)",
                symbol_type=SymbolType.PROPERTY,
                name_group=1,
                signature_group=2
            ),
            
            # Table headers
            RegexPattern(
                pattern=r"^\|(.+\|)+\s*$",
                symbol_type=SymbolType.STRUCT,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Task list items
            RegexPattern(
                pattern=r"^\s*[-*+]\s+\[([ x])\]\s+(.+)$",
                symbol_type=SymbolType.ENUM,
                name_group=2,
                signature_group=1,
                flags=re.MULTILINE
            ),
            
            # Math formulas (display)
            RegexPattern(
                pattern=r"\$\$([^$]+)\$\$",
                symbol_type=SymbolType.CONSTANT,
                name_group=1
            ),
            
            # Math formulas (inline)
            RegexPattern(
                pattern=r"\$([^$]+)\$",
                symbol_type=SymbolType.CONSTANT,
                name_group=1
            ),
            
            # Wiki links
            RegexPattern(
                pattern=r"\[\[([^\]]+?)(?:\|([^\]]+))?\]\]",
                symbol_type=SymbolType.NAMESPACE,
                name_group=1,
                signature_group=2
            ),
            
            # JSX components (for MDX)
            RegexPattern(
                pattern=r"<([A-Z][a-zA-Z0-9]*)[^>]*(?:/>|>[^<]*</\1>)",
                symbol_type=SymbolType.INTERFACE,
                name_group=1
            )
        ]
    
    def get_fallback_threshold(self) -> float:
        """Return threshold for deciding when to fallback to regex."""
        return 0.15  # Markdown structure is often complex, use lower threshold
    
    def _compile_markdown_patterns(self) -> None:
        """Compile additional Markdown-specific patterns."""
        self.front_matter_pattern = re.compile(
            r'^---\s*\n(.*?)\n---\s*\n',
            re.MULTILINE | re.DOTALL
        )
        
        self.toml_front_matter_pattern = re.compile(
            r'^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n',
            re.MULTILINE | re.DOTALL
        )
        
        self.json_front_matter_pattern = re.compile(
            r'^{\s*\n(.*?)\n}\s*\n',
            re.MULTILINE | re.DOTALL
        )
        
        self.table_pattern = re.compile(
            r'^\|(.+\|)+\s*\n\|[-:\s|]+\|\s*\n((?:\|.+\|\s*\n?)*)',
            re.MULTILINE
        )
        
        self.code_fence_pattern = re.compile(
            r'^```(\w*)\s*(?:\{([^}]*)\})?\s*\n(.*?)\n```\s*$',
            re.MULTILINE | re.DOTALL
        )
        
        self.footnote_pattern = re.compile(
            r'^\[\^([^\]]+)\]:\s*(.+)$',
            re.MULTILINE
        )
    
    def _extract_symbols(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Enhanced symbol extraction with Markdown-specific features."""
        # First get base symbols
        symbols = super()._extract_symbols(content, file_path)
        
        # Add Markdown-specific symbols
        markdown_symbols = self._extract_markdown_specific_symbols(content, file_path)
        symbols.extend(markdown_symbols)
        
        # Sort by line number
        symbols.sort(key=lambda s: s.line)
        
        return symbols
    
    def _extract_markdown_specific_symbols(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract Markdown-specific symbols."""
        symbols = []
        
        # Extract front matter
        symbols.extend(self._extract_front_matter(content))
        
        # Extract tables
        symbols.extend(self._extract_tables(content))
        
        # Extract enhanced code blocks
        symbols.extend(self._extract_enhanced_code_blocks(content))
        
        # Extract footnotes
        symbols.extend(self._extract_footnotes(content))
        
        # Extract task lists
        symbols.extend(self._extract_task_lists(content))
        
        # Extract math formulas
        symbols.extend(self._extract_math_formulas(content))
        
        # Extract wiki links
        symbols.extend(self._extract_wiki_links(content))
        
        # Extract JSX components (for MDX)
        if file_path.endswith('.mdx'):
            symbols.extend(self._extract_jsx_components(content))
        
        return symbols
    
    def _extract_front_matter(self, content: str) -> List[ParsedSymbol]:
        """Extract front matter (YAML, TOML, JSON)."""
        symbols = []
        
        # YAML front matter
        match = self.front_matter_pattern.match(content)
        if match:
            try:
                front_matter = yaml.safe_load(match.group(1))
                symbols.append(ParsedSymbol(
                    name="yaml_front_matter",
                    symbol_type=SymbolType.MODULE,
                    line=1,
                    column=0,
                    end_line=content[:match.end()].count('\n'),
                    signature="---",
                    docstring=f"YAML front matter with {len(front_matter)} keys" if isinstance(front_matter, dict) else "YAML front matter",
                    metadata={
                        "type": "yaml_front_matter",
                        "keys": list(front_matter.keys()) if isinstance(front_matter, dict) else [],
                        "content": front_matter
                    }
                ))
            except yaml.YAMLError:
                pass
        
        # TOML front matter
        match = self.toml_front_matter_pattern.match(content)
        if match:
            symbols.append(ParsedSymbol(
                name="toml_front_matter",
                symbol_type=SymbolType.MODULE,
                line=1,
                column=0,
                end_line=content[:match.end()].count('\n'),
                signature="+++",
                docstring="TOML front matter",
                metadata={
                    "type": "toml_front_matter",
                    "content": match.group(1)
                }
            ))
        
        # JSON front matter
        match = self.json_front_matter_pattern.match(content)
        if match:
            try:
                front_matter = json.loads(match.group(1))
                symbols.append(ParsedSymbol(
                    name="json_front_matter",
                    symbol_type=SymbolType.MODULE,
                    line=1,
                    column=0,
                    end_line=content[:match.end()].count('\n'),
                    signature="{",
                    docstring=f"JSON front matter with {len(front_matter)} keys" if isinstance(front_matter, dict) else "JSON front matter",
                    metadata={
                        "type": "json_front_matter",
                        "keys": list(front_matter.keys()) if isinstance(front_matter, dict) else [],
                        "content": front_matter
                    }
                ))
            except json.JSONDecodeError:
                pass
        
        return symbols
    
    def _extract_tables(self, content: str) -> List[ParsedSymbol]:
        """Extract table structures."""
        symbols = []
        lines = content.splitlines()
        
        for match in self.table_pattern.finditer(content):
            start_line = content[:match.start()].count('\n') + 1
            table_content = match.group(0)
            
            # Parse table structure
            table_lines = table_content.strip().split('\n')
            header_line = table_lines[0] if table_lines else ""
            columns = [col.strip() for col in header_line.split('|') if col.strip()]
            
            symbols.append(ParsedSymbol(
                name=f"table_line_{start_line}",
                symbol_type=SymbolType.STRUCT,
                line=start_line,
                column=match.start() - content.rfind('\n', 0, match.start()) - 1,
                end_line=start_line + table_content.count('\n'),
                signature=header_line.strip(),
                docstring=f"Table with {len(columns)} columns",
                metadata={
                    "type": "table",
                    "columns": columns,
                    "rows": len(table_lines) - 2,  # Excluding header and separator
                    "table_content": table_content
                }
            ))
        
        return symbols
    
    def _extract_enhanced_code_blocks(self, content: str) -> List[ParsedSymbol]:
        """Extract code blocks with enhanced information."""
        symbols = []
        
        for match in self.code_fence_pattern.finditer(content):
            start_line = content[:match.start()].count('\n') + 1
            language = match.group(1) or "text"
            attributes = match.group(2) or ""
            code_content = match.group(3)
            
            # Analyze code content
            line_count = code_content.count('\n') + 1
            
            symbols.append(ParsedSymbol(
                name=f"code_block_{language}_{start_line}",
                symbol_type=SymbolType.FUNCTION,
                line=start_line,
                column=0,
                end_line=start_line + match.group(0).count('\n'),
                signature=f"```{language}",
                docstring=f"{language} code block ({line_count} lines)",
                metadata={
                    "type": "code_block",
                    "language": language,
                    "attributes": attributes,
                    "line_count": line_count,
                    "code_content": code_content[:200] + "..." if len(code_content) > 200 else code_content
                }
            ))
        
        return symbols
    
    def _extract_footnotes(self, content: str) -> List[ParsedSymbol]:
        """Extract footnote definitions."""
        symbols = []
        
        for match in self.footnote_pattern.finditer(content):
            start_line = content[:match.start()].count('\n') + 1
            footnote_id = match.group(1)
            footnote_content = match.group(2)
            
            symbols.append(ParsedSymbol(
                name=f"footnote_{footnote_id}",
                symbol_type=SymbolType.VARIABLE,
                line=start_line,
                column=match.start() - content.rfind('\n', 0, match.start()) - 1,
                signature=f"[^{footnote_id}]:",
                docstring=footnote_content[:100] + "..." if len(footnote_content) > 100 else footnote_content,
                metadata={
                    "type": "footnote",
                    "footnote_id": footnote_id,
                    "content": footnote_content
                }
            ))
        
        return symbols
    
    def _extract_task_lists(self, content: str) -> List[ParsedSymbol]:
        """Extract task list items."""
        symbols = []
        lines = content.splitlines()
        
        task_pattern = re.compile(r'^(\s*)[-*+]\s+\[([ xX])\]\s+(.+)$')
        
        for line_no, line in enumerate(lines, 1):
            match = task_pattern.match(line)
            if match:
                indent = match.group(1)
                status = match.group(2)
                task_text = match.group(3)
                
                symbols.append(ParsedSymbol(
                    name=f"task_{line_no}",
                    symbol_type=SymbolType.ENUM,
                    line=line_no,
                    column=len(indent),
                    signature=f"[{status}] {task_text[:50]}",
                    docstring=task_text,
                    metadata={
                        "type": "task_list_item",
                        "status": "completed" if status.lower() == 'x' else "pending",
                        "indent_level": len(indent) // 2,
                        "text": task_text
                    }
                ))
        
        return symbols
    
    def _extract_math_formulas(self, content: str) -> List[ParsedSymbol]:
        """Extract math formulas (LaTeX)."""
        symbols = []
        
        # Display math ($$...$$)
        display_math_pattern = re.compile(r'\$\$([^$]+)\$\$', re.DOTALL)
        for match in display_math_pattern.finditer(content):
            start_line = content[:match.start()].count('\n') + 1
            formula = match.group(1).strip()
            
            symbols.append(ParsedSymbol(
                name=f"math_display_{start_line}",
                symbol_type=SymbolType.CONSTANT,
                line=start_line,
                column=match.start() - content.rfind('\n', 0, match.start()) - 1,
                signature="$$",
                docstring=f"Display math: {formula[:100]}{'...' if len(formula) > 100 else ''}",
                metadata={
                    "type": "math_display",
                    "formula": formula
                }
            ))
        
        # Inline math ($...$)
        inline_math_pattern = re.compile(r'\$([^$]+)\$')
        for match in inline_math_pattern.finditer(content):
            start_line = content[:match.start()].count('\n') + 1
            formula = match.group(1).strip()
            
            symbols.append(ParsedSymbol(
                name=f"math_inline_{start_line}_{match.start()}",
                symbol_type=SymbolType.CONSTANT,
                line=start_line,
                column=match.start() - content.rfind('\n', 0, match.start()) - 1,
                signature="$",
                docstring=f"Inline math: {formula}",
                metadata={
                    "type": "math_inline",
                    "formula": formula
                }
            ))
        
        return symbols
    
    def _extract_wiki_links(self, content: str) -> List[ParsedSymbol]:
        """Extract wiki-style links [[...]]."""
        symbols = []
        
        wiki_link_pattern = re.compile(r'\[\[([^\]]+?)(?:\|([^\]]+))?\]\]')
        for match in wiki_link_pattern.finditer(content):
            start_line = content[:match.start()].count('\n') + 1
            target = match.group(1)
            display_text = match.group(2) or target
            
            symbols.append(ParsedSymbol(
                name=f"wiki_link_{target}",
                symbol_type=SymbolType.NAMESPACE,
                line=start_line,
                column=match.start() - content.rfind('\n', 0, match.start()) - 1,
                signature=f"[[{target}]]",
                docstring=f"Wiki link to: {target}",
                metadata={
                    "type": "wiki_link",
                    "target": target,
                    "display_text": display_text
                }
            ))
        
        return symbols
    
    def _extract_jsx_components(self, content: str) -> List[ParsedSymbol]:
        """Extract JSX components (for MDX files)."""
        symbols = []
        
        # JSX component pattern
        jsx_pattern = re.compile(r'<([A-Z][a-zA-Z0-9]*)[^>]*(?:/>|>[^<]*</\\1>)', re.DOTALL)
        
        for match in jsx_pattern.finditer(content):
            start_line = content[:match.start()].count('\n') + 1
            component_name = match.group(1)
            full_tag = match.group(0)
            
            # Extract props
            props_match = re.search(r'<' + component_name + r'([^>]*)', full_tag)
            props = props_match.group(1).strip() if props_match else ""
            
            symbols.append(ParsedSymbol(
                name=component_name,
                symbol_type=SymbolType.INTERFACE,
                line=start_line,
                column=match.start() - content.rfind('\n', 0, match.start()) - 1,
                end_line=start_line + full_tag.count('\n'),
                signature=f"<{component_name}{props[:50]}{'...' if len(props) > 50 else ''}>",
                docstring=f"JSX component: {component_name}",
                metadata={
                    "type": "jsx_component",
                    "component_name": component_name,
                    "props": props,
                    "is_self_closing": full_tag.endswith('/>')
                }
            ))
        
        return symbols
    
    def get_markdown_statistics(self) -> Dict[str, Any]:
        """Get Markdown-specific statistics."""
        base_stats = self.get_statistics()
        
        # Add Markdown-specific stats
        markdown_stats = {
            "markdown_features": {
                "front_matter_support": True,
                "table_parsing": True,
                "code_block_analysis": True,
                "task_list_detection": True,
                "math_formula_support": True,
                "wiki_link_support": True,
                "jsx_component_support": True,
                "footnote_support": True
            },
            "supported_formats": {
                "github_flavored_markdown": True,
                "commonmark": True,
                "mdx": True,
                "front_matter_yaml": True,
                "front_matter_toml": True,
                "front_matter_json": True
            }
        }
        
        return {**base_stats, **markdown_stats}
