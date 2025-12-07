"""Objective-C interoperability analysis for Swift code."""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ObjCInteropType(Enum):
    """Types of Objective-C interoperability."""

    IMPORT = "import"  # Importing Objective-C headers
    EXPOSE = "expose"  # Exposing Swift to Objective-C
    BRIDGE = "bridge"  # Bridging between types
    SELECTOR = "selector"  # Using selectors
    RUNTIME = "runtime"  # Runtime introspection


@dataclass
class ObjCBridgingHeader:
    """Information about bridging header usage."""

    header_path: str
    imported_classes: List[str]
    imported_protocols: List[str]
    imported_functions: List[str]
    imported_constants: List[str]

    def __post_init__(self):
        if self.imported_classes is None:
            self.imported_classes = []
        if self.imported_protocols is None:
            self.imported_protocols = []
        if self.imported_functions is None:
            self.imported_functions = []
        if self.imported_constants is None:
            self.imported_constants = []


@dataclass
class ObjCExposure:
    """Information about Swift code exposed to Objective-C."""

    symbol_name: str
    symbol_type: str  # class, protocol, method, property
    objc_name: Optional[str]  # Custom Objective-C name
    file_path: str
    line_number: int
    attributes: List[str] = None  # @objc, @objcMembers, etc.

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = []


@dataclass
class TypeBridging:
    """Information about type bridging between Swift and Objective-C."""

    swift_type: str
    objc_type: str
    bridging_method: str  # automatic, explicit, toll-free
    is_collection: bool = False
    element_type: Optional[str] = None


@dataclass
class SelectorUsage:
    """Information about Objective-C selector usage."""

    selector_name: str
    target_type: Optional[str]
    usage_context: str  # method_call, target_action, kvo, etc.
    file_path: str
    line_number: int


class ObjectiveCBridge:
    """Analyzes Objective-C interoperability in Swift code."""

    def __init__(self):
        self.bridging_headers: List[ObjCBridgingHeader] = []
        self.exposures: List[ObjCExposure] = []
        self.type_bridges: Dict[str, TypeBridging] = {}
        self.selector_usage: List[SelectorUsage] = []

        # Initialize type bridging mappings
        self._init_type_bridges()

        # Known Objective-C frameworks and their types
        self.objc_frameworks = self._init_objc_frameworks()

    def analyze_interop(self, content: str, file_path: str = "") -> Dict[str, Any]:
        """Analyze Objective-C interoperability in Swift code."""
        analysis = {
            "objc_attributes": self._find_objc_attributes(content, file_path),
            "bridging_casts": self._find_bridging_casts(content, file_path),
            "selector_usage": self._find_selector_usage(content, file_path),
            "objc_runtime": self._find_objc_runtime_usage(content, file_path),
            "foundation_usage": self._find_foundation_usage(content, file_path),
            "toll_free_bridging": self._find_toll_free_bridging(content, file_path),
            "unsafe_interop": self._find_unsafe_interop(content, file_path),
            "objc_exceptions": self._find_objc_exception_handling(content, file_path),
        }

        # Calculate interop complexity score
        analysis["complexity_score"] = self._calculate_interop_complexity(analysis)

        return analysis

    def analyze_bridging_header(self, header_path: Path) -> ObjCBridgingHeader:
        """Analyze an Objective-C bridging header."""
        if not header_path.exists():
            return ObjCBridgingHeader(str(header_path), [], [], [], [])

        try:
            content = header_path.read_text()

            # Parse Objective-C header content
            classes = self._parse_objc_classes(content)
            protocols = self._parse_objc_protocols(content)
            functions = self._parse_objc_functions(content)
            constants = self._parse_objc_constants(content)

            bridging_header = ObjCBridgingHeader(
                header_path=str(header_path),
                imported_classes=classes,
                imported_protocols=protocols,
                imported_functions=functions,
                imported_constants=constants,
            )

            self.bridging_headers.append(bridging_header)
            return bridging_header

        except Exception as e:
            logger.warning(f"Failed to analyze bridging header {header_path}: {e}")
            return ObjCBridgingHeader(str(header_path), [], [], [], [])

    def find_objc_exposures(self, content: str, file_path: str = "") -> List[ObjCExposure]:
        """Find Swift symbols exposed to Objective-C."""
        exposures = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("//") or line.startswith("/*"):
                continue

            # Find @objc attributes
            objc_match = re.search(
                r"@objc(?:\(([^)]+)\))?\s+(?:(class|protocol|func|var)\s+(\w+))?", line
            )
            if objc_match:
                custom_name = objc_match.group(1)
                symbol_type = objc_match.group(2) or "unknown"
                symbol_name = objc_match.group(3) or "unknown"

                exposure = ObjCExposure(
                    symbol_name=symbol_name,
                    symbol_type=symbol_type,
                    objc_name=custom_name,
                    file_path=file_path,
                    line_number=line_num,
                    attributes=["@objc"],
                )
                exposures.append(exposure)

            # Find @objcMembers
            if "@objcMembers" in line:
                class_match = re.search(r"class\s+(\w+)", line)
                if class_match:
                    exposure = ObjCExposure(
                        symbol_name=class_match.group(1),
                        symbol_type="class",
                        objc_name=None,
                        file_path=file_path,
                        line_number=line_num,
                        attributes=["@objcMembers"],
                    )
                    exposures.append(exposure)

        self.exposures.extend(exposures)
        return exposures

    def validate_objc_compatibility(self, content: str, file_path: str = "") -> Dict[str, Any]:
        """Validate Objective-C compatibility of Swift code."""
        validation = {
            "compatible": True,
            "issues": [],
            "warnings": [],
            "suggestions": [],
        }

        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Check for incompatible Swift features
            incompatible_features = self._find_incompatible_features(line)
            for feature in incompatible_features:
                validation["issues"].append(
                    {
                        "type": "incompatible_feature",
                        "feature": feature,
                        "line": line_num,
                        "message": f"Feature '{feature}' is not compatible with Objective-C",
                    }
                )
                validation["compatible"] = False

            # Check for missing @objc attributes
            missing_objc = self._check_missing_objc_attributes(line, content, line_num)
            for issue in missing_objc:
                validation["warnings"].append(issue)

            # Check for problematic type usage
            type_issues = self._check_objc_type_compatibility(line)
            for issue in type_issues:
                validation["warnings"].append(
                    {"type": "type_compatibility", "line": line_num, "message": issue}
                )

        return validation

    def _find_objc_attributes(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Find @objc and related attributes."""
        attributes = []

        # Pattern to match various @objc attributes
        objc_patterns = [
            r"@objc(?:\(([^)]+)\))?",
            r"@objcMembers",
            r"@NSManaged",
            r"@NSCopying",
            r"@IBAction",
            r"@IBOutlet",
            r"@IBDesignable",
            r"@IBInspectable",
        ]

        for pattern in objc_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                attributes.append(
                    {
                        "attribute": match.group(0),
                        "custom_name": (match.group(1) if len(match.groups()) > 0 else None),
                        "line": line_num,
                        "file": file_path,
                    }
                )

        return attributes

    def _find_bridging_casts(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Find bridging casts between Swift and Objective-C types."""
        casts = []

        # Common bridging cast patterns
        cast_patterns = [
            r"(\w+)\s+as\s+(\w+)",  # Basic cast
            r"(\w+)\s+as\!\s+(\w+)",  # Force cast
            r"(\w+)\s+as\?\s+(\w+)",  # Optional cast
            r"unsafeBitCast\(([^,]+),\s*to:\s*([^)]+)\)",  # Unsafe cast
        ]

        for pattern in cast_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                source_type = match.group(1)
                target_type = match.group(2)

                # Check if it's a bridging cast
                if self._is_bridging_cast(source_type, target_type):
                    casts.append(
                        {
                            "source_type": source_type,
                            "target_type": target_type,
                            "cast_type": self._get_cast_type(match.group(0)),
                            "line": line_num,
                            "file": file_path,
                        }
                    )

        return casts

    def _find_selector_usage(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Find Objective-C selector usage."""
        selectors = []

        # Selector patterns
        selector_patterns = [
            r"#selector\(([^)]+)\)",
            r'Selector\("([^"]+)"\)',
            r'NSSelectorFromString\("([^"]+)"\)',
            r"@selector\(([^)]+)\)",  # Less common in Swift
        ]

        for pattern in selector_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                selector_name = match.group(1)

                # Determine context
                context = self._determine_selector_context(content, match.start())

                selectors.append(
                    {
                        "selector": selector_name,
                        "context": context,
                        "line": line_num,
                        "file": file_path,
                    }
                )

        return selectors

    def _find_objc_runtime_usage(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Find Objective-C runtime API usage."""
        runtime_usage = []

        # Runtime API patterns
        runtime_patterns = [
            r'objc_getClass\("([^"]+)"\)',
            r"object_getClass\(([^)]+)\)",
            r"class_addMethod\([^)]+\)",
            r"method_exchangeImplementations\([^)]+\)",
            r"objc_setAssociatedObject\([^)]+\)",
            r"objc_getAssociatedObject\([^)]+\)",
            r'NSClassFromString\("([^"]+)"\)',
            r"NSStringFromClass\(([^)]+)\)",
        ]

        for pattern in runtime_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                runtime_usage.append(
                    {
                        "api": match.group(0),
                        "function": pattern.split("\\")[0].replace("r'", ""),
                        "line": line_num,
                        "file": file_path,
                    }
                )

        return runtime_usage

    def _find_foundation_usage(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Find Foundation framework usage that might involve bridging."""
        foundation_usage = []

        # Foundation types that bridge to Swift
        foundation_types = [
            "NSString",
            "NSArray",
            "NSDictionary",
            "NSSet",
            "NSData",
            "NSDate",
            "NSURL",
            "NSNumber",
            "NSError",
            "NSNotification",
            "NSUserDefaults",
        ]

        for foundation_type in foundation_types:
            pattern = rf"\b{foundation_type}\b"
            matches = re.finditer(pattern, content)

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                # Check if it's used in a bridging context
                context_line = content.split("\n")[line_num - 1]
                is_bridging = (
                    "as " in context_line
                    or "bridge" in context_line.lower()
                    or "()" in context_line
                )  # Initializer call

                if is_bridging:
                    foundation_usage.append(
                        {
                            "type": foundation_type,
                            "bridging": True,
                            "line": line_num,
                            "file": file_path,
                        }
                    )

        return foundation_usage

    def _find_toll_free_bridging(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Find toll-free bridging usage."""
        toll_free_usage = []

        # Core Foundation types that are toll-free bridged
        cf_types = [
            "CFString",
            "CFArray",
            "CFDictionary",
            "CFSet",
            "CFData",
            "CFDate",
            "CFURL",
            "CFNumber",
            "CFError",
            "CFNotification",
        ]

        for cf_type in cf_types:
            pattern = rf"\b{cf_type}(?:Ref)?\b"
            matches = re.finditer(pattern, content)

            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                toll_free_usage.append(
                    {"cf_type": match.group(0), "line": line_num, "file": file_path}
                )

        return toll_free_usage

    def _find_unsafe_interop(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Find unsafe interoperability patterns."""
        unsafe_patterns = []

        # Unsafe interop patterns
        unsafe_apis = [
            r"UnsafeMutablePointer",
            r"UnsafePointer",
            r"UnsafeRawPointer",
            r"UnsafeMutableRawPointer",
            r"withUnsafePointer",
            r"withUnsafeMutablePointer",
            r"unsafeBitCast",
            r"Unmanaged\.",
        ]

        for pattern in unsafe_apis:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                unsafe_patterns.append(
                    {
                        "pattern": match.group(0),
                        "type": "unsafe_interop",
                        "line": line_num,
                        "file": file_path,
                    }
                )

        return unsafe_patterns

    def _find_objc_exception_handling(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Find Objective-C exception handling patterns."""
        exception_patterns = []

        # Exception handling patterns
        patterns = [
            r"try\s+ObjC\.catchException\s*\{",
            r"NSException\.",
            r"@throw",
            r"NS_DURING",
            r"NS_HANDLER",
            r"NS_ENDHANDLER",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1

                exception_patterns.append(
                    {
                        "pattern": match.group(0),
                        "type": "exception_handling",
                        "line": line_num,
                        "file": file_path,
                    }
                )

        return exception_patterns

    def _parse_objc_classes(self, content: str) -> List[str]:
        """Parse Objective-C class declarations from header content."""
        classes = []

        # Objective-C class patterns
        class_patterns = [
            r"@interface\s+(\w+)\s*:",
            r"@interface\s+(\w+)\s*\(",  # Category
            r"@interface\s+(\w+)\s*$",  # No superclass
        ]

        for pattern in class_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                classes.append(match.group(1))

        return list(set(classes))

    def _parse_objc_protocols(self, content: str) -> List[str]:
        """Parse Objective-C protocol declarations."""
        protocols = []

        protocol_pattern = r"@protocol\s+(\w+)"
        matches = re.finditer(protocol_pattern, content)

        for match in matches:
            protocols.append(match.group(1))

        return list(set(protocols))

    def _parse_objc_functions(self, content: str) -> List[str]:
        """Parse Objective-C function declarations."""
        functions = []

        # C function patterns
        function_patterns = [
            r"^\s*\w+\s+(\w+)\s*\([^)]*\)\s*;",  # Return type function(params);
            r"^\s*extern\s+\w+\s+(\w+)\s*\([^)]*\)\s*;",  # extern functions
        ]

        for pattern in function_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                functions.append(match.group(1))

        return list(set(functions))

    def _parse_objc_constants(self, content: str) -> List[str]:
        """Parse Objective-C constant declarations."""
        constants = []

        # Constant patterns
        constant_patterns = [
            r"^\s*extern\s+\w+\s+(\w+)\s*;",  # extern constants
            r"^\s*#define\s+(\w+)",  # Macros
            r"^\s*const\s+\w+\s+(\w+)",  # const declarations
        ]

        for pattern in constant_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                constants.append(match.group(1))

        return list(set(constants))

    def _find_incompatible_features(self, line: str) -> List[str]:
        """Find Swift features incompatible with Objective-C."""
        incompatible = []

        # Features not compatible with @objc
        incompatible_features = [
            ("struct", "structs"),
            ("enum", "enums (except @objc enums)"),
            ("protocol.*where", "protocols with associated types"),
            ("func.*<.*>", "generic functions"),
            ("var.*some ", "opaque return types"),
            ("inout ", "inout parameters"),
            ("throws", "throwing functions (use NSError)"),
            ("rethrows", "rethrowing functions"),
        ]

        for pattern, feature_name in incompatible_features:
            if re.search(pattern, line) and "@objc" in line:
                incompatible.append(feature_name)

        return incompatible

    def _check_missing_objc_attributes(
        self, line: str, full_content: str, line_num: int
    ) -> List[Dict[str, Any]]:
        """Check for symbols that should have @objc attributes."""
        issues = []

        # Patterns that might need @objc
        if "IBAction" in line or "IBOutlet" in line or "target:" in line and "action:" in line:

            if "@objc" not in line:
                issues.append(
                    {
                        "type": "missing_objc",
                        "line": line_num,
                        "message": "Consider adding @objc attribute for Objective-C interoperability",
                    }
                )

        return issues

    def _check_objc_type_compatibility(self, line: str) -> List[str]:
        """Check for Objective-C type compatibility issues."""
        issues = []

        # Swift types that don't bridge automatically
        problematic_types = [
            "Set",
            "OptionSet",
            "Character",
            "UInt",
            "UInt8",
            "UInt16",
            "UInt32",
            "UInt64",
            "Int8",
            "Int16",
            "Int32",
            "Int64",
            "Float80",
        ]

        for ptype in problematic_types:
            if f": {ptype}" in line or f"-> {ptype}" in line:
                issues.append(f"Type '{ptype}' may not bridge properly to Objective-C")

        return issues

    def _is_bridging_cast(self, source_type: str, target_type: str) -> bool:
        """Check if a cast is a bridging cast."""
        # Check if types are in our bridging mappings
        return (
            source_type in self.type_bridges
            or target_type in self.type_bridges
            or self._is_foundation_bridging(source_type, target_type)
        )

    def _is_foundation_bridging(self, source_type: str, target_type: str) -> bool:
        """Check if it's Foundation bridging."""
        foundation_pairs = [
            ("String", "NSString"),
            ("Array", "NSArray"),
            ("Dictionary", "NSDictionary"),
            ("Set", "NSSet"),
            ("Data", "NSData"),
            ("Date", "NSDate"),
            ("URL", "NSURL"),
            ("Int", "NSNumber"),
            ("Double", "NSNumber"),
        ]

        for swift_type, objc_type in foundation_pairs:
            if (source_type == swift_type and target_type == objc_type) or (
                source_type == objc_type and target_type == swift_type
            ):
                return True

        return False

    def _get_cast_type(self, cast_expression: str) -> str:
        """Determine the type of cast."""
        if "as!" in cast_expression:
            return "force_cast"
        elif "as?" in cast_expression:
            return "optional_cast"
        elif "unsafeBitCast" in cast_expression:
            return "unsafe_cast"
        else:
            return "safe_cast"

    def _determine_selector_context(self, content: str, position: int) -> str:
        """Determine the context of selector usage."""
        # Look at surrounding context
        start = max(0, position - 100)
        end = min(len(content), position + 100)
        context = content[start:end]

        if "addTarget" in context or "target:" in context:
            return "target_action"
        elif "addObserver" in context or "observer:" in context:
            return "kvo"
        elif "performSelector" in context:
            return "perform_selector"
        elif "responds" in context:
            return "responds_to_selector"
        else:
            return "general"

    def _calculate_interop_complexity(self, analysis: Dict[str, Any]) -> int:
        """Calculate a complexity score for Objective-C interoperability."""
        score = 0

        # Add points for various interop features
        score += len(analysis.get("objc_attributes", [])) * 1
        score += len(analysis.get("bridging_casts", [])) * 2
        score += len(analysis.get("selector_usage", [])) * 3
        score += len(analysis.get("objc_runtime", [])) * 5
        score += len(analysis.get("unsafe_interop", [])) * 10

        return score

    def _init_type_bridges(self):
        """Initialize type bridging mappings."""
        self.type_bridges = {
            "String": TypeBridging("String", "NSString", "automatic"),
            "Array": TypeBridging("Array", "NSArray", "automatic", is_collection=True),
            "Dictionary": TypeBridging(
                "Dictionary", "NSDictionary", "automatic", is_collection=True
            ),
            "Set": TypeBridging("Set", "NSSet", "automatic", is_collection=True),
            "Data": TypeBridging("Data", "NSData", "automatic"),
            "Date": TypeBridging("Date", "NSDate", "automatic"),
            "URL": TypeBridging("URL", "NSURL", "automatic"),
            "Int": TypeBridging("Int", "NSNumber", "automatic"),
            "Double": TypeBridging("Double", "NSNumber", "automatic"),
            "Float": TypeBridging("Float", "NSNumber", "automatic"),
            "Bool": TypeBridging("Bool", "NSNumber", "automatic"),
        }

    def _init_objc_frameworks(self) -> Dict[str, List[str]]:
        """Initialize Objective-C framework type mappings."""
        return {
            "Foundation": [
                "NSObject",
                "NSString",
                "NSArray",
                "NSDictionary",
                "NSSet",
                "NSData",
                "NSDate",
                "NSURL",
                "NSNumber",
                "NSError",
                "NSNotification",
                "NSUserDefaults",
                "NSBundle",
                "NSFileManager",
            ],
            "UIKit": [
                "UIView",
                "UIViewController",
                "UILabel",
                "UIButton",
                "UIImageView",
                "UITableView",
                "UICollectionView",
                "UINavigationController",
                "UITabBarController",
            ],
            "CoreFoundation": [
                "CFString",
                "CFArray",
                "CFDictionary",
                "CFSet",
                "CFData",
                "CFDate",
                "CFURL",
                "CFNumber",
            ],
        }
