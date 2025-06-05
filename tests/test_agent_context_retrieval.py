#!/usr/bin/env python3
"""Demonstrate context retrieval optimized for coding agents."""

import sys
from pathlib import Path
import json
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.plugins.js_plugin.plugin import Plugin as JSPlugin
from mcp_server.plugins.jvm_plugin.plugin import Plugin as JVMPlugin

@dataclass
class EditContext:
    """Context information for a coding agent to make edits."""
    file_path: str
    start_line: int
    end_line: int
    symbol_name: str
    symbol_type: str
    full_context: str
    edit_instructions: str
    related_symbols: List[Dict[str, Any]]
    file_imports: List[str]
    language: str

class AgentContextRetriever:
    """Retrieves optimized context for coding agents."""
    
    def __init__(self):
        # Initialize without SQLite to avoid setup issues
        self.plugins = {
            "python": PythonPlugin(None),
            "javascript": JSPlugin(None),
            "java": JVMPlugin(None)
        }
        self.file_cache = {}
    
    def search_and_prepare_context(self, query: str, intent: str) -> List[EditContext]:
        """Search for code and prepare edit contexts for agent."""
        # First, find relevant code
        search_results = self._search_code(query)
        
        # Then prepare detailed contexts for each result
        edit_contexts = []
        for result in search_results[:3]:  # Top 3 results
            context = self._prepare_edit_context(result, intent)
            if context:
                edit_contexts.append(context)
        
        return edit_contexts
    
    def _search_code(self, query: str) -> List[Dict[str, Any]]:
        """Search for code across all indexed files."""
        results = []
        
        # Search using each plugin
        for lang, plugin in self.plugins.items():
            try:
                plugin_results = plugin.search(query, {"limit": 5})
                for r in plugin_results:
                    r["language"] = lang
                    results.append(r)
            except:
                pass
        
        # Sort by relevance
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results
    
    def _prepare_edit_context(self, search_result: Dict[str, Any], intent: str) -> Optional[EditContext]:
        """Prepare comprehensive context for editing."""
        file_path = search_result["file"]
        
        # Load file content (with caching)
        if file_path not in self.file_cache:
            try:
                self.file_cache[file_path] = Path(file_path).read_text()
            except:
                return None
        
        content = self.file_cache[file_path]
        lines = content.split('\n')
        
        # Get symbol information from search result
        symbol_line = search_result["line"]
        symbol_name = search_result["symbol"]
        symbol_type = search_result.get("kind", "unknown")
        
        # Determine context boundaries
        start_line, end_line = self._find_symbol_boundaries(
            lines, symbol_line - 1, symbol_type, search_result["language"]
        )
        
        # Extract the full context
        full_context = '\n'.join(lines[start_line:end_line + 1])
        
        # Find related symbols in the same file
        related_symbols = self._find_related_symbols(
            file_path, symbol_name, search_result["language"]
        )
        
        # Extract imports/dependencies
        imports = self._extract_imports(lines, search_result["language"])
        
        # Generate edit instructions based on intent
        edit_instructions = self._generate_edit_instructions(
            symbol_name, symbol_type, intent, full_context
        )
        
        return EditContext(
            file_path=file_path,
            start_line=start_line + 1,  # Convert to 1-based
            end_line=end_line + 1,
            symbol_name=symbol_name,
            symbol_type=symbol_type,
            full_context=full_context,
            edit_instructions=edit_instructions,
            related_symbols=related_symbols,
            file_imports=imports,
            language=search_result["language"]
        )
    
    def _find_symbol_boundaries(self, lines: List[str], target_line: int, 
                               symbol_type: str, language: str) -> Tuple[int, int]:
        """Find the start and end lines of a symbol."""
        # Language-specific boundary detection
        if language == "python":
            return self._find_python_boundaries(lines, target_line, symbol_type)
        elif language == "javascript":
            return self._find_javascript_boundaries(lines, target_line, symbol_type)
        elif language == "java":
            return self._find_java_boundaries(lines, target_line, symbol_type)
        else:
            # Default: include some context
            start = max(0, target_line - 5)
            end = min(len(lines) - 1, target_line + 15)
            return start, end
    
    def _find_python_boundaries(self, lines: List[str], target_line: int, 
                               symbol_type: str) -> Tuple[int, int]:
        """Find Python symbol boundaries."""
        start = target_line
        end = target_line
        
        # Find start (including decorators)
        while start > 0:
            line = lines[start - 1].strip()
            if line.startswith('@') or line == '':
                start -= 1
            else:
                break
        
        # Find end based on indentation
        if target_line < len(lines):
            base_indent = len(lines[target_line]) - len(lines[target_line].lstrip())
            end = target_line + 1
            
            while end < len(lines):
                line = lines[end]
                if line.strip() == '':
                    end += 1
                    continue
                    
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= base_indent and line.strip():
                    break
                end += 1
        
        return start, min(end - 1, len(lines) - 1)
    
    def _find_javascript_boundaries(self, lines: List[str], target_line: int,
                                   symbol_type: str) -> Tuple[int, int]:
        """Find JavaScript symbol boundaries."""
        start = target_line
        end = target_line
        
        # Simple brace counting for functions/classes
        if symbol_type in ["function", "class", "method"]:
            # Find opening brace
            brace_count = 0
            for i in range(target_line, len(lines)):
                line = lines[i]
                brace_count += line.count('{') - line.count('}')
                if brace_count > 0:
                    # Found opening, now find closing
                    for j in range(i + 1, len(lines)):
                        line = lines[j]
                        brace_count += line.count('{') - line.count('}')
                        if brace_count == 0:
                            end = j
                            break
                    break
        
        return start, end
    
    def _find_java_boundaries(self, lines: List[str], target_line: int,
                             symbol_type: str) -> Tuple[int, int]:
        """Find Java symbol boundaries."""
        start = target_line
        end = target_line
        
        # Include annotations
        while start > 0 and lines[start - 1].strip().startswith('@'):
            start -= 1
        
        # Find method/class end by brace counting
        if symbol_type in ["method", "class"]:
            brace_count = 0
            for i in range(target_line, len(lines)):
                line = lines[i]
                brace_count += line.count('{') - line.count('}')
                if brace_count > 0:
                    for j in range(i + 1, len(lines)):
                        line = lines[j]
                        brace_count += line.count('{') - line.count('}')
                        if brace_count == 0:
                            end = j
                            break
                    break
        
        return start, end
    
    def _find_related_symbols(self, file_path: str, symbol_name: str, 
                             language: str) -> List[Dict[str, Any]]:
        """Find symbols that might be related to the target symbol."""
        related = []
        
        # Re-index the file to find all symbols
        plugin = self.plugins.get(language)
        if not plugin:
            return related
        
        try:
            content = self.file_cache.get(file_path, Path(file_path).read_text())
            result = plugin.indexFile(file_path, content)
            
            if result and "symbols" in result:
                for symbol in result["symbols"]:
                    # Look for symbols that might be related
                    if (symbol["symbol"] != symbol_name and 
                        (symbol_name.lower() in symbol["symbol"].lower() or
                         symbol["symbol"].lower() in symbol_name.lower() or
                         symbol.get("kind") == "test")):  # Include tests
                        related.append({
                            "name": symbol["symbol"],
                            "type": symbol.get("kind", "unknown"),
                            "line": symbol["line"]
                        })
        except:
            pass
        
        return related[:5]  # Limit to 5 related symbols
    
    def _extract_imports(self, lines: List[str], language: str) -> List[str]:
        """Extract import statements from the file."""
        imports = []
        
        if language == "python":
            for line in lines:
                if line.strip().startswith(('import ', 'from ')):
                    imports.append(line.strip())
                elif not line.strip().startswith('#') and line.strip() and not line[0].isspace():
                    # Stop at first non-import, non-comment line
                    if not line.strip().startswith(('"""', "'''")):
                        break
        
        elif language == "javascript":
            for line in lines:
                if line.strip().startswith(('import ', 'const ', 'require(')):
                    imports.append(line.strip())
                elif line.strip() and not line.strip().startswith('//'):
                    # Stop at first non-import line
                    if not line.strip().startswith(('import', 'const', 'require')):
                        break
        
        elif language == "java":
            for line in lines:
                if line.strip().startswith('import '):
                    imports.append(line.strip())
                elif line.strip().startswith('package '):
                    imports.insert(0, line.strip())  # Package at the beginning
                elif line.strip() and not line.strip().startswith(('import', '//', '/*', '*')):
                    break
        
        return imports
    
    def _generate_edit_instructions(self, symbol_name: str, symbol_type: str,
                                   intent: str, context: str) -> str:
        """Generate specific instructions for the coding agent."""
        instructions = f"Edit the {symbol_type} '{symbol_name}' to {intent}.\n\n"
        
        # Add specific guidance based on intent
        if "error handling" in intent.lower():
            instructions += "- Add appropriate try-catch blocks or error checks\n"
            instructions += "- Return meaningful error messages\n"
            instructions += "- Log errors appropriately\n"
        
        elif "validation" in intent.lower():
            instructions += "- Add input validation checks\n"
            instructions += "- Validate data types and ranges\n"
            instructions += "- Return validation errors clearly\n"
        
        elif "optimize" in intent.lower():
            instructions += "- Improve performance where possible\n"
            instructions += "- Reduce redundant operations\n"
            instructions += "- Consider caching if applicable\n"
        
        elif "test" in intent.lower():
            instructions += "- Add unit tests for this function\n"
            instructions += "- Cover edge cases\n"
            instructions += "- Include both positive and negative test cases\n"
        
        instructions += f"\nCurrent implementation:\n```\n{context[:200]}...\n```"
        
        return instructions
    
    def format_for_agent(self, contexts: List[EditContext]) -> str:
        """Format the contexts for a coding agent."""
        output = []
        
        for i, ctx in enumerate(contexts, 1):
            output.append(f"## Edit Context {i}")
            output.append(f"**File**: `{ctx.file_path}`")
            output.append(f"**Lines**: {ctx.start_line}-{ctx.end_line}")
            output.append(f"**Symbol**: `{ctx.symbol_name}` ({ctx.symbol_type})")
            output.append(f"**Language**: {ctx.language}")
            
            output.append("\n### Required Imports")
            for imp in ctx.file_imports[:5]:  # Show first 5 imports
                output.append(f"- {imp}")
            
            if ctx.related_symbols:
                output.append("\n### Related Symbols in File")
                for sym in ctx.related_symbols:
                    output.append(f"- `{sym['name']}` ({sym['type']}) at line {sym['line']}")
            
            output.append("\n### Edit Instructions")
            output.append(ctx.edit_instructions)
            
            output.append("\n### Code to Edit")
            output.append("```" + ctx.language)
            output.append(ctx.full_context)
            output.append("```")
            output.append("\n---\n")
        
        return '\n'.join(output)

def demonstrate_agent_context():
    """Demonstrate context retrieval for coding agents."""
    print("="*70)
    print("CODING AGENT CONTEXT RETRIEVAL DEMONSTRATION")
    print("="*70)
    
    retriever = AgentContextRetriever()
    
    # Index some sample files
    sample_files = [
        ("examples/user_auth.py", """import hashlib
import jwt
from datetime import datetime, timedelta

def authenticate_user(username, password):
    # TODO: Add proper validation
    user = get_user(username)
    if user and user.password == password:
        return generate_token(user)
    return None

def generate_token(user):
    payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, 'secret', algorithm='HS256')

def validate_token(token):
    try:
        payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        return payload
    except:
        return None
""", "python"),
        
        ("examples/api_handler.js", """const express = require('express');
const router = express.Router();

router.post('/api/users', async (req, res) => {
    // Create new user
    const userData = req.body;
    
    // TODO: Add validation
    const user = await User.create(userData);
    
    res.json({ success: true, user });
});

router.get('/api/users/:id', async (req, res) => {
    const userId = req.params.id;
    const user = await User.findById(userId);
    
    if (!user) {
        return res.status(404).json({ error: 'User not found' });
    }
    
    res.json(user);
});
""", "javascript")
    ]
    
    # Index the sample files
    for file_path, content, language in sample_files:
        plugin = retriever.plugins.get(language)
        if plugin:
            Path(file_path).parent.mkdir(exist_ok=True)
            Path(file_path).write_text(content)
            plugin.indexFile(file_path, content)
    
    # Test queries with different intents
    test_cases = [
        {
            "query": "authenticate user function",
            "intent": "add proper input validation and error handling"
        },
        {
            "query": "create user API endpoint", 
            "intent": "add validation for required fields and data types"
        },
        {
            "query": "token validation",
            "intent": "improve error handling and add expiration check"
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*70}")
        print(f"Query: \"{test['query']}\"")
        print(f"Intent: {test['intent']}")
        print("="*70)
        
        # Get contexts
        contexts = retriever.search_and_prepare_context(test["query"], test["intent"])
        
        if contexts:
            # Show what the agent would receive
            agent_input = retriever.format_for_agent(contexts)
            print(agent_input)
        else:
            print("No relevant code found.")
    
    # Clean up
    for file_path, _, _ in sample_files:
        Path(file_path).unlink(missing_ok=True)
    Path("examples").rmdir()

if __name__ == "__main__":
    demonstrate_agent_context()