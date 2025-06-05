"""YAML plugin for indexing YAML configuration files, Kubernetes manifests, and CI/CD configs."""

from typing import Dict, List, Optional, Set, Any
from pathlib import Path
import re
import yaml
from yaml.constructor import ConstructorError
from yaml.parser import ParserError
from yaml.scanner import ScannerError

from ..regex_plugin_base import RegexPluginBase, RegexPattern
from ..plugin_template import SymbolType, ParsedSymbol, PluginConfig


class Plugin(RegexPluginBase):
    """YAML language plugin with structure-aware parsing."""
    
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        return "yaml"
    
    def get_supported_extensions(self) -> List[str]:
        """Return list of file extensions this plugin supports."""
        return ['.yaml', '.yml']
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return regex patterns for different symbol types."""
        return {
            SymbolType.VARIABLE: r'^(\w+):\s*(.+)',
            SymbolType.NAMESPACE: r'^(\w+):(?:\s*$|\s*#)',
            SymbolType.IMPORT: r'^\s*\$ref:\s*["\']([^"\']+)["\']',
            SymbolType.ANNOTATION: r'^\s*#\s*(.*)',
            SymbolType.CONSTANT: r'^(\w+):\s*["\']([^"\']+)["\']',
            SymbolType.MODULE: r'^---\s*(?:#.*)?$'
        }
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        """Return list of regex patterns for symbol extraction."""
        return [
            # Top-level keys (namespaces/sections)
            RegexPattern(
                pattern=r'^([a-zA-Z_][a-zA-Z0-9_-]*):(?:\s*$|\s*#.*$)',
                symbol_type=SymbolType.NAMESPACE,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Key-value pairs
            RegexPattern(
                pattern=r'^(\s*)([a-zA-Z_][a-zA-Z0-9_-]*):(\s+(.+?)(?:\s*#.*)?$|\s*$)',
                symbol_type=SymbolType.VARIABLE,
                name_group=2,
                signature_group=0,
                flags=re.MULTILINE
            ),
            
            # Array items with names (common in Kubernetes)
            RegexPattern(
                pattern=r'^\s*-\s+name:\s*([a-zA-Z_][a-zA-Z0-9_-]*)',
                symbol_type=SymbolType.VARIABLE,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Kubernetes resource definitions
            RegexPattern(
                pattern=r'^kind:\s*([A-Z][a-zA-Z0-9]*)',
                symbol_type=SymbolType.TYPE,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Kubernetes metadata names
            RegexPattern(
                pattern=r'^\s*name:\s*([a-zA-Z0-9_.-]+)',
                symbol_type=SymbolType.CONSTANT,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Environment variables in YAML
            RegexPattern(
                pattern=r'^\s*(\w+):\s*\${([^}]+)}',
                symbol_type=SymbolType.VARIABLE,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # References and includes
            RegexPattern(
                pattern=r'^\s*\$ref:\s*["\']([^"\']+)["\']',
                symbol_type=SymbolType.IMPORT,
                name_group=1,
                flags=re.MULTILINE
            ),
            
            # Anchors and aliases
            RegexPattern(
                pattern=r'^(\s*)(\w+):\s*&(\w+)',
                symbol_type=SymbolType.CONSTANT,
                name_group=3,
                flags=re.MULTILINE
            ),
            
            # Alias references
            RegexPattern(
                pattern=r'^(\s*)(\w+):\s*\*(\w+)',
                symbol_type=SymbolType.VARIABLE,
                name_group=3,
                flags=re.MULTILINE
            ),
            
            # Comments (for documentation extraction)
            RegexPattern(
                pattern=r'^\s*#\s*(.*)',
                symbol_type=SymbolType.COMMENT,
                name_group=1,
                flags=re.MULTILINE
            )
        ]
    
    def get_multi_line_patterns(self) -> Dict[SymbolType, RegexPattern]:
        """Return patterns for multi-line constructs."""
        return {
            SymbolType.COMMENT: RegexPattern(
                pattern=r'^#\s*={3,}.*?={3,}\s*$.*?^#\s*={3,}.*?={3,}\s*$',
                flags=re.MULTILINE | re.DOTALL,
                symbol_type=SymbolType.COMMENT
            )
        }
    
    def get_context_patterns(self) -> Dict[str, RegexPattern]:
        """Return patterns for extracting context information."""
        return {
            "document_separator": RegexPattern(
                pattern=r'^---\s*(?:#.*)?$',
                flags=re.MULTILINE
            ),
            "kubernetes_resource": RegexPattern(
                pattern=r'^(apiVersion|kind|metadata):\s*(.+)$',
                flags=re.MULTILINE
            ),
            "docker_compose_service": RegexPattern(
                pattern=r'^(\s+)(\w+):\s*$(?:\n\1\s+)',
                flags=re.MULTILINE
            ),
            "ci_cd_job": RegexPattern(
                pattern=r'^([a-zA-Z_][a-zA-Z0-9_-]*):(?:\s*$|\s*#.*$)(?:\n\s+)',
                flags=re.MULTILINE
            )
        }
    
    def _extract_symbols_regex(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Enhanced symbol extraction for YAML files."""
        symbols = super()._extract_symbols_regex(content, file_path)
        
        # Add YAML-specific enhancements
        symbols.extend(self._extract_yaml_structure(content, file_path))
        symbols.extend(self._extract_kubernetes_resources(content))
        symbols.extend(self._extract_docker_compose_services(content))
        symbols.extend(self._extract_ci_cd_config(content))
        
        return symbols
    
    def _extract_yaml_structure(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract YAML document structure using actual YAML parsing."""
        symbols = []
        
        try:
            # Parse YAML documents
            documents = list(yaml.safe_load_all(content))
            
            for doc_idx, document in enumerate(documents):
                if document is None:
                    continue
                
                doc_symbols = self._extract_from_yaml_object(
                    document, 
                    f"document_{doc_idx}", 
                    content,
                    base_line=self._find_document_start_line(content, doc_idx)
                )
                symbols.extend(doc_symbols)
                
        except (ParserError, ScannerError, ConstructorError) as e:
            self.logger.warning(f"YAML parsing error in {file_path}: {e}")
            # Fall back to regex-only parsing
        
        return symbols
    
    def _extract_from_yaml_object(self, obj: Any, path: str, content: str, base_line: int = 0) -> List[ParsedSymbol]:
        """Recursively extract symbols from YAML object structure."""
        symbols = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(key, str):
                    # Find the line number for this key
                    line_no = self._find_key_line_number(content, key, base_line)
                    
                    # Determine symbol type based on value and context
                    symbol_type = self._determine_symbol_type(key, value, path)
                    
                    symbol = ParsedSymbol(
                        name=key,
                        symbol_type=symbol_type,
                        line=line_no,
                        signature=f"{key}: {self._format_value_for_signature(value)}",
                        scope=path if path != "document_0" else None,
                        metadata={
                            "yaml_path": f"{path}.{key}",
                            "value_type": type(value).__name__,
                            "is_container": isinstance(value, (dict, list))
                        }
                    )
                    symbols.append(symbol)
                    
                    # Recursively process nested structures
                    if isinstance(value, (dict, list)):
                        nested_symbols = self._extract_from_yaml_object(
                            value, 
                            f"{path}.{key}", 
                            content, 
                            line_no
                        )
                        symbols.extend(nested_symbols)
        
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                if isinstance(item, dict) and 'name' in item:
                    # Common pattern: list of objects with 'name' field
                    name = item['name']
                    line_no = self._find_key_line_number(content, str(name), base_line)
                    
                    symbol = ParsedSymbol(
                        name=str(name),
                        symbol_type=SymbolType.VARIABLE,
                        line=line_no,
                        signature=f"- name: {name}",
                        scope=path,
                        metadata={
                            "yaml_path": f"{path}[{idx}].name",
                            "list_item": True
                        }
                    )
                    symbols.append(symbol)
                
                # Recursively process list items
                if isinstance(item, (dict, list)):
                    nested_symbols = self._extract_from_yaml_object(
                        item, 
                        f"{path}[{idx}]", 
                        content, 
                        base_line
                    )
                    symbols.extend(nested_symbols)
        
        return symbols
    
    def _determine_symbol_type(self, key: str, value: Any, path: str) -> SymbolType:
        """Determine the appropriate symbol type based on key, value, and context."""
        key_lower = key.lower()
        
        # Kubernetes-specific types
        if key_lower == "kind":
            return SymbolType.TYPE
        elif key_lower in ["name", "namespace"]:
            return SymbolType.CONSTANT
        elif key_lower in ["apiversion", "version"]:
            return SymbolType.MODULE
        
        # Docker Compose specific
        elif "services" in path and isinstance(value, dict):
            return SymbolType.NAMESPACE
        
        # CI/CD specific
        elif key_lower in ["job", "stage", "script", "before_script", "after_script"]:
            return SymbolType.FUNCTION
        
        # Environment variables
        elif key_lower in ["env", "environment", "variables"]:
            return SymbolType.NAMESPACE
        elif "env" in path.lower() or "environment" in path.lower():
            return SymbolType.VARIABLE
        
        # General categorization
        elif isinstance(value, dict):
            return SymbolType.NAMESPACE
        elif isinstance(value, list):
            return SymbolType.VARIABLE
        elif isinstance(value, str) and (value.startswith("$") or "${" in value):
            return SymbolType.VARIABLE
        elif isinstance(value, (bool, int, float)):
            return SymbolType.CONSTANT
        else:
            return SymbolType.VARIABLE
    
    def _format_value_for_signature(self, value: Any) -> str:
        """Format YAML value for use in symbol signature."""
        if isinstance(value, dict):
            return f"{{...}} ({len(value)} keys)"
        elif isinstance(value, list):
            return f"[...] ({len(value)} items)"
        elif isinstance(value, str):
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
        else:
            return str(value)
    
    def _find_document_start_line(self, content: str, doc_idx: int) -> int:
        """Find the line number where a YAML document starts."""
        lines = content.splitlines()
        doc_count = 0
        
        for line_no, line in enumerate(lines, 1):
            if line.strip() == "---":
                if doc_count == doc_idx:
                    return line_no
                doc_count += 1
        
        return 1  # First document starts at line 1 if no separators
    
    def _find_key_line_number(self, content: str, key: str, start_line: int = 0) -> int:
        """Find the line number where a specific key appears."""
        lines = content.splitlines()
        key_pattern = re.compile(rf'^\s*{re.escape(key)}\s*:')
        
        for line_no, line in enumerate(lines[start_line:], start_line + 1):
            if key_pattern.match(line):
                return line_no
        
        return start_line + 1  # Fallback
    
    def _extract_kubernetes_resources(self, content: str) -> List[ParsedSymbol]:
        """Extract Kubernetes-specific resources and configurations."""
        symbols = []
        lines = content.splitlines()
        
        current_resource = None
        current_namespace = None
        
        for line_no, line in enumerate(lines, 1):
            # Track current Kubernetes resource
            kind_match = re.match(r'^\s*kind:\s*([A-Z][a-zA-Z0-9]*)', line)
            if kind_match:
                current_resource = kind_match.group(1)
                symbols.append(ParsedSymbol(
                    name=current_resource,
                    symbol_type=SymbolType.TYPE,
                    line=line_no,
                    signature=line.strip(),
                    metadata={"kubernetes_resource": True, "resource_type": current_resource}
                ))
            
            # Track resource metadata
            if current_resource:
                name_match = re.match(r'^\s*name:\s*([a-zA-Z0-9_.-]+)', line)
                if name_match:
                    resource_name = name_match.group(1)
                    symbols.append(ParsedSymbol(
                        name=resource_name,
                        symbol_type=SymbolType.CONSTANT,
                        line=line_no,
                        signature=line.strip(),
                        scope=current_resource,
                        metadata={
                            "kubernetes_resource": True,
                            "resource_name": resource_name,
                            "resource_type": current_resource
                        }
                    ))
                
                namespace_match = re.match(r'^\s*namespace:\s*([a-zA-Z0-9_.-]+)', line)
                if namespace_match:
                    current_namespace = namespace_match.group(1)
            
            # Extract container names and images
            container_match = re.match(r'^\s*-\s*name:\s*([a-zA-Z0-9_.-]+)', line)
            if container_match and "containers" in content[:content.find(line)]:
                container_name = container_match.group(1)
                symbols.append(ParsedSymbol(
                    name=container_name,
                    symbol_type=SymbolType.VARIABLE,
                    line=line_no,
                    signature=line.strip(),
                    scope=f"{current_resource}.containers",
                    metadata={
                        "kubernetes_container": True,
                        "container_name": container_name,
                        "namespace": current_namespace
                    }
                ))
        
        return symbols
    
    def _extract_docker_compose_services(self, content: str) -> List[ParsedSymbol]:
        """Extract Docker Compose service definitions."""
        symbols = []
        lines = content.splitlines()
        
        in_services = False
        current_service = None
        
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check if we're in the services section
            if re.match(r'^services:\s*$', line):
                in_services = True
                continue
            elif re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*:\s*$', line) and not line.startswith(' '):
                in_services = False
            
            # Extract service definitions
            if in_services:
                service_match = re.match(r'^  ([a-zA-Z_][a-zA-Z0-9_-]*):(?:\s*$|\s*#.*$)', line)
                if service_match:
                    current_service = service_match.group(1)
                    symbols.append(ParsedSymbol(
                        name=current_service,
                        symbol_type=SymbolType.NAMESPACE,
                        line=line_no,
                        signature=line.strip(),
                        scope="services",
                        metadata={
                            "docker_compose_service": True,
                            "service_name": current_service
                        }
                    ))
                
                # Extract service properties
                elif current_service and line.startswith('    '):
                    prop_match = re.match(r'^    ([a-zA-Z_][a-zA-Z0-9_-]*):(.*)$', line)
                    if prop_match:
                        prop_name = prop_match.group(1)
                        prop_value = prop_match.group(2).strip()
                        
                        symbols.append(ParsedSymbol(
                            name=prop_name,
                            symbol_type=SymbolType.VARIABLE,
                            line=line_no,
                            signature=line.strip(),
                            scope=f"services.{current_service}",
                            metadata={
                                "docker_compose_property": True,
                                "service_name": current_service,
                                "property_name": prop_name,
                                "property_value": prop_value[:100] if prop_value else ""
                            }
                        ))
        
        return symbols
    
    def _extract_ci_cd_config(self, content: str) -> List[ParsedSymbol]:
        """Extract CI/CD configuration (GitHub Actions, GitLab CI, etc.)."""
        symbols = []
        lines = content.splitlines()
        
        # Detect CI/CD type
        ci_type = self._detect_ci_cd_type(content)
        
        if ci_type == "github_actions":
            symbols.extend(self._extract_github_actions(lines))
        elif ci_type == "gitlab_ci":
            symbols.extend(self._extract_gitlab_ci(lines))
        elif ci_type == "azure_pipelines":
            symbols.extend(self._extract_azure_pipelines(lines))
        
        return symbols
    
    def _detect_ci_cd_type(self, content: str) -> Optional[str]:
        """Detect the type of CI/CD configuration."""
        if "on:" in content and ("push:" in content or "pull_request:" in content):
            return "github_actions"
        elif "stages:" in content and "script:" in content:
            return "gitlab_ci"
        elif "trigger:" in content and "pool:" in content:
            return "azure_pipelines"
        return None
    
    def _extract_github_actions(self, lines: List[str]) -> List[ParsedSymbol]:
        """Extract GitHub Actions workflow structure."""
        symbols = []
        current_job = None
        
        for line_no, line in enumerate(lines, 1):
            # Extract job definitions
            job_match = re.match(r'^  ([a-zA-Z_][a-zA-Z0-9_-]*):(?:\s*$|\s*#.*$)', line)
            if job_match and any("jobs:" in lines[i] for i in range(max(0, line_no-10), line_no)):
                current_job = job_match.group(1)
                symbols.append(ParsedSymbol(
                    name=current_job,
                    symbol_type=SymbolType.FUNCTION,
                    line=line_no,
                    signature=line.strip(),
                    scope="jobs",
                    metadata={
                        "github_actions_job": True,
                        "job_name": current_job
                    }
                ))
            
            # Extract step names
            step_match = re.match(r'^\s*-\s+name:\s*(.+)', line)
            if step_match and current_job:
                step_name = step_match.group(1).strip('\'"')
                symbols.append(ParsedSymbol(
                    name=step_name,
                    symbol_type=SymbolType.FUNCTION,
                    line=line_no,
                    signature=line.strip(),
                    scope=f"jobs.{current_job}.steps",
                    metadata={
                        "github_actions_step": True,
                        "step_name": step_name,
                        "job_name": current_job
                    }
                ))
        
        return symbols
    
    def _extract_gitlab_ci(self, lines: List[str]) -> List[ParsedSymbol]:
        """Extract GitLab CI pipeline structure."""
        symbols = []
        
        for line_no, line in enumerate(lines, 1):
            # Extract job definitions (top-level keys that aren't keywords)
            job_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_:-]*):(?:\s*$|\s*#.*$)', line)
            if job_match:
                job_name = job_match.group(1)
                # Skip GitLab CI keywords
                if job_name not in ['stages', 'variables', 'before_script', 'after_script', 'image', 'services']:
                    symbols.append(ParsedSymbol(
                        name=job_name,
                        symbol_type=SymbolType.FUNCTION,
                        line=line_no,
                        signature=line.strip(),
                        metadata={
                            "gitlab_ci_job": True,
                            "job_name": job_name
                        }
                    ))
        
        return symbols
    
    def _extract_azure_pipelines(self, lines: List[str]) -> List[ParsedSymbol]:
        """Extract Azure Pipelines structure."""
        symbols = []
        
        for line_no, line in enumerate(lines, 1):
            # Extract job and task definitions
            job_match = re.match(r'^- job:\s*([a-zA-Z_][a-zA-Z0-9_-]*)', line)
            if job_match:
                job_name = job_match.group(1)
                symbols.append(ParsedSymbol(
                    name=job_name,
                    symbol_type=SymbolType.FUNCTION,
                    line=line_no,
                    signature=line.strip(),
                    metadata={
                        "azure_pipelines_job": True,
                        "job_name": job_name
                    }
                ))
        
        return symbols
    
    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the given file."""
        path = Path(path) if isinstance(path, str) else path
        extension = path.suffix.lower()
        
        # Support YAML extensions
        if extension in self.get_supported_extensions():
            return True
        
        # Support common YAML config files without extensions
        filename = path.name.lower()
        yaml_files = [
            'docker-compose', 'compose', '.travis', '.gitlab-ci',
            'azure-pipelines', 'buildkite', 'circleci', 'appveyor'
        ]
        
        if any(yaml_file in filename for yaml_file in yaml_files):
            return True
        
        return False
    
    def get_mcp_tools(self) -> List[Dict]:
        """Return MCP tools provided by this plugin."""
        return [
            {
                "name": "analyze_yaml_structure",
                "description": "Analyze YAML file structure and extract key information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "yaml_path": {
                            "type": "string",
                            "description": "Path to the YAML file"
                        }
                    },
                    "required": ["yaml_path"]
                },
                "handler": self._analyze_yaml_structure
            },
            {
                "name": "find_kubernetes_resources",
                "description": "Find and analyze Kubernetes resources in YAML files",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "directory_path": {
                            "type": "string",
                            "description": "Path to search for Kubernetes YAML files"
                        }
                    },
                    "required": ["directory_path"]
                },
                "handler": self._find_kubernetes_resources
            },
            {
                "name": "extract_docker_compose_services",
                "description": "Extract Docker Compose service definitions",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "compose_file": {
                            "type": "string",
                            "description": "Path to docker-compose.yml file"
                        }
                    },
                    "required": ["compose_file"]
                },
                "handler": self._extract_compose_services
            }
        ]
    
    async def _analyze_yaml_structure(self, params: dict) -> dict:
        """Analyze YAML file structure."""
        yaml_path = Path(params["yaml_path"])
        
        if not yaml_path.exists():
            return {"error": f"YAML file {yaml_path} does not exist"}
        
        try:
            content = yaml_path.read_text(encoding='utf-8')
            symbols = self._extract_symbols(content, str(yaml_path))
            
            # Parse the YAML to get structure info
            documents = list(yaml.safe_load_all(content))
            
            analysis = {
                "file_path": str(yaml_path),
                "document_count": len([d for d in documents if d is not None]),
                "top_level_keys": [],
                "namespaces": [],
                "variables": [],
                "constants": [],
                "structure_type": "unknown"
            }
            
            # Detect structure type
            if any("kind:" in content and "apiVersion:" in content for d in documents if d):
                analysis["structure_type"] = "kubernetes"
            elif "services:" in content:
                analysis["structure_type"] = "docker_compose"
            elif "jobs:" in content and ("on:" in content or "workflow_dispatch:" in content):
                analysis["structure_type"] = "github_actions"
            elif "stages:" in content and "script:" in content:
                analysis["structure_type"] = "gitlab_ci"
            
            # Extract top-level structure
            if documents and documents[0]:
                analysis["top_level_keys"] = list(documents[0].keys()) if isinstance(documents[0], dict) else []
            
            # Categorize symbols
            for symbol in symbols:
                symbol_info = {
                    "name": symbol.name,
                    "line": symbol.line,
                    "signature": symbol.signature,
                    "scope": symbol.scope,
                    "metadata": symbol.metadata
                }
                
                if symbol.symbol_type == SymbolType.NAMESPACE:
                    analysis["namespaces"].append(symbol_info)
                elif symbol.symbol_type == SymbolType.VARIABLE:
                    analysis["variables"].append(symbol_info)
                elif symbol.symbol_type == SymbolType.CONSTANT:
                    analysis["constants"].append(symbol_info)
            
            return analysis
            
        except Exception as e:
            return {"error": f"Failed to analyze YAML: {str(e)}"}
    
    async def _find_kubernetes_resources(self, params: dict) -> dict:
        """Find Kubernetes resources in YAML files."""
        directory_path = Path(params["directory_path"])
        resources = []
        
        if not directory_path.exists():
            return {"error": f"Directory {directory_path} does not exist"}
        
        # Search for YAML files
        for yaml_file in directory_path.rglob("*.yaml"):
            if yaml_file.is_file():
                try:
                    content = yaml_file.read_text(encoding='utf-8')
                    if "kind:" in content and "apiVersion:" in content:
                        symbols = self._extract_symbols(content, str(yaml_file))
                        
                        for symbol in symbols:
                            if symbol.metadata.get("kubernetes_resource"):
                                resources.append({
                                    "file": str(yaml_file),
                                    "resource_type": symbol.metadata.get("resource_type"),
                                    "resource_name": symbol.metadata.get("resource_name"),
                                    "line": symbol.line,
                                    "namespace": symbol.metadata.get("namespace")
                                })
                                
                except Exception as e:
                    self.logger.warning(f"Failed to analyze {yaml_file}: {e}")
        
        return {"kubernetes_resources": resources}
    
    async def _extract_compose_services(self, params: dict) -> dict:
        """Extract Docker Compose services."""
        compose_file = Path(params["compose_file"])
        
        if not compose_file.exists():
            return {"error": f"Compose file {compose_file} does not exist"}
        
        try:
            content = compose_file.read_text(encoding='utf-8')
            symbols = self._extract_symbols(content, str(compose_file))
            
            services = []
            for symbol in symbols:
                if symbol.metadata.get("docker_compose_service"):
                    service_info = {
                        "name": symbol.name,
                        "line": symbol.line,
                        "properties": []
                    }
                    
                    # Find properties for this service
                    for prop_symbol in symbols:
                        if (prop_symbol.metadata.get("docker_compose_property") and
                            prop_symbol.metadata.get("service_name") == symbol.name):
                            service_info["properties"].append({
                                "name": prop_symbol.metadata.get("property_name"),
                                "value": prop_symbol.metadata.get("property_value"),
                                "line": prop_symbol.line
                            })
                    
                    services.append(service_info)
            
            return {"services": services}
            
        except Exception as e:
            return {"error": f"Failed to extract services: {str(e)}"}