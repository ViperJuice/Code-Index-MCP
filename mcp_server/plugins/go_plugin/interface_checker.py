"""Go interface satisfaction checker."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .package_analyzer import InterfaceInfo, PackageInfo, TypeInfo

logger = logging.getLogger(__name__)


@dataclass
class InterfaceSatisfaction:
    """Represents interface satisfaction result."""

    type_name: str
    interface_name: str
    satisfied: bool
    missing_methods: List[str]
    implemented_methods: List[str]
    notes: List[str]


class GoInterfaceChecker:
    """Checks interface satisfaction for Go types."""

    def __init__(self, package_analyzer):
        self.package_analyzer = package_analyzer
        self._satisfaction_cache: Dict[Tuple[str, str], InterfaceSatisfaction] = {}

    def check_interface_satisfaction(
        self, type_info: TypeInfo, interface_info: InterfaceInfo
    ) -> InterfaceSatisfaction:
        """Check if a type satisfies an interface."""
        cache_key = (type_info.name, interface_info.name)
        if cache_key in self._satisfaction_cache:
            return self._satisfaction_cache[cache_key]

        # Get all methods of the type (including promoted methods)
        type_methods = self._get_all_methods(type_info)

        # Get all required methods from interface (including embedded)
        required_methods = self._get_all_interface_methods(interface_info)

        # Check satisfaction
        implemented = []
        missing = []
        notes = []

        for method_name, method_sig in required_methods.items():
            if method_name in type_methods:
                # Check if signatures are compatible
                if self._signatures_compatible(type_methods[method_name], method_sig):
                    implemented.append(method_name)
                else:
                    missing.append(method_name)
                    notes.append(f"Method {method_name} has incompatible signature")
            else:
                missing.append(method_name)

        satisfied = len(missing) == 0

        result = InterfaceSatisfaction(
            type_name=type_info.name,
            interface_name=interface_info.name,
            satisfied=satisfied,
            missing_methods=missing,
            implemented_methods=implemented,
            notes=notes,
        )

        self._satisfaction_cache[cache_key] = result
        return result

    def find_types_implementing_interface(
        self, interface_info: InterfaceInfo, packages: List[PackageInfo]
    ) -> List[TypeInfo]:
        """Find all types that implement a given interface."""
        implementing_types = []

        for package in packages:
            for type_info in package.types.values():
                result = self.check_interface_satisfaction(type_info, interface_info)
                if result.satisfied:
                    implementing_types.append(type_info)

        return implementing_types

    def find_interfaces_for_type(
        self, type_info: TypeInfo, packages: List[PackageInfo]
    ) -> List[InterfaceInfo]:
        """Find all interfaces that a type satisfies."""
        satisfied_interfaces = []

        for package in packages:
            for interface_info in package.interfaces.values():
                result = self.check_interface_satisfaction(type_info, interface_info)
                if result.satisfied:
                    satisfied_interfaces.append(interface_info)

        return satisfied_interfaces

    def _get_all_methods(self, type_info: TypeInfo) -> Dict[str, str]:
        """Get all methods of a type including promoted methods."""
        methods = {}

        # Direct methods
        for method_name in type_info.methods:
            # Find the method signature
            method_sig = self._find_method_signature(type_info, method_name)
            if method_sig:
                methods[method_name] = method_sig

        # Methods from embedded types
        for embedded_type in type_info.embedded:
            embedded_methods = self._get_embedded_methods(embedded_type)
            methods.update(embedded_methods)

        return methods

    def _get_all_interface_methods(self, interface_info: InterfaceInfo) -> Dict[str, str]:
        """Get all methods required by an interface including embedded interfaces."""
        methods = dict(interface_info.methods)

        # Methods from embedded interfaces
        for embedded_interface in interface_info.embedded:
            embedded_methods = self._get_embedded_interface_methods(embedded_interface)
            methods.update(embedded_methods)

        return methods

    def _find_method_signature(self, type_info: TypeInfo, method_name: str) -> Optional[str]:
        """Find the signature of a method for a type."""
        # Look through the package for the method
        for package_info in self.package_analyzer.packages.values():
            for func_info in package_info.functions.values():
                if (
                    func_info.name == method_name
                    and func_info.receiver
                    and self._receiver_matches_type(func_info.receiver, type_info.name)
                ):
                    return func_info.signature
        return None

    def _receiver_matches_type(self, receiver: str, type_name: str) -> bool:
        """Check if a receiver matches a type name."""
        # Remove pointer if present
        receiver = receiver.replace("*", "").strip()
        # Check if type name is in receiver
        return type_name in receiver

    def _get_embedded_methods(self, embedded_type: str) -> Dict[str, str]:
        """Get methods from an embedded type."""
        methods = {}

        # Find the embedded type in packages
        for package_info in self.package_analyzer.packages.values():
            if embedded_type in package_info.types:
                embedded_info = package_info.types[embedded_type]
                methods.update(self._get_all_methods(embedded_info))
                break

        return methods

    def _get_embedded_interface_methods(self, embedded_interface: str) -> Dict[str, str]:
        """Get methods from an embedded interface."""
        methods = {}

        # Find the embedded interface in packages
        for package_info in self.package_analyzer.packages.values():
            if embedded_interface in package_info.interfaces:
                embedded_info = package_info.interfaces[embedded_interface]
                methods.update(self._get_all_interface_methods(embedded_info))
                break

        return methods

    def _signatures_compatible(self, impl_sig: str, interface_sig: str) -> bool:
        """Check if two method signatures are compatible."""
        # Simple compatibility check - in reality this would need more sophisticated parsing
        # For now, we'll do basic normalization and comparison

        # Normalize whitespace
        impl_sig = " ".join(impl_sig.split())
        interface_sig = " ".join(interface_sig.split())

        # Extract method parts
        impl_parts = self._parse_method_signature(impl_sig)
        interface_parts = self._parse_method_signature(interface_sig)

        if not impl_parts or not interface_parts:
            return False

        # Compare parameters and returns
        return (
            impl_parts["params"] == interface_parts["params"]
            and impl_parts["returns"] == interface_parts["returns"]
        )

    def _parse_method_signature(self, signature: str) -> Optional[Dict[str, str]]:
        """Parse a method signature into components."""
        import re

        # Extract method name, params, and returns
        match = re.search(r"(\w+)\s*\(([^)]*)\)(?:\s*\(([^)]*)\))?(?:\s+(.+))?", signature)
        if match:
            method_name = match.group(1)
            params = match.group(2) or ""
            returns = match.group(3) or match.group(4) or ""

            return {
                "name": method_name,
                "params": self._normalize_params(params),
                "returns": self._normalize_returns(returns),
            }
        return None

    def _normalize_params(self, params: str) -> str:
        """Normalize parameter list for comparison."""
        if not params:
            return ""

        # Simple normalization - remove parameter names, keep types
        parts = []
        for param in params.split(","):
            param = param.strip()
            if param:
                # Try to extract just the type
                tokens = param.split()
                if len(tokens) >= 2:
                    # Assume last token is the type
                    parts.append(tokens[-1])
                elif tokens:
                    parts.append(tokens[0])

        return ",".join(parts)

    def _normalize_returns(self, returns: str) -> str:
        """Normalize return types for comparison."""
        if not returns:
            return ""

        returns = returns.strip()
        if returns.startswith("(") and returns.endswith(")"):
            returns = returns[1:-1]

        # Split and rejoin to normalize spacing
        parts = [r.strip() for r in returns.split(",") if r.strip()]
        return ",".join(parts)

    def generate_interface_report(self, packages: List[PackageInfo]) -> str:
        """Generate a report of interface implementations."""
        report_lines = ["# Go Interface Implementation Report\n"]

        for package in packages:
            if package.interfaces:
                report_lines.append(f"\n## Package: {package.name}")
                report_lines.append(f"Path: {package.path}\n")

                for interface_info in package.interfaces.values():
                    report_lines.append(f"\n### Interface: {interface_info.name}")
                    report_lines.append(f"Methods: {len(interface_info.methods)}")

                    # Find implementing types
                    implementing_types = self.find_types_implementing_interface(
                        interface_info, packages
                    )

                    if implementing_types:
                        report_lines.append("\nImplemented by:")
                        for type_info in implementing_types:
                            report_lines.append(f"  - {type_info.name} ({type_info.file})")
                    else:
                        report_lines.append("\nNo implementations found.")

        return "\n".join(report_lines)
