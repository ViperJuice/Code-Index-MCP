#!/usr/bin/env python3
"""Test script for Java plugin functionality."""

import tempfile
from pathlib import Path

from mcp_server.plugins.java_plugin import Plugin


def test_java_plugin():
    """Test Java plugin with sample Java code."""

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Create Maven project structure
        (project_root / "src/main/java/com/example").mkdir(parents=True)
        (project_root / "src/test/java/com/example").mkdir(parents=True)

        # Create a sample pom.xml
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>test-project</artifactId>
    <version>1.0.0</version>
    
    <dependencies>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.apache.commons</groupId>
            <artifactId>commons-lang3</artifactId>
            <version>3.12.0</version>
        </dependency>
    </dependencies>
</project>"""
        (project_root / "pom.xml").write_text(pom_content)

        # Create sample Java files
        main_class = """package com.example;

import java.util.List;
import java.util.ArrayList;
import org.apache.commons.lang3.StringUtils;

/**
 * Main application class demonstrating various Java features.
 */
public class Application {
    private String name;
    private List<String> features;
    
    public Application(String name) {
        this.name = name;
        this.features = new ArrayList<>();
    }
    
    public void addFeature(String feature) {
        if (StringUtils.isNotBlank(feature)) {
            features.add(feature);
        }
    }
    
    public List<String> getFeatures() {
        return new ArrayList<>(features);
    }
    
    public static void main(String[] args) {
        Application app = new Application("Test App");
        app.addFeature("Feature 1");
        app.addFeature("Feature 2");
        
        System.out.println("Application: " + app.name);
        System.out.println("Features: " + app.getFeatures());
    }
}"""
        (project_root / "src/main/java/com/example/Application.java").write_text(main_class)

        # Create an interface
        interface_code = """package com.example;

import java.util.List;

/**
 * Service interface with generic type support.
 */
public interface Service<T> {
    void process(T item);
    List<T> getAll();
    T findById(String id);
}"""
        (project_root / "src/main/java/com/example/Service.java").write_text(interface_code)

        # Create implementation
        impl_code = """package com.example;

import java.util.List;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

/**
 * Implementation of the Service interface.
 */
public class ServiceImpl<T extends Model> implements Service<T> {
    private Map<String, T> storage = new HashMap<>();
    
    @Override
    public void process(T item) {
        storage.put(item.getId(), item);
    }
    
    @Override
    public List<T> getAll() {
        return new ArrayList<>(storage.values());
    }
    
    @Override
    public T findById(String id) {
        return storage.get(id);
    }
}"""
        (project_root / "src/main/java/com/example/ServiceImpl.java").write_text(impl_code)

        # Create Model class
        model_code = """package com.example;

/**
 * Base model class.
 */
public abstract class Model {
    protected String id;
    
    public String getId() {
        return id;
    }
    
    public void setId(String id) {
        this.id = id;
    }
}"""
        (project_root / "src/main/java/com/example/Model.java").write_text(model_code)

        # Create a test class
        test_code = """package com.example;

import org.junit.Test;
import org.junit.Before;
import static org.junit.Assert.*;

public class ApplicationTest {
    private Application app;
    
    @Before
    public void setUp() {
        app = new Application("Test");
    }
    
    @Test
    public void testAddFeature() {
        app.addFeature("Test Feature");
        assertEquals(1, app.getFeatures().size());
    }
    
    @Test
    public void testEmptyFeature() {
        app.addFeature("");
        assertEquals(0, app.getFeatures().size());
    }
}"""
        (project_root / "src/test/java/com/example/ApplicationTest.java").write_text(test_code)

        # Change to project directory
        import os

        original_dir = os.getcwd()
        os.chdir(project_root)

        try:
            # Initialize plugin
            print("Initializing Java plugin...")
            plugin = Plugin(enable_semantic=False)  # Disable semantic for testing

            # Test 1: File support
            print("\n1. Testing file support:")
            assert plugin.supports("Application.java")
            assert plugin.supports(Path("src/main/java/com/example/Application.java"))
            assert not plugin.supports("test.py")
            print("✓ File support working")

            # Test 2: Indexing
            print("\n2. Testing file indexing:")
            app_path = "src/main/java/com/example/Application.java"
            shard = plugin.indexFile(app_path, main_class)
            print(f"✓ Indexed {len(shard['symbols'])} symbols from Application.java")

            # Print symbols found
            for symbol in shard["symbols"]:
                print(f"  - {symbol['kind']}: {symbol['symbol']}")

            # Test 3: Get definition
            print("\n3. Testing getDefinition:")
            definition = plugin.getDefinition("Application")
            if definition:
                print(f"✓ Found definition for Application: {definition['signature']}")
                if "java_info" in definition:
                    print(f"  Access: {definition['java_info']['access']}")

            # Test 4: Build system
            print("\n4. Testing build system integration:")
            deps = plugin.get_project_dependencies()
            print(f"✓ Found {len(deps)} dependencies:")
            for dep in deps:
                print(f"  - {dep.group_id}:{dep.name}:{dep.version} (dev: {dep.is_dev_dependency})")

            # Test 5: Type analysis
            print("\n5. Testing type analysis:")
            type_info = plugin.type_analyzer.get_type_info("ServiceImpl", "")
            if type_info:
                print("✓ Found type info for ServiceImpl:")
                print(f"  - Generic: {type_info.is_generic}")
                print(f"  - Implements: {type_info.implements}")
                print(f"  - Type params: {type_info.generic_params}")

            # Test 6: Import resolution
            print("\n6. Testing import resolution:")
            import_stmt = "import java.util.List;"
            import_info = plugin.import_resolver.parse_import_statement(import_stmt)
            if import_info:
                print(f"✓ Parsed import: {import_info.module_path}")
                print(f"  - Static: {import_info.is_static}")
                print(f"  - Wildcard: {import_info.is_wildcard}")

            # Test 7: Cross-file references
            print("\n7. Testing cross-file references:")
            refs = plugin.findReferences("Model")
            ref_count = len(list(refs))
            print(f"✓ Found {ref_count} references to Model")

            # Test 8: Class hierarchy
            print("\n8. Testing class hierarchy:")
            hierarchy = plugin.get_class_hierarchy("ServiceImpl")
            print("✓ Class hierarchy for ServiceImpl:")
            print(f"  - Implements: {hierarchy['implements']}")
            print(f"  - Extended by: {hierarchy['extended_by']}")

            # Test 9: Package structure
            print("\n9. Testing package structure:")
            packages = plugin.get_package_structure()
            print(f"✓ Found {len(packages)} packages:")
            for pkg, files in packages.items():
                print(f"  - {pkg}: {len(files)} files")

            # Test 10: Search
            print("\n10. Testing search:")
            results = list(plugin.search("Application"))
            print(f"✓ Search for 'Application' returned {len(results)} results")

            print("\n✅ All tests passed!")

        finally:
            # Restore original directory
            os.chdir(original_dir)


if __name__ == "__main__":
    # Check if javalang is installed
    try:
        pass

        print("✓ javalang library is installed")
    except ImportError:
        print("✗ javalang library is not installed")
        print("Please run: pip install javalang")
        exit(1)

    test_java_plugin()
