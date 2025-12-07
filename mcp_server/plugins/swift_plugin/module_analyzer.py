"""Swift module system and framework import analyzer."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..specialized_plugin_base import ImportInfo

logger = logging.getLogger(__name__)


@dataclass
class SwiftModule:
    """Represents a Swift module."""

    name: str
    path: Optional[Path] = None
    is_framework: bool = False
    is_system: bool = False
    targets: List[str] = None
    dependencies: List[str] = None

    def __post_init__(self):
        if self.targets is None:
            self.targets = []
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class FrameworkInfo:
    """Information about an imported framework."""

    name: str
    import_type: str  # 'framework', 'module', 'class', 'struct', 'protocol', 'func'
    imported_symbols: List[str]
    is_system_framework: bool
    availability: Optional[str] = None  # iOS version, macOS version, etc.


class SwiftModuleAnalyzer:
    """Analyzes Swift module system and framework imports."""

    def __init__(self):
        self.modules: Dict[str, SwiftModule] = {}
        self.frameworks: Dict[str, FrameworkInfo] = {}
        self.import_cache: Dict[str, List[ImportInfo]] = {}

        # System frameworks and their symbols
        self.system_frameworks = self._init_system_frameworks()

    def analyze_imports(self, content: str) -> List[ImportInfo]:
        """Analyze all import statements in Swift code."""
        imports = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("//") or line.startswith("/*"):
                continue

            # Parse different import patterns
            import_info = self._parse_import_statement(line, line_num)
            if import_info:
                imports.append(import_info)

        return imports

    def _parse_import_statement(self, line: str, line_number: int) -> Optional[ImportInfo]:
        """Parse a single import statement."""
        # Basic import patterns
        patterns = [
            # import Module
            (r"^import\s+(\w+)$", "module"),
            # import Module.SubModule
            (r"^import\s+([\w.]+)$", "module"),
            # import class Module.ClassName
            (
                r"^import\s+(class|struct|protocol|enum|func|var|typealias)\s+([\w.]+)$",
                "specific",
            ),
            # @testable import Module
            (r"^@testable\s+import\s+(\w+)$", "testable"),
            # import Foundation.NSString
            (r"^import\s+([\w.]+)\.([\w.]+)$", "specific_symbol"),
        ]

        for pattern, import_type in patterns:
            match = re.match(pattern, line)
            if match:
                if import_type == "module":
                    module_path = match.group(1)
                    return ImportInfo(
                        module_path=module_path,
                        imported_names=[],
                        line_number=line_number,
                        is_relative=False,
                    )

                elif import_type == "specific":
                    symbol_type = match.group(1)
                    full_path = match.group(2)
                    parts = full_path.split(".")
                    module_path = parts[0]
                    symbol_name = parts[-1] if len(parts) > 1 else full_path

                    return ImportInfo(
                        module_path=module_path,
                        imported_names=[f"{symbol_type} {symbol_name}"],
                        line_number=line_number,
                        is_relative=False,
                    )

                elif import_type == "testable":
                    module_path = match.group(1)
                    return ImportInfo(
                        module_path=module_path,
                        imported_names=[],
                        line_number=line_number,
                        is_relative=False,
                        alias="@testable",
                    )

                elif import_type == "specific_symbol":
                    module_path = match.group(1)
                    symbol_name = match.group(2)

                    return ImportInfo(
                        module_path=module_path,
                        imported_names=[symbol_name],
                        line_number=line_number,
                        is_relative=False,
                    )

        return None

    def analyze_swift_package(self, package_swift_path: Path) -> Dict[str, SwiftModule]:
        """Analyze Package.swift file to understand module structure."""
        modules = {}

        try:
            content = package_swift_path.read_text()

            # Parse targets
            targets = self._parse_package_targets(content)

            for target in targets:
                module = SwiftModule(
                    name=target["name"],
                    is_framework=target.get("type") == "framework",
                    targets=[target["name"]],
                    dependencies=target.get("dependencies", []),
                )
                modules[target["name"]] = module

            # Parse package dependencies
            package_deps = self._parse_package_dependencies(content)

            # Update modules with external dependencies
            for module in modules.values():
                module.dependencies.extend(package_deps)

        except Exception as e:
            logger.warning(f"Failed to analyze Package.swift: {e}")

        return modules

    def _parse_package_targets(self, content: str) -> List[Dict[str, Any]]:
        """Parse target definitions from Package.swift."""
        targets = []

        # Look for .target and .executableTarget definitions
        target_patterns = [
            r'\.target\(\s*name:\s*"([^"]+)"[^)]*dependencies:\s*\[([^\]]*)\]',
            r'\.executableTarget\(\s*name:\s*"([^"]+)"[^)]*dependencies:\s*\[([^\]]*)\]',
            r'\.testTarget\(\s*name:\s*"([^"]+)"[^)]*dependencies:\s*\[([^\]]*)\]',
        ]

        for pattern in target_patterns:
            matches = re.finditer(pattern, content, re.DOTALL)
            for match in matches:
                name = match.group(1)
                deps_str = match.group(2) if len(match.groups()) > 1 else ""

                # Parse dependencies
                dependencies = []
                if deps_str:
                    # Simple parsing - could be improved
                    dep_matches = re.findall(r'"([^"]+)"', deps_str)
                    dependencies = dep_matches

                target_type = "library"
                if ".executableTarget" in match.group(0):
                    target_type = "executable"
                elif ".testTarget" in match.group(0):
                    target_type = "test"

                targets.append({"name": name, "type": target_type, "dependencies": dependencies})

        return targets

    def _parse_package_dependencies(self, content: str) -> List[str]:
        """Parse package-level dependencies from Package.swift."""
        dependencies = []

        # Look for .package dependencies
        package_patterns = [
            r'\.package\(url:\s*"[^"]*\/([^"/]+)(?:\.git)?",',
            r'\.package\(name:\s*"([^"]+)"',
            r'\.package\(path:\s*"([^"]+)"',
        ]

        for pattern in package_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                dep_name = match.group(1)
                # Extract package name from URL or use as-is
                if "/" in dep_name:
                    dep_name = dep_name.split("/")[-1]
                dependencies.append(dep_name)

        return dependencies

    def analyze_framework_usage(self, content: str) -> Dict[str, FrameworkInfo]:
        """Analyze how frameworks are used in the code."""
        framework_usage = {}

        # Get all imports first
        imports = self.analyze_imports(content)

        for import_info in imports:
            module_name = import_info.module_path

            # Check if it's a known system framework
            is_system = module_name in self.system_frameworks

            # Analyze usage patterns in the code
            usage_symbols = self._find_framework_symbol_usage(content, module_name)

            framework_info = FrameworkInfo(
                name=module_name,
                import_type="framework" if is_system else "module",
                imported_symbols=import_info.imported_names + usage_symbols,
                is_system_framework=is_system,
                availability=self._detect_availability_requirements(content, module_name),
            )

            framework_usage[module_name] = framework_info

        return framework_usage

    def _find_framework_symbol_usage(self, content: str, framework_name: str) -> List[str]:
        """Find symbols from a framework used in the code."""
        symbols = []

        if framework_name not in self.system_frameworks:
            return symbols

        framework_symbols = self.system_frameworks[framework_name]

        # Look for usage of known framework symbols
        for symbol in framework_symbols:
            # Simple pattern matching - could be improved with AST parsing
            patterns = [
                rf"\b{re.escape(symbol)}\b",  # Direct usage
                rf"{re.escape(symbol)}\(",  # Function/initializer call
                rf"\.{re.escape(symbol)}\b",  # Property/method access
            ]

            for pattern in patterns:
                if re.search(pattern, content):
                    symbols.append(symbol)
                    break

        return list(set(symbols))  # Remove duplicates

    def _detect_availability_requirements(self, content: str, framework_name: str) -> Optional[str]:
        """Detect availability requirements for framework usage."""
        # Look for @available attributes
        available_patterns = [
            r"@available\(([^)]+)\)",
            r"if\s+#available\(([^)]+)\)",
        ]

        availability_info = []

        for pattern in available_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                availability_info.append(match.group(1))

        if availability_info:
            return "; ".join(availability_info)

        return None

    def get_module_dependencies(self, module_name: str) -> List[str]:
        """Get dependencies for a specific module."""
        if module_name in self.modules:
            return self.modules[module_name].dependencies.copy()
        return []

    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the module graph."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(module: str, path: List[str]) -> bool:
            if module in rec_stack:
                # Found cycle
                cycle_start = path.index(module)
                cycles.append(path[cycle_start:] + [module])
                return True

            if module in visited:
                return False

            visited.add(module)
            rec_stack.add(module)
            path.append(module)

            if module in self.modules:
                for dep in self.modules[module].dependencies:
                    if dfs(dep, path):
                        return True

            rec_stack.remove(module)
            path.pop()
            return False

        for module in self.modules:
            if module not in visited:
                dfs(module, [])

        return cycles

    def validate_imports(self, content: str, available_modules: Set[str]) -> List[Dict[str, Any]]:
        """Validate that all imports are available."""
        issues = []
        imports = self.analyze_imports(content)

        for import_info in imports:
            module_name = import_info.module_path

            # Check if module is available
            if (
                module_name not in available_modules
                and module_name not in self.system_frameworks
                and not self._is_local_module(module_name)
            ):

                issues.append(
                    {
                        "type": "missing_module",
                        "module": module_name,
                        "line": import_info.line_number,
                        "message": f"Module '{module_name}' not found",
                    }
                )

            # Check specific symbol imports
            if import_info.imported_names:
                for symbol in import_info.imported_names:
                    if not self._validate_symbol_availability(module_name, symbol):
                        issues.append(
                            {
                                "type": "missing_symbol",
                                "module": module_name,
                                "symbol": symbol,
                                "line": import_info.line_number,
                                "message": f"Symbol '{symbol}' not found in module '{module_name}'",
                            }
                        )

        return issues

    def _is_local_module(self, module_name: str) -> bool:
        """Check if module is a local module."""
        return module_name in self.modules

    def _validate_symbol_availability(self, module_name: str, symbol: str) -> bool:
        """Check if a symbol is available in a module."""
        if module_name in self.system_frameworks:
            framework_symbols = self.system_frameworks[module_name]
            # Remove type prefix if present
            symbol_clean = symbol.split(" ")[-1]
            return symbol_clean in framework_symbols

        # For local modules, assume symbols are available
        # (would need more sophisticated analysis)
        return True

    def _init_system_frameworks(self) -> Dict[str, List[str]]:
        """Initialize system framework symbol mappings."""
        return {
            "Foundation": [
                "NSString",
                "NSArray",
                "NSDictionary",
                "NSData",
                "NSDate",
                "NSError",
                "NSNotificationCenter",
                "NSUserDefaults",
                "NSBundle",
                "NSFileManager",
                "NSTimer",
                "NSThread",
                "NSURL",
                "NSURLSession",
                "NSJSONSerialization",
                "String",
                "Array",
                "Dictionary",
                "Data",
                "Date",
                "NotificationCenter",
                "UserDefaults",
                "Bundle",
                "FileManager",
                "Timer",
                "Thread",
                "URL",
                "URLSession",
                "JSONSerialization",
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
                "UIApplication",
                "UIWindow",
                "UIScreen",
                "UIColor",
                "UIFont",
                "UIImage",
                "UIStoryboard",
                "UIAlertController",
                "UITextField",
                "UITextView",
                "UIScrollView",
                "UIStackView",
            ],
            "SwiftUI": [
                "View",
                "Text",
                "VStack",
                "HStack",
                "ZStack",
                "Button",
                "Image",
                "List",
                "NavigationView",
                "TabView",
                "Form",
                "Section",
                "Toggle",
                "Slider",
                "Stepper",
                "Picker",
                "State",
                "Binding",
                "ObservedObject",
                "StateObject",
                "EnvironmentObject",
                "Environment",
                "Published",
            ],
            "Combine": [
                "Publisher",
                "Subscriber",
                "Subject",
                "PassthroughSubject",
                "CurrentValueSubject",
                "AnyCancellable",
                "Published",
                "ObservableObject",
                "Just",
                "Future",
                "Empty",
                "Fail",
            ],
            "CoreData": [
                "NSManagedObject",
                "NSManagedObjectContext",
                "NSPersistentContainer",
                "NSFetchRequest",
                "NSEntityDescription",
                "NSPredicate",
                "NSSortDescriptor",
                "NSManagedObjectModel",
                "NSPersistentStore",
            ],
            "CoreGraphics": [
                "CGFloat",
                "CGPoint",
                "CGSize",
                "CGRect",
                "CGColor",
                "CGImage",
                "CGContext",
                "CGPath",
                "CGAffineTransform",
            ],
            "QuartzCore": [
                "CALayer",
                "CAAnimation",
                "CABasicAnimation",
                "CAKeyframeAnimation",
                "CATransition",
                "CAShapeLayer",
                "CAGradientLayer",
            ],
            "AVFoundation": [
                "AVPlayer",
                "AVPlayerItem",
                "AVAsset",
                "AVAudioPlayer",
                "AVAudioSession",
                "AVCaptureSession",
                "AVCaptureDevice",
            ],
            "WebKit": [
                "WKWebView",
                "WKWebViewConfiguration",
                "WKUserContentController",
                "WKNavigationDelegate",
                "WKUIDelegate",
            ],
            "MapKit": [
                "MKMapView",
                "MKAnnotation",
                "MKPointAnnotation",
                "MKCoordinateRegion",
                "CLLocationCoordinate2D",
            ],
            "CoreLocation": [
                "CLLocationManager",
                "CLLocation",
                "CLLocationCoordinate2D",
                "CLGeocoder",
                "CLPlacemark",
                "CLLocationManagerDelegate",
            ],
            "UserNotifications": [
                "UNUserNotificationCenter",
                "UNNotificationRequest",
                "UNMutableNotificationContent",
                "UNTimeIntervalNotificationTrigger",
            ],
            "CloudKit": [
                "CKContainer",
                "CKDatabase",
                "CKRecord",
                "CKRecordID",
                "CKQuery",
                "CKQueryOperation",
                "CKModifyRecordsOperation",
            ],
        }
