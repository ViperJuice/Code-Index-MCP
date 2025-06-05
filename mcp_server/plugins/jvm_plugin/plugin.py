from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict, Any
import hashlib

from ...plugin_base import (
    IPlugin,
    IndexShard,
    SymbolDef,
    Reference,
    SearchResult,
    SearchOpts,
)

from ...utils.fuzzy_indexer import FuzzyIndexer
from ...storage.sqlite_store import SQLiteStore


class JvmParser:
    """Unified parser for Java and Kotlin languages."""
    
    def __init__(self):
        # Java patterns - improved for better symbol detection
        self.java_class_pattern = re.compile(
            r'^\s*(?:(?:public|private|protected|static|abstract|final)\s+)*(class|interface|enum)\s+(\w+)(?:<.*?>)?.*?\{',
            re.MULTILINE
        )
        # Method pattern - handles generics before return type
        self.java_method_pattern = re.compile(
            r'^\s*(?:(?:public|private|protected|static|abstract|final|synchronized|native)\s+)*(?:<[^>]*>\s+)?(\w+(?:<[^>]*>)?(?:\[\])*)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[^{;]+)?\s*(?:\{|;)',
            re.MULTILINE
        )
        # Pattern for methods with generics before return type (more permissive)
        self.java_generic_method_pattern = re.compile(
            r'^\s*(?:(?:public|private|protected|static|abstract|final|synchronized|native)\s+)+<.*?>\s+(\w+)(?:<.*?>)?\s+(\w+)\s*\(',
            re.MULTILINE
        )
        self.java_annotation_pattern = re.compile(
            r'^\s*@(\w+)(?:\([^)]*\))?',
            re.MULTILINE
        )
        self.java_field_pattern = re.compile(
            r'^\s*(?:(?:public|private|protected|static|final|volatile|transient)\s+)*(\w+(?:<[^>]*>)?(?:\[\])*)\s+(\w+)\s*(?:=|;)',
            re.MULTILINE
        )
        
        # Kotlin patterns - improved for better symbol detection
        self.kotlin_class_pattern = re.compile(
            r'^\s*(?:(?:public|private|protected|internal|open|abstract|final|sealed|data|inner)\s+)*(?:class|interface|object|enum\s+class)\s+(\w+)(?:<[^>]*>)?(?:\s*\([^)]*\))?(?:\s*:\s*[^{\n]+)?(?:\s*\{)?',
            re.MULTILINE
        )
        # Separate pattern for object declarations
        self.kotlin_object_pattern = re.compile(
            r'^\s*(?:(?:public|private|protected|internal)\s+)*object\s+(\w+)(?:\s*:\s*[^{]+)?\s*\{',
            re.MULTILINE
        )
        self.kotlin_function_pattern = re.compile(
            r'^\s*(?:(?:public|private|protected|internal|inline|suspend|operator|infix|tailrec|override|const)\s+)*fun\s+(?:<.*?>\s+)?(\w+)\s*\([^)]*\)(?:\s*:\s*[^{=\n]+)?(?:\s*[{=])?',
            re.MULTILINE
        )
        self.kotlin_property_pattern = re.compile(
            r'^\s*(?:(?:public|private|protected|internal|const|lateinit|override)\s+)*(?:val|var)\s+(\w+)\s*:\s*([^=\n{]+)(?:\s*[=\n{]|$)',
            re.MULTILINE
        )
        self.kotlin_extension_pattern = re.compile(
            r'^\s*(?:(?:public|private|protected|internal|inline)\s+)*fun\s+(?:<.*?>\s+)?(\w+(?:<[^>]*>)?)\.\s*(\w+)\s*\([^)]*\)',
            re.MULTILINE
        )
        # Inline and value class patterns
        self.kotlin_inline_class_pattern = re.compile(
            r'^\s*(?:@JvmInline\s+)?(?:inline\s+class|value\s+class)\s+(\w+)\s*\([^)]*\)',
            re.MULTILINE
        )
        
        # Package and import patterns (shared)
        self.package_pattern = re.compile(r'^\s*package\s+([\w.]+)', re.MULTILINE)
        self.import_pattern = re.compile(r'^\s*import\s+((?:static\s+)?[\w.*]+)', re.MULTILINE)
        
        # Generic type pattern
        self.generic_pattern = re.compile(r'<([^<>]+(?:<[^<>]*>[^<>]*)*)>')
    
    def is_java_file(self, content: str) -> bool:
        """Check if content appears to be Java based on syntax patterns."""
        java_indicators = [
            r'\bpublic\s+class\b',
            r'\bpublic\s+static\s+void\s+main\b',
            r'\bimport\s+java\.',
            r'\@Override\b',
            r'\bSystem\.out\.println\b'
        ]
        return any(re.search(pattern, content) for pattern in java_indicators)
    
    def is_kotlin_file(self, content: str) -> bool:
        """Check if content appears to be Kotlin based on syntax patterns."""
        kotlin_indicators = [
            r'\bfun\s+\w+\s*\(',
            r'\bval\s+\w+\s*[:=]',
            r'\bvar\s+\w+\s*[:=]',
            r'\bobject\s+\w+',
            r'\bdata\s+class\b',
            r'\bsealed\s+class\b'
        ]
        return any(re.search(pattern, content) for pattern in kotlin_indicators)
    
    def parse_java_file(self, content: str) -> Dict[str, Any]:
        """Parse Java file content and extract symbols."""
        symbols = {
            'classes': [],
            'methods': [],
            'fields': [],
            'annotations': [],
            'package': None,
            'imports': []
        }
        
        lines = content.split('\n')
        
        # Parse package
        package_match = self.package_pattern.search(content)
        if package_match:
            symbols['package'] = package_match.group(1)
        
        # Parse imports
        for match in self.import_pattern.finditer(content):
            symbols['imports'].append(match.group(1))
        
        # Parse classes/interfaces/enums
        for match in self.java_class_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            class_type = match.group(1)  # class, interface, or enum
            class_name = match.group(2)  # class name
            full_signature = match.group(0).strip()
            
            # Determine class type
            if class_type == 'interface':
                kind = 'interface'
            elif class_type == 'enum':
                kind = 'enum'
            else:
                kind = 'class'
            
            symbols['classes'].append({
                'name': class_name,
                'line': line_num,
                'signature': full_signature,
                'kind': kind
            })
        
        # Parse methods
        class_names = {symbol['name'] for symbol in symbols['classes']}
        processed_methods = set()  # To avoid duplicates
        
        # Regular method pattern
        for match in self.java_method_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            return_type = match.group(1)
            method_name = match.group(2)
            full_match = match.group(0).strip()
            
            # Skip if this looks like a class declaration or matches a class name
            if (return_type in ['class', 'interface', 'enum'] or 
                method_name in class_names or
                'class ' in full_match or 'interface ' in full_match or 'enum ' in full_match):
                continue
            
            method_key = (method_name, line_num)
            if method_key not in processed_methods:
                symbols['methods'].append({
                    'name': method_name,
                    'line': line_num,
                    'signature': full_match,
                    'return_type': return_type
                })
                processed_methods.add(method_key)
        
        # Generic method pattern (simplified - just find the methods)
        for match in self.java_generic_method_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            return_type = match.group(1)
            method_name = match.group(2)
            
            # Create a signature from the line content
            lines = content.split('\n')
            if line_num <= len(lines):
                line_content = lines[line_num - 1].strip()
                # Try to get the full method signature
                full_signature = line_content
                if '{' not in line_content and line_num < len(lines):
                    # Method might span multiple lines
                    for i in range(line_num, min(line_num + 3, len(lines))):
                        if '{' in lines[i] or ';' in lines[i]:
                            full_signature = ' '.join(lines[line_num-1:i+1]).strip()
                            break
            else:
                full_signature = match.group(0).strip()
            
            # Skip if this looks like a class declaration or matches a class name
            if (return_type in ['class', 'interface', 'enum'] or 
                method_name in class_names or
                'class ' in full_signature or 'interface ' in full_signature or 'enum ' in full_signature):
                continue
            
            method_key = (method_name, line_num)
            if method_key not in processed_methods:
                symbols['methods'].append({
                    'name': method_name,
                    'line': line_num,
                    'signature': full_signature,
                    'return_type': return_type
                })
                processed_methods.add(method_key)
        
        # Parse fields
        for match in self.java_field_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            field_type = match.group(1)
            field_name = match.group(2)
            full_match = match.group(0).strip()
            
            # Skip if this looks like a class/method declaration
            if (field_type in ['class', 'interface', 'enum', 'void'] or
                '(' in full_match or ')' in full_match or
                'class ' in full_match or 'interface ' in full_match):
                continue
            
            symbols['fields'].append({
                'name': field_name,
                'line': line_num,
                'signature': full_match,
                'type': field_type
            })
        
        # Parse annotations
        for match in self.java_annotation_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            annotation_name = match.group(1)
            
            symbols['annotations'].append({
                'name': annotation_name,
                'line': line_num,
                'signature': match.group(0).strip()
            })
        
        return symbols
    
    def parse_kotlin_file(self, content: str) -> Dict[str, Any]:
        """Parse Kotlin file content and extract symbols."""
        symbols = {
            'classes': [],
            'functions': [],
            'properties': [],
            'extensions': [],
            'package': None,
            'imports': []
        }
        
        # Parse package
        package_match = self.package_pattern.search(content)
        if package_match:
            symbols['package'] = package_match.group(1)
        
        # Parse imports
        for match in self.import_pattern.finditer(content):
            symbols['imports'].append(match.group(1))
        
        # Track processed objects to avoid duplicates
        processed_objects = set()
        
        # Parse classes/interfaces/objects
        for match in self.kotlin_class_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            class_name = match.group(1)
            full_signature = match.group(0).strip()
            
            # Determine class type
            if 'object' in full_signature and not ('class' in full_signature or 'interface' in full_signature):
                kind = 'object'
                processed_objects.add((class_name, line_num))
            elif 'interface' in full_signature:
                kind = 'interface'
            elif 'enum class' in full_signature:
                kind = 'enum'
            elif 'data class' in full_signature:
                kind = 'data_class'
            elif 'sealed class' in full_signature:
                kind = 'sealed_class'
            else:
                kind = 'class'
            
            symbols['classes'].append({
                'name': class_name,
                'line': line_num,
                'signature': full_signature,
                'kind': kind
            })
        
        # Parse standalone objects (skip if already processed)
        for match in self.kotlin_object_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            object_name = match.group(1)
            full_signature = match.group(0).strip()
            
            if (object_name, line_num) not in processed_objects:
                symbols['classes'].append({
                    'name': object_name,
                    'line': line_num,
                    'signature': full_signature,
                    'kind': 'object'
                })
        
        # Parse inline/value classes
        for match in self.kotlin_inline_class_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            class_name = match.group(1)
            full_signature = match.group(0).strip()
            
            symbols['classes'].append({
                'name': class_name,
                'line': line_num,
                'signature': full_signature,
                'kind': 'inline_class' if 'inline class' in full_signature else 'value_class'
            })
        
        # Parse functions
        for match in self.kotlin_function_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            function_name = match.group(1)
            
            symbols['functions'].append({
                'name': function_name,
                'line': line_num,
                'signature': match.group(0).strip()
            })
        
        # Parse properties
        for match in self.kotlin_property_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            property_name = match.group(1)
            property_type = match.group(2).strip()
            
            symbols['properties'].append({
                'name': property_name,
                'line': line_num,
                'signature': match.group(0).strip(),
                'type': property_type
            })
        
        # Parse extension functions
        for match in self.kotlin_extension_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            receiver_type = match.group(1)
            function_name = match.group(2)
            
            # Strip generic parameters from receiver type for the symbol name
            receiver_base = receiver_type.split('<')[0] if '<' in receiver_type else receiver_type
            
            symbols['extensions'].append({
                'name': f"{receiver_base}.{function_name}",
                'line': line_num,
                'signature': match.group(0).strip(),
                'receiver': receiver_type,
                'function': function_name
            })
        
        return symbols


class Plugin(IPlugin):
    lang = "jvm"

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._parser = JvmParser()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), 
                Path.cwd().name,
                {"language": "jvm"}
            )
        
        self._preindex()

    def _preindex(self) -> None:
        """Pre-index all JVM files in the current directory."""
        extensions = ["*.java", "*.kt", "*.kts"]
        build_files = ["pom.xml", "build.gradle", "build.gradle.kts"]
        
        for pattern in extensions:
            for path in Path(".").rglob(pattern):
                try:
                    text = path.read_text(encoding='utf-8')
                    self._indexer.add_file(str(path), text)
                except Exception:
                    continue
        
        # Index build files
        for build_file in build_files:
            for path in Path(".").rglob(build_file):
                try:
                    text = path.read_text(encoding='utf-8')
                    self._indexer.add_file(str(path), text)
                except Exception:
                    continue

    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches JVM files."""
        path_obj = Path(path) if isinstance(path, str) else path
        
        # Support Java and Kotlin source files
        if path_obj.suffix in [".java", ".kt", ".kts"]:
            return True
        
        # Support build files
        if path_obj.name in ["pom.xml", "build.gradle", "build.gradle.kts"]:
            return True
        
        return False

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a JVM file and extract symbols."""
        if isinstance(path, str):
            path = Path(path)
        
        self._indexer.add_file(str(path), content)
        
        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            # Handle relative path calculation safely
            try:
                if path.is_absolute():
                    relative_path = str(path.relative_to(Path.cwd()))
                else:
                    relative_path = str(path)
            except ValueError:
                # If path is not under current directory, use the filename
                relative_path = path.name
            
            # Determine language
            if path.suffix == ".java":
                language = "java"
            elif path.suffix in [".kt", ".kts"]:
                language = "kotlin"
            elif path.name in ["pom.xml", "build.gradle", "build.gradle.kts"]:
                language = "build"
            else:
                language = "jvm"
            
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                relative_path,
                language=language,
                size=len(content),
                hash=file_hash
            )

        symbols: List[Dict[str, Any]] = []
        
        # Handle build files
        if path.name == "pom.xml":
            return self._parse_maven_pom(path, content, file_id)
        elif path.name in ["build.gradle", "build.gradle.kts"]:
            return self._parse_gradle_build(path, content, file_id)
        
        # Parse source files
        if path.suffix == ".java" or self._parser.is_java_file(content):
            parsed_symbols = self._parser.parse_java_file(content)
            return self._create_index_shard(path, content, parsed_symbols, file_id, "java")
        elif path.suffix in [".kt", ".kts"] or self._parser.is_kotlin_file(content):
            parsed_symbols = self._parser.parse_kotlin_file(content)
            return self._create_index_shard(path, content, parsed_symbols, file_id, "kotlin")
        
        # Fallback for unknown file types
        return {"file": str(path), "symbols": [], "language": "jvm"}
    
    def _create_index_shard(self, path: Path, content: str, parsed_symbols: Dict[str, Any], 
                           file_id: Optional[int], language: str) -> IndexShard:
        """Create index shard from parsed symbols."""
        symbols: List[Dict[str, Any]] = []
        
        # Process different symbol types based on language
        if language == "java":
            symbol_mappings = {
                'classes': 'class',
                'methods': 'method',
                'fields': 'field',
                'annotations': 'annotation'
            }
        else:  # kotlin
            symbol_mappings = {
                'classes': 'class',
                'functions': 'function',
                'properties': 'property',
                'extensions': 'extension'
            }
        
        # Track symbol names to prioritize classes over constructors
        symbol_names = set()
        class_names = set()
        
        # First pass: collect class names
        for symbol_type, symbol_list in parsed_symbols.items():
            if symbol_type == 'classes':
                for symbol_data in symbol_list:
                    class_names.add(symbol_data['name'])
        
        for symbol_type, symbol_list in parsed_symbols.items():
            if symbol_type in ['package', 'imports'] or not symbol_list:
                continue
            
            kind = symbol_mappings.get(symbol_type, 'unknown')
            
            for symbol_data in symbol_list:
                name = symbol_data['name']
                line = symbol_data['line']
                signature = symbol_data['signature']
                
                # Use specific kind from symbol data if available
                specific_kind = symbol_data.get('kind', kind)
                
                # Skip constructors that have the same name as a class (unless no class was found)
                if (specific_kind == 'method' and name in class_names and 
                    '(' in signature and signature.strip().endswith('{')):
                    continue
                
                # Store symbol in SQLite if available
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        name,
                        specific_kind,
                        line,
                        line + 1,  # End line approximation
                        signature=signature
                    )
                    # Add to fuzzy indexer with metadata
                    self._indexer.add_symbol(
                        name, 
                        str(path), 
                        line,
                        {"symbol_id": symbol_id, "file_id": file_id}
                    )

                symbols.append({
                    "symbol": name,
                    "kind": specific_kind,
                    "signature": signature,
                    "line": line,
                    "span": (line, line + 1),
                })
                symbol_names.add(name)
        
        return {
            "file": str(path), 
            "symbols": symbols, 
            "language": language,
            "package": parsed_symbols.get('package'),
            "imports": parsed_symbols.get('imports', [])
        }
    
    def _parse_maven_pom(self, path: Path, content: str, file_id: Optional[int]) -> IndexShard:
        """Parse Maven pom.xml file for dependency information."""
        symbols = []
        
        try:
            root = ET.fromstring(content)
            
            # Handle namespace
            namespace = ''
            if root.tag.startswith('{'):
                namespace = root.tag.split('}')[0] + '}'
            
            # Parse artifact coordinates
            group_id_elem = root.find(f'{namespace}groupId')
            artifact_id_elem = root.find(f'{namespace}artifactId')
            version_elem = root.find(f'{namespace}version')
            
            if group_id_elem is not None and artifact_id_elem is not None:
                group_id = group_id_elem.text or ""
                artifact_id = artifact_id_elem.text or ""
                version = version_elem.text if version_elem is not None else "unknown"
                
                symbols.append({
                    "symbol": f"{group_id}:{artifact_id}",
                    "kind": "artifact",
                    "signature": f"artifact {group_id}:{artifact_id}:{version}",
                    "line": 1,
                    "span": (1, 1),
                })
            
            # Parse dependencies
            dependencies = root.find(f'{namespace}dependencies')
            if dependencies is not None:
                for dep in dependencies.findall(f'{namespace}dependency'):
                    dep_group = dep.find(f'{namespace}groupId')
                    dep_artifact = dep.find(f'{namespace}artifactId')
                    dep_version = dep.find(f'{namespace}version')
                    
                    if dep_group is not None and dep_artifact is not None:
                        dep_name = f"{dep_group.text}:{dep_artifact.text}"
                        dep_ver = dep_version.text if dep_version is not None else "unknown"
                        
                        symbols.append({
                            "symbol": dep_name,
                            "kind": "dependency",
                            "signature": f"dependency {dep_name}:{dep_ver}",
                            "line": 1,  # XML line numbers would need more sophisticated parsing
                            "span": (1, 1),
                        })
                        
                        if self._sqlite_store and file_id:
                            symbol_id = self._sqlite_store.store_symbol(
                                file_id,
                                dep_name,
                                "dependency",
                                1,
                                1,
                                signature=f"dependency {dep_name}:{dep_ver}"
                            )
                            self._indexer.add_symbol(
                                dep_name, 
                                str(path), 
                                1,
                                {"symbol_id": symbol_id, "file_id": file_id}
                            )
            
        except ET.ParseError:
            # Handle malformed XML gracefully
            pass
        
        return {"file": str(path), "symbols": symbols, "language": "maven"}
    
    def _parse_gradle_build(self, path: Path, content: str, file_id: Optional[int]) -> IndexShard:
        """Parse Gradle build file for dependency information."""
        symbols = []
        lines = content.split('\n')
        
        # Parse dependencies block
        in_dependencies = False
        dependency_pattern = re.compile(r'''(?:implementation|compile|api|testImplementation|testCompile|runtimeOnly|compileOnly)\s*['"]([\w\.\-:]+)['"]''')
        plugin_pattern = re.compile(r'''(?:id\s*['"]([\w\.\-]+)['"]|apply\s+plugin:\s*['"]([\w\.\-]+)['"])''')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Track dependencies block
            if 'dependencies' in line and '{' in line:
                in_dependencies = True
                continue
            elif in_dependencies and '}' in line:
                in_dependencies = False
                continue
            
            # Parse dependencies
            if in_dependencies:
                dep_match = dependency_pattern.search(line)
                if dep_match:
                    dep_name = dep_match.group(1)
                    symbols.append({
                        "symbol": dep_name,
                        "kind": "dependency",
                        "signature": line.strip(),
                        "line": line_num,
                        "span": (line_num, line_num),
                    })
                    
                    if self._sqlite_store and file_id:
                        symbol_id = self._sqlite_store.store_symbol(
                            file_id,
                            dep_name,
                            "dependency",
                            line_num,
                            line_num,
                            signature=line.strip()
                        )
                        self._indexer.add_symbol(
                            dep_name, 
                            str(path), 
                            line_num,
                            {"symbol_id": symbol_id, "file_id": file_id}
                        )
            
            # Parse plugins
            plugin_match = plugin_pattern.search(line)
            if plugin_match:
                plugin_name = plugin_match.group(1) or plugin_match.group(2)
                symbols.append({
                    "symbol": plugin_name,
                    "kind": "plugin",
                    "signature": line.strip(),
                    "line": line_num,
                    "span": (line_num, line_num),
                })
                
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        plugin_name,
                        "plugin",
                        line_num,
                        line_num,
                        signature=line.strip()
                    )
                    self._indexer.add_symbol(
                        plugin_name, 
                        str(path), 
                        line_num,
                        {"symbol_id": symbol_id, "file_id": file_id}
                    )
        
        return {"file": str(path), "symbols": symbols, "language": "gradle"}

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get definition location for a JVM symbol."""
        extensions = ["*.java", "*.kt", "*.kts"]
        
        for pattern in extensions:
            for path in Path(".").rglob(pattern):
                try:
                    content = path.read_text(encoding='utf-8')
                    
                    if path.suffix == ".java" or self._parser.is_java_file(content):
                        parsed_symbols = self._parser.parse_java_file(content)
                        language = "java"
                    else:
                        parsed_symbols = self._parser.parse_kotlin_file(content)
                        language = "kotlin"
                    
                    # Search through all symbol types
                    for symbol_type, symbol_list in parsed_symbols.items():
                        if symbol_type in ['package', 'imports']:
                            continue
                        
                        for symbol_data in symbol_list:
                            if symbol_data['name'] == symbol:
                                kind = symbol_data.get('kind', symbol_type.rstrip('s'))
                                return {
                                    "symbol": symbol,
                                    "kind": kind,
                                    "language": language,
                                    "signature": symbol_data['signature'],
                                    "doc": "",  # Doc extraction would need more sophisticated parsing
                                    "defined_in": str(path),
                                    "line": symbol_data['line'],
                                    "span": (symbol_data['line'], symbol_data['line'] + 1),
                                }
                except Exception:
                    continue
        return None

    def findReferences(self, symbol: str) -> List[Reference]:
        """Find references to a JVM symbol."""
        refs: List[Reference] = []
        seen: set[tuple[str, int]] = set()
        
        # Simple text-based reference finding
        symbol_pattern = re.compile(r'\b' + re.escape(symbol) + r'\b')
        extensions = ["*.java", "*.kt", "*.kts"]
        
        for pattern in extensions:
            for path in Path(".").rglob(pattern):
                try:
                    content = path.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        if symbol_pattern.search(line):
                            key = (str(path), line_num)
                            if key not in seen:
                                refs.append(Reference(file=str(path), line=line_num))
                                seen.add(key)
                except Exception:
                    continue
        
        return refs

    def search(self, query: str, opts: SearchOpts | None = None) -> List[SearchResult]:
        """Search for JVM symbols and code patterns."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        if opts and opts.get("semantic"):
            return []
        return self._indexer.search(query, limit=limit)
    
    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        stats = self._indexer.get_stats()
        return stats.get('files', 0)