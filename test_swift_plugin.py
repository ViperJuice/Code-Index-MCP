#!/usr/bin/env python3
"""Test Swift plugin implementation."""

import tempfile
from pathlib import Path
from mcp_server.plugins.swift_plugin.plugin import Plugin
from mcp_server.storage.sqlite_store import SQLiteStore


def test_swift_plugin_basic():
    """Test basic Swift plugin functionality."""
    # Create a temporary Swift file
    swift_content = """
import Foundation
import UIKit
import SwiftUI

@propertyWrapper
struct State<Value> {
    private var value: Value
    
    init(wrappedValue: Value) {
        self.value = wrappedValue
    }
    
    var wrappedValue: Value {
        get { value }
        set { value = newValue }
    }
}

@resultBuilder
struct ViewBuilder {
    static func buildBlock(_ components: any View...) -> some View {
        VStack {
            ForEach(Array(components.indices), id: \\.self) { index in
                components[index]
            }
        }
    }
}

protocol Drawable {
    func draw()
}

class Shape: Drawable {
    func draw() {
        print("Drawing a shape")
    }
}

struct Circle: Drawable {
    let radius: Double
    
    func draw() {
        print("Drawing a circle with radius \\(radius)")
    }
}

extension Circle: Equatable {
    static func == (lhs: Circle, rhs: Circle) -> Bool {
        return lhs.radius == rhs.radius
    }
}

actor DataManager {
    private var data: [String] = []
    
    func addData(_ item: String) async {
        data.append(item)
    }
    
    func getData() async -> [String] {
        return data
    }
}

@objc class SwiftViewController: UIViewController {
    @IBOutlet weak var label: UILabel!
    @State private var count = 0
    
    @IBAction func buttonTapped(_ sender: UIButton) {
        count += 1
        label.text = "Count: \\(count)"
    }
    
    @objc func handleNotification(_ notification: Notification) {
        // Handle notification
    }
}

class MyView: UIView {
    override func draw(_ rect: CGRect) {
        super.draw(rect)
        // Custom drawing
    }
}
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.swift', delete=False) as f:
        f.write(swift_content)
        temp_file = Path(f.name)
    
    try:
        # Create plugin instance
        plugin = Plugin()
        
        # Test supports method
        assert plugin.supports(temp_file), "Plugin should support .swift files"
        assert not plugin.supports("test.py"), "Plugin should not support .py files"
        
        # Test indexing
        index_result = plugin.indexFile(temp_file, swift_content)
        print(f"Index result: {index_result}")
        
        # Verify index structure
        assert index_result['file'] == str(temp_file)
        assert index_result['language'] == 'swift'
        assert len(index_result['symbols']) > 0
        
        # Test module analysis
        module_analyzer = plugin.module_analyzer
        imports = module_analyzer.analyze_imports(swift_content)
        print(f"Found imports: {[imp.module_path for imp in imports]}")
        
        expected_imports = ['Foundation', 'UIKit', 'SwiftUI']
        found_imports = [imp.module_path for imp in imports]
        for expected in expected_imports:
            assert expected in found_imports, f"Should find import: {expected}"
        
        # Test protocol analysis
        protocol_checker = plugin.protocol_checker
        conformances = protocol_checker.find_conformances(swift_content)
        print(f"Found conformances: {conformances}")
        
        assert 'Circle' in conformances, "Should find Circle conformances"
        assert 'Equatable' in conformances['Circle'], "Circle should conform to Equatable"
        
        # Test property wrapper analysis
        property_wrappers = protocol_checker.analyze_property_wrappers(swift_content, str(temp_file))
        print(f"Found property wrappers: {[pw.name for pw in property_wrappers]}")
        
        # Should find State property wrapper definition
        wrapper_names = [pw.name for pw in property_wrappers]
        assert 'State' in wrapper_names, f"Should find State property wrapper, found: {wrapper_names}"
        
        # Test result builder analysis
        result_builders = protocol_checker.analyze_result_builders(swift_content, str(temp_file))
        print(f"Found result builders: {[rb.name for rb in result_builders]}")
        
        builder_names = [rb.name for rb in result_builders]
        assert 'ViewBuilder' in builder_names, f"Should find ViewBuilder result builder, found: {builder_names}"
        
        # Test Objective-C bridge analysis
        objc_bridge = plugin.objc_bridge
        objc_analysis = objc_bridge.analyze_interop(swift_content)
        print(f"Objective-C interop analysis: {objc_analysis}")
        
        # Should find @objc attributes
        objc_attrs = objc_analysis['objc_attributes']
        assert len(objc_attrs) > 0, "Should find @objc attributes"
        
        # Test search functionality
        search_results = list(plugin.search("Circle"))
        print(f"Search results for 'Circle': {len(search_results)}")
        assert len(search_results) > 0, "Should find search results for 'Circle'"
        
        # Test semantic search for protocol conformance
        protocol_results = list(plugin.search("protocol:Drawable", {'semantic': True}))
        print(f"Protocol conformance search results: {len(protocol_results)}")
        
        # Test property wrapper search
        wrapper_results = list(plugin.search("@State", {'semantic': True}))
        print(f"Property wrapper search results: {len(wrapper_results)}")
        
        print("✅ All Swift plugin tests passed!")
        
    finally:
        # Cleanup
        temp_file.unlink()


def test_swift_package_analysis():
    """Test Swift Package Manager integration."""
    package_swift_content = """
// swift-tools-version:5.5
import PackageDescription

let package = Package(
    name: "MySwiftPackage",
    platforms: [
        .iOS(.v14),
        .macOS(.v11)
    ],
    products: [
        .library(
            name: "MySwiftPackage",
            targets: ["MySwiftPackage"]),
    ],
    dependencies: [
        .package(url: "https://github.com/Alamofire/Alamofire.git", from: "5.6.0"),
        .package(url: "https://github.com/apple/swift-nio.git", from: "2.40.0"),
    ],
    targets: [
        .target(
            name: "MySwiftPackage",
            dependencies: ["Alamofire", "NIO"]),
        .testTarget(
            name: "MySwiftPackageTests",
            dependencies: ["MySwiftPackage"]),
    ]
)
"""
    
    # Create a temporary Package.swift file
    import tempfile
    import os
    temp_dir = tempfile.mkdtemp()
    package_file = Path(temp_dir) / "Package.swift"
    package_file.write_text(package_swift_content)
    
    try:
        plugin = Plugin()
        
        # Test Swift package analysis
        modules = plugin.module_analyzer.analyze_swift_package(package_file)
        print(f"Found modules: {list(modules.keys())}")
        
        assert 'MySwiftPackage' in modules, "Should find main target"
        assert 'MySwiftPackageTests' in modules, "Should find test target"
        
        # Test build system integration
        build_system = plugin.build_system
        dependencies = build_system.parse_build_file(package_file)
        print(f"Found dependencies: {[dep.name for dep in dependencies]}")
        
        dep_names = [dep.name for dep in dependencies]
        assert 'Alamofire' in dep_names, "Should find Alamofire dependency"
        assert 'swift-nio' in dep_names, "Should find swift-nio dependency"
        
        # Test project structure
        structure = build_system.get_project_structure()
        print(f"Project structure: {structure}")
        
        assert structure['type'] == 'swift_package', "Should identify as Swift package"
        
        print("✅ Swift Package Manager tests passed!")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("Testing Swift plugin...")
    test_swift_plugin_basic()
    test_swift_package_analysis()
    print("All tests completed successfully! 🎉")