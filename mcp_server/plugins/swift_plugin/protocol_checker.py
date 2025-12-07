"""Swift protocol conformance checking and analysis."""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ConformanceType(Enum):
    """Types of protocol conformance."""

    DIRECT = "direct"  # class Foo: Protocol
    EXTENSION = "extension"  # extension Foo: Protocol
    CONDITIONAL = "conditional"  # extension Foo: Protocol where T: SomeType
    SYNTHESIZED = "synthesized"  # @Codable, @Hashable, etc.


@dataclass
class ProtocolConformance:
    """Represents a protocol conformance."""

    type_name: str
    protocol_name: str
    conformance_type: ConformanceType
    file_path: str
    line_number: int
    conditions: List[str] = None  # For conditional conformances
    requirements: List[str] = None  # Protocol requirements
    implementations: List[str] = None  # Implemented methods/properties

    def __post_init__(self):
        if self.conditions is None:
            self.conditions = []
        if self.requirements is None:
            self.requirements = []
        if self.implementations is None:
            self.implementations = []


@dataclass
class ProtocolDefinition:
    """Represents a protocol definition."""

    name: str
    file_path: str
    line_number: int
    requirements: List[str]
    inherited_protocols: List[str]
    associated_types: List[str]
    default_implementations: List[str]
    availability: Optional[str] = None

    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []
        if self.inherited_protocols is None:
            self.inherited_protocols = []
        if self.associated_types is None:
            self.associated_types = []
        if self.default_implementations is None:
            self.default_implementations = []


@dataclass
class PropertyWrapper:
    """Represents a property wrapper definition or usage."""

    name: str
    wrapped_type: Optional[str]
    projected_type: Optional[str]
    file_path: str
    line_number: int
    usage_sites: List[Tuple[str, int]] = None  # (property_name, line_number)

    def __post_init__(self):
        if self.usage_sites is None:
            self.usage_sites = []


@dataclass
class ResultBuilder:
    """Represents a result builder definition or usage."""

    name: str
    build_methods: List[str]
    file_path: str
    line_number: int
    usage_sites: List[Tuple[str, int]] = None  # (function_name, line_number)

    def __post_init__(self):
        if self.usage_sites is None:
            self.usage_sites = []


class SwiftProtocolChecker:
    """Analyzes Swift protocol conformances and modern features."""

    def __init__(self):
        self.protocols: Dict[str, ProtocolDefinition] = {}
        self.conformances: Dict[str, List[ProtocolConformance]] = {}
        self.property_wrappers: Dict[str, PropertyWrapper] = {}
        self.result_builders: Dict[str, ResultBuilder] = {}

        # Known system protocols
        self.system_protocols = self._init_system_protocols()

    def find_conformances(self, content: str, file_path: str = "") -> Dict[str, List[str]]:
        """Find all protocol conformances in Swift code."""
        conformances = {}
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("//") or line.startswith("/*"):
                continue

            # Find direct conformances in type declarations
            direct_conformances = self._find_direct_conformances(line, file_path, line_num)
            for conformance in direct_conformances:
                if conformance.type_name not in conformances:
                    conformances[conformance.type_name] = []
                conformances[conformance.type_name].append(conformance.protocol_name)

            # Find extension conformances
            extension_conformances = self._find_extension_conformances(line, file_path, line_num)
            for conformance in extension_conformances:
                if conformance.type_name not in conformances:
                    conformances[conformance.type_name] = []
                conformances[conformance.type_name].append(conformance.protocol_name)

        return conformances

    def analyze_protocols(self, content: str, file_path: str = "") -> List[ProtocolDefinition]:
        """Analyze protocol definitions in Swift code."""
        protocols = []
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for protocol declarations
            protocol_match = re.match(r"protocol\s+(\w+)(?:\s*:\s*([^{]+))?\s*\{?", line)
            if protocol_match:
                protocol_name = protocol_match.group(1)
                inherited_str = protocol_match.group(2) or ""

                inherited_protocols = []
                if inherited_str:
                    inherited_protocols = [p.strip() for p in inherited_str.split(",")]

                # Parse protocol body
                requirements, associated_types, defaults = self._parse_protocol_body(
                    lines, i + 1, file_path
                )

                protocol_def = ProtocolDefinition(
                    name=protocol_name,
                    file_path=file_path,
                    line_number=i + 1,
                    requirements=requirements,
                    inherited_protocols=inherited_protocols,
                    associated_types=associated_types,
                    default_implementations=defaults,
                )

                protocols.append(protocol_def)
                self.protocols[protocol_name] = protocol_def

            i += 1

        return protocols

    def analyze_property_wrappers(self, content: str, file_path: str = "") -> List[PropertyWrapper]:
        """Analyze property wrapper definitions and usage."""
        property_wrappers = []
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check for @propertyWrapper attribute
            if "@propertyWrapper" in line:
                # Look ahead for the struct/class definition
                j = i
                while j < len(lines):
                    next_line = lines[j].strip()
                    struct_match = re.search(r"(?:struct|class)\s+(\w+)", next_line)
                    if struct_match:
                        wrapper_name = struct_match.group(1)
                        wrapper_def = PropertyWrapper(
                            name=wrapper_name,
                            wrapped_type=None,
                            projected_type=None,
                            file_path=file_path,
                            line_number=i + 1,
                        )
                        property_wrappers.append(wrapper_def)
                        self.property_wrappers[wrapper_def.name] = wrapper_def
                        break
                    j += 1
                    if j > i + 3:  # Don't look too far ahead
                        break

            # Find property wrapper usage
            wrapper_usage = self._find_property_wrapper_usage(line, file_path, i + 1)
            for usage in wrapper_usage:
                if usage.name in self.property_wrappers:
                    self.property_wrappers[usage.name].usage_sites.append(
                        (usage.wrapped_type or "unknown", i + 1)
                    )

            i += 1

        return property_wrappers

    def analyze_result_builders(self, content: str, file_path: str = "") -> List[ResultBuilder]:
        """Analyze result builder definitions and usage."""
        result_builders = []
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check for @resultBuilder attribute
            if "@resultBuilder" in line:
                # Look ahead for the struct/class definition
                j = i
                while j < len(lines):
                    next_line = lines[j].strip()
                    struct_match = re.search(r"(?:struct|class|enum)\s+(\w+)", next_line)
                    if struct_match:
                        builder_name = struct_match.group(1)
                        builder_def = ResultBuilder(
                            name=builder_name,
                            build_methods=[],  # Would need more analysis
                            file_path=file_path,
                            line_number=i + 1,
                        )
                        result_builders.append(builder_def)
                        self.result_builders[builder_def.name] = builder_def
                        break
                    j += 1
                    if j > i + 3:  # Don't look too far ahead
                        break

            # Find result builder usage
            builder_usage = self._find_result_builder_usage(line, file_path, i + 1)
            for usage in builder_usage:
                if usage in self.result_builders:
                    # Extract function name if possible
                    func_match = re.search(r"func\s+(\w+)", line)
                    func_name = func_match.group(1) if func_match else "unknown"
                    self.result_builders[usage].usage_sites.append((func_name, i + 1))

            i += 1

        return result_builders

    def validate_conformance(
        self, type_name: str, protocol_name: str, content: str
    ) -> Dict[str, Any]:
        """Validate that a type properly conforms to a protocol."""
        validation_result = {
            "valid": True,
            "missing_requirements": [],
            "extra_implementations": [],
            "warnings": [],
        }

        # Get protocol requirements
        if protocol_name in self.protocols:
            protocol_def = self.protocols[protocol_name]
            required_methods = protocol_def.requirements
        elif protocol_name in self.system_protocols:
            required_methods = self.system_protocols[protocol_name]
        else:
            validation_result["warnings"].append(f"Unknown protocol: {protocol_name}")
            return validation_result

        # Find implemented methods in the type
        implemented_methods = self._find_implemented_methods(type_name, content)

        # Check for missing requirements
        for requirement in required_methods:
            if not self._is_requirement_satisfied(requirement, implemented_methods):
                validation_result["missing_requirements"].append(requirement)
                validation_result["valid"] = False

        return validation_result

    def find_protocol_extensions(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Find protocol extensions and their default implementations."""
        extensions = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Look for protocol extensions
            extension_match = re.match(r"extension\s+(\w+)(?:\s+where\s+([^{]+))?\s*\{?", line)
            if extension_match:
                protocol_name = extension_match.group(1)
                where_clause = extension_match.group(2)

                # Check if it's extending a known protocol
                if protocol_name in self.protocols or protocol_name in self.system_protocols:

                    # Parse extension body for default implementations
                    implementations = self._parse_extension_body(lines, line_num, file_path)

                    extensions.append(
                        {
                            "protocol_name": protocol_name,
                            "where_clause": where_clause,
                            "implementations": implementations,
                            "file_path": file_path,
                            "line_number": line_num,
                        }
                    )

        return extensions

    def _find_direct_conformances(
        self, line: str, file_path: str, line_num: int
    ) -> List[ProtocolConformance]:
        """Find direct protocol conformances in type declarations."""
        conformances = []

        # Patterns for type declarations with conformances
        patterns = [
            r"(class|struct|enum|actor)\s+(\w+)(?:<[^>]+>)?\s*:\s*([^{]+)",
        ]

        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                _ = match.group(1)
                type_name = match.group(2)
                conformance_list = match.group(3).strip()

                # Parse conformances (could be superclass + protocols)
                conformances_str = [c.strip() for c in conformance_list.split(",")]

                for conf_str in conformances_str:
                    # Skip if it's likely a superclass (starts with uppercase, no known protocol)
                    if conf_str and (
                        conf_str in self.system_protocols
                        or conf_str in self.protocols
                        or self._looks_like_protocol(conf_str)
                    ):

                        conformance = ProtocolConformance(
                            type_name=type_name,
                            protocol_name=conf_str,
                            conformance_type=ConformanceType.DIRECT,
                            file_path=file_path,
                            line_number=line_num,
                        )
                        conformances.append(conformance)

        return conformances

    def _find_extension_conformances(
        self, line: str, file_path: str, line_num: int
    ) -> List[ProtocolConformance]:
        """Find protocol conformances in extensions."""
        conformances = []

        # Extension with conformance
        extension_match = re.match(r"extension\s+(\w+)\s*:\s*([^{]+)", line)
        if extension_match:
            type_name = extension_match.group(1)
            conformance_list = extension_match.group(2).strip()

            # Parse where clause if present
            where_conditions = []
            if " where " in conformance_list:
                parts = conformance_list.split(" where ")
                conformance_list = parts[0]
                where_conditions = [parts[1]]

            conformances_str = [c.strip() for c in conformance_list.split(",")]

            for conf_str in conformances_str:
                if conf_str:
                    conformance_type = (
                        ConformanceType.CONDITIONAL
                        if where_conditions
                        else ConformanceType.EXTENSION
                    )

                    conformance = ProtocolConformance(
                        type_name=type_name,
                        protocol_name=conf_str,
                        conformance_type=conformance_type,
                        file_path=file_path,
                        line_number=line_num,
                        conditions=where_conditions,
                    )
                    conformances.append(conformance)

        return conformances

    def _find_property_wrapper_definition(
        self, line: str, file_path: str, line_num: int
    ) -> Optional[PropertyWrapper]:
        """Find property wrapper definitions."""
        # Look for @propertyWrapper attribute followed by struct/class
        wrapper_match = re.search(
            r"@propertyWrapper\s*(?:\n\s*)?(?:struct|class)\s+(\w+)", line, re.MULTILINE
        )
        if wrapper_match:
            wrapper_name = wrapper_match.group(1)

            return PropertyWrapper(
                name=wrapper_name,
                wrapped_type=None,  # Would need more analysis to determine
                projected_type=None,
                file_path=file_path,
                line_number=line_num,
            )

        # Also check if the line contains @propertyWrapper and the next content might be on the same line
        if "@propertyWrapper" in line:
            # Look for struct/class on the same line after the attribute
            struct_match = re.search(r"@propertyWrapper.*?(?:struct|class)\s+(\w+)", line)
            if struct_match:
                wrapper_name = struct_match.group(1)

                return PropertyWrapper(
                    name=wrapper_name,
                    wrapped_type=None,
                    projected_type=None,
                    file_path=file_path,
                    line_number=line_num,
                )

        return None

    def _find_property_wrapper_usage(
        self, line: str, file_path: str, line_num: int
    ) -> List[PropertyWrapper]:
        """Find property wrapper usage."""
        wrappers = []

        # Look for @WrapperName property declarations
        wrapper_usage_match = re.search(r"@(\w+)(?:\([^)]*\))?\s+(?:var|let)\s+(\w+)", line)
        if wrapper_usage_match:
            wrapper_name = wrapper_usage_match.group(1)
            property_name = wrapper_usage_match.group(2)

            # Check if it's a known property wrapper or follows naming convention
            if wrapper_name in self.property_wrappers or self._looks_like_property_wrapper(
                wrapper_name
            ):

                wrapper = PropertyWrapper(
                    name=wrapper_name,
                    wrapped_type=property_name,
                    projected_type=None,
                    file_path=file_path,
                    line_number=line_num,
                )
                wrappers.append(wrapper)

        return wrappers

    def _find_result_builder_definition(
        self, line: str, file_path: str, line_num: int
    ) -> Optional[ResultBuilder]:
        """Find result builder definitions."""
        # Look for @resultBuilder attribute
        if "@resultBuilder" in line:
            builder_match = re.search(r"@resultBuilder\s+(?:struct|class|enum)\s+(\w+)", line)
            if builder_match:
                builder_name = builder_match.group(1)

                return ResultBuilder(
                    name=builder_name,
                    build_methods=[],  # Would need more analysis
                    file_path=file_path,
                    line_number=line_num,
                )

        return None

    def _find_result_builder_usage(self, line: str, file_path: str, line_num: int) -> List[str]:
        """Find result builder usage in function definitions."""
        builders = []

        # Look for @BuilderName func declarations
        builder_usage_match = re.search(r"@(\w+)\s+func\s+\w+", line)
        if builder_usage_match:
            builder_name = builder_usage_match.group(1)

            # Check if it's a known result builder
            if builder_name in self.result_builders or self._looks_like_result_builder(
                builder_name
            ):
                builders.append(builder_name)

        return builders

    def _parse_protocol_body(
        self, lines: List[str], start_line: int, file_path: str
    ) -> Tuple[List[str], List[str], List[str]]:
        """Parse protocol body for requirements, associated types, and default implementations."""
        requirements = []
        associated_types = []
        default_implementations = []

        brace_count = 0
        i = start_line

        while i < len(lines):
            line = lines[i].strip()

            # Track braces
            brace_count += line.count("{") - line.count("}")

            if brace_count < 0:
                break  # End of protocol

            # Skip comments and empty lines
            if not line or line.startswith("//"):
                i += 1
                continue

            # Find requirements (methods, properties)
            if self._is_protocol_requirement(line):
                requirements.append(line)

            # Find associated types
            associated_type_match = re.match(r"associatedtype\s+(\w+)", line)
            if associated_type_match:
                associated_types.append(associated_type_match.group(1))

            # Find default implementations (methods with bodies)
            if "{" in line and ("func " in line or "var " in line):
                default_implementations.append(line)

            i += 1

        return requirements, associated_types, default_implementations

    def _parse_extension_body(self, lines: List[str], start_line: int, file_path: str) -> List[str]:
        """Parse extension body for implementations."""
        implementations = []

        brace_count = 0
        i = start_line

        while i < len(lines):
            line = lines[i].strip()

            # Track braces
            brace_count += line.count("{") - line.count("}")

            if brace_count < 0:
                break  # End of extension

            # Skip comments and empty lines
            if not line or line.startswith("//"):
                i += 1
                continue

            # Find implementations
            if "func " in line or "var " in line or "subscript" in line:
                implementations.append(line)

            i += 1

        return implementations

    def _find_implemented_methods(self, type_name: str, content: str) -> List[str]:
        """Find methods implemented in a type."""
        implementations = []
        lines = content.split("\n")

        in_type = False
        brace_count = 0

        for line in lines:
            line_stripped = line.strip()

            # Check if we're entering the type definition
            if re.match(
                rf"(?:class|struct|enum|actor)\s+{re.escape(type_name)}\b",
                line_stripped,
            ):
                in_type = True
                brace_count = 0
                continue

            if in_type:
                brace_count += line_stripped.count("{") - line_stripped.count("}")

                if brace_count < 0:
                    break  # End of type

                # Find method/property implementations
                if (
                    "func " in line_stripped
                    or "var " in line_stripped
                    or "subscript" in line_stripped
                ):
                    implementations.append(line_stripped)

        return implementations

    def _is_protocol_requirement(self, line: str) -> bool:
        """Check if a line is a protocol requirement."""
        # Requirements don't have implementation bodies
        return (
            ("func " in line or "var " in line or "subscript" in line)
            and "{" not in line
            and not line.endswith("}")
        )

    def _is_requirement_satisfied(self, requirement: str, implementations: List[str]) -> bool:
        """Check if a protocol requirement is satisfied by implementations."""
        # Extract method/property signature from requirement
        req_signature = self._extract_signature(requirement)

        for impl in implementations:
            impl_signature = self._extract_signature(impl)
            if self._signatures_match(req_signature, impl_signature):
                return True

        return False

    def _extract_signature(self, line: str) -> str:
        """Extract method/property signature from a line."""
        # Simple signature extraction - could be improved
        if "func " in line:
            match = re.search(r"func\s+(\w+)\s*\([^)]*\)", line)
            return match.group(0) if match else line
        elif "var " in line:
            match = re.search(r"var\s+(\w+)\s*:", line)
            return match.group(0) if match else line

        return line

    def _signatures_match(self, req_sig: str, impl_sig: str) -> bool:
        """Check if requirement and implementation signatures match."""
        # Simplified matching - could be improved
        return req_sig.replace(" ", "") in impl_sig.replace(" ", "")

    def _looks_like_protocol(self, name: str) -> bool:
        """Check if a name looks like a protocol."""
        # Many Swift protocols end with common suffixes
        protocol_suffixes = ["Protocol", "Delegate", "DataSource", "able", "ing"]
        return any(name.endswith(suffix) for suffix in protocol_suffixes)

    def _looks_like_property_wrapper(self, name: str) -> bool:
        """Check if a name looks like a property wrapper."""
        # Common property wrapper patterns
        wrapper_patterns = [
            "State",
            "Binding",
            "Published",
            "ObservedObject",
            "EnvironmentObject",
        ]
        return name in wrapper_patterns or name.startswith(("UI", "Core", "App"))

    def _looks_like_result_builder(self, name: str) -> bool:
        """Check if a name looks like a result builder."""
        # Common result builder patterns
        builder_patterns = ["Builder", "DSL"]
        return any(pattern in name for pattern in builder_patterns)

    def _init_system_protocols(self) -> Dict[str, List[str]]:
        """Initialize system protocol requirements."""
        return {
            "Equatable": ["=="],
            "Hashable": ["hash(into:)"],
            "Comparable": ["<"],
            "Codable": ["encode(to:)", "init(from:)"],
            "CustomStringConvertible": ["description"],
            "CustomDebugStringConvertible": ["debugDescription"],
            "Sequence": ["makeIterator()"],
            "Collection": ["startIndex", "endIndex", "subscript(_:)", "index(after:)"],
            "RandomAccessCollection": [],
            "BidirectionalCollection": ["index(before:)"],
            "RangeReplaceableCollection": ["init()", "replaceSubrange(_:with:)"],
            "ExpressibleByStringLiteral": ["init(stringLiteral:)"],
            "ExpressibleByIntegerLiteral": ["init(integerLiteral:)"],
            "ExpressibleByFloatLiteral": ["init(floatLiteral:)"],
            "ExpressibleByBooleanLiteral": ["init(booleanLiteral:)"],
            "ExpressibleByArrayLiteral": ["init(arrayLiteral:)"],
            "ExpressibleByDictionaryLiteral": ["init(dictionaryLiteral:)"],
            "CaseIterable": ["allCases"],
            "Error": [],
            "LocalizedError": [
                "errorDescription",
                "failureReason",
                "recoverySuggestion",
                "helpAnchor",
            ],
            "ObservableObject": ["objectWillChange"],
            "Identifiable": ["id"],
            "Sendable": [],
            "Actor": [],
        }
