#!/usr/bin/env python3
"""Comprehensive demonstration of Java plugin features."""

import tempfile
import shutil
from pathlib import Path
from mcp_server.plugins.java_plugin import Plugin
from mcp_server.storage.sqlite_store import SQLiteStore


def create_sample_project(project_root: Path):
    """Create a sample Java project with various features."""
    
    # Create directory structure
    (project_root / "src/main/java/com/example/app").mkdir(parents=True)
    (project_root / "src/main/java/com/example/service").mkdir(parents=True)
    (project_root / "src/main/java/com/example/model").mkdir(parents=True)
    (project_root / "src/test/java/com/example/app").mkdir(parents=True)
    
    # Create Maven POM
    pom = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>demo-app</artifactId>
    <version>1.0.0</version>
    
    <properties>
        <spring.version>5.3.20</spring.version>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-core</artifactId>
            <version>${spring.version}</version>
        </dependency>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>"""
    (project_root / "pom.xml").write_text(pom)
    
    # Create model classes
    (project_root / "src/main/java/com/example/model/Entity.java").write_text("""
package com.example.model;

/**
 * Base entity interface with generic ID type.
 */
public interface Entity<ID> {
    ID getId();
    void setId(ID id);
}
""")
    
    (project_root / "src/main/java/com/example/model/User.java").write_text("""
package com.example.model;

import java.util.List;
import java.util.ArrayList;

/**
 * User entity implementing the Entity interface.
 */
public class User implements Entity<Long> {
    private Long id;
    private String username;
    private String email;
    private List<String> roles;
    
    public User(String username, String email) {
        this.username = username;
        this.email = email;
        this.roles = new ArrayList<>();
    }
    
    @Override
    public Long getId() {
        return id;
    }
    
    @Override
    public void setId(Long id) {
        this.id = id;
    }
    
    public String getUsername() {
        return username;
    }
    
    public String getEmail() {
        return email;
    }
    
    public List<String> getRoles() {
        return new ArrayList<>(roles);
    }
    
    public void addRole(String role) {
        roles.add(role);
    }
}
""")
    
    # Create service interfaces and implementations
    (project_root / "src/main/java/com/example/service/Repository.java").write_text("""
package com.example.service;

import com.example.model.Entity;
import java.util.List;
import java.util.Optional;

/**
 * Generic repository interface.
 */
public interface Repository<T extends Entity<ID>, ID> {
    T save(T entity);
    Optional<T> findById(ID id);
    List<T> findAll();
    void delete(T entity);
    void deleteById(ID id);
}
""")
    
    (project_root / "src/main/java/com/example/service/UserRepository.java").write_text("""
package com.example.service;

import com.example.model.User;

/**
 * User-specific repository interface.
 */
public interface UserRepository extends Repository<User, Long> {
    User findByUsername(String username);
    User findByEmail(String email);
}
""")
    
    (project_root / "src/main/java/com/example/service/UserRepositoryImpl.java").write_text("""
package com.example.service;

import com.example.model.User;
import java.util.*;

/**
 * In-memory implementation of UserRepository.
 */
public class UserRepositoryImpl implements UserRepository {
    private final Map<Long, User> storage = new HashMap<>();
    private final Map<String, User> usernameIndex = new HashMap<>();
    private final Map<String, User> emailIndex = new HashMap<>();
    private Long nextId = 1L;
    
    @Override
    public User save(User entity) {
        if (entity.getId() == null) {
            entity.setId(nextId++);
        }
        storage.put(entity.getId(), entity);
        usernameIndex.put(entity.getUsername(), entity);
        emailIndex.put(entity.getEmail(), entity);
        return entity;
    }
    
    @Override
    public Optional<User> findById(Long id) {
        return Optional.ofNullable(storage.get(id));
    }
    
    @Override
    public List<User> findAll() {
        return new ArrayList<>(storage.values());
    }
    
    @Override
    public void delete(User entity) {
        deleteById(entity.getId());
    }
    
    @Override
    public void deleteById(Long id) {
        User user = storage.remove(id);
        if (user != null) {
            usernameIndex.remove(user.getUsername());
            emailIndex.remove(user.getEmail());
        }
    }
    
    @Override
    public User findByUsername(String username) {
        return usernameIndex.get(username);
    }
    
    @Override
    public User findByEmail(String email) {
        return emailIndex.get(email);
    }
}
""")
    
    # Create application class
    (project_root / "src/main/java/com/example/app/Application.java").write_text("""
package com.example.app;

import com.example.model.User;
import com.example.service.UserRepository;
import com.example.service.UserRepositoryImpl;
import java.util.List;

/**
 * Main application demonstrating the repository pattern.
 */
public class Application {
    private final UserRepository userRepository;
    
    public Application() {
        this.userRepository = new UserRepositoryImpl();
    }
    
    public void run() {
        // Create users
        User admin = new User("admin", "admin@example.com");
        admin.addRole("ADMIN");
        admin.addRole("USER");
        
        User user = new User("john", "john@example.com");
        user.addRole("USER");
        
        // Save users
        userRepository.save(admin);
        userRepository.save(user);
        
        // Find users
        User found = userRepository.findByUsername("admin");
        System.out.println("Found user: " + found.getUsername());
        
        // List all users
        List<User> allUsers = userRepository.findAll();
        System.out.println("Total users: " + allUsers.size());
    }
    
    public static void main(String[] args) {
        Application app = new Application();
        app.run();
    }
}
""")
    
    # Create test class
    (project_root / "src/test/java/com/example/app/UserRepositoryTest.java").write_text("""
package com.example.app;

import com.example.model.User;
import com.example.service.UserRepository;
import com.example.service.UserRepositoryImpl;
import org.junit.Test;
import org.junit.Before;
import static org.junit.Assert.*;

public class UserRepositoryTest {
    private UserRepository repository;
    
    @Before
    public void setUp() {
        repository = new UserRepositoryImpl();
    }
    
    @Test
    public void testSaveAndFind() {
        User user = new User("test", "test@example.com");
        User saved = repository.save(user);
        
        assertNotNull(saved.getId());
        assertEquals(user.getUsername(), saved.getUsername());
        
        User found = repository.findByUsername("test");
        assertNotNull(found);
        assertEquals(saved.getId(), found.getId());
    }
    
    @Test
    public void testDelete() {
        User user = new User("delete", "delete@example.com");
        repository.save(user);
        
        repository.delete(user);
        
        assertNull(repository.findByUsername("delete"));
    }
}
""")


def demonstrate_java_plugin():
    """Demonstrate all Java plugin features."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        create_sample_project(project_root)
        
        # Change to project directory
        import os
        original_dir = os.getcwd()
        os.chdir(project_root)
        
        try:
            print("=== Java Plugin Feature Demonstration ===\n")
            
            # Initialize plugin with SQLite store
            db_path = project_root / "code_index.db"
            sqlite_store = SQLiteStore(str(db_path))
            plugin = Plugin(sqlite_store=sqlite_store, enable_semantic=False)
            
            print("1. Build System Integration")
            print("-" * 40)
            deps = plugin.get_project_dependencies()
            print(f"Found {len(deps)} dependencies:")
            for dep in deps:
                print(f"  - {dep.group_id}:{dep.name}:{dep.version}")
                print(f"    Dev dependency: {dep.is_dev_dependency}")
            
            structure = plugin.build_system.get_project_structure()
            print(f"\nProject structure:")
            print(f"  Build system: {structure['build_system']}")
            print(f"  Source dirs: {structure['source_dirs']}")
            print(f"  Test dirs: {structure['test_dirs']}")
            
            print("\n2. Type Analysis")
            print("-" * 40)
            # Get type information for generic interface
            type_info = plugin.type_analyzer.get_type_info("Repository", "")
            if type_info:
                print(f"Repository interface:")
                print(f"  Generic: {type_info.is_generic}")
                print(f"  Type params: {type_info.generic_params}")
            
            # Find implementations
            impls = plugin.type_analyzer.find_implementations("UserRepository")
            print(f"\nImplementations of UserRepository: {len(impls)}")
            
            # Check inheritance
            is_sub = plugin.type_analyzer.is_subtype_of("UserRepositoryImpl", "Repository")
            print(f"UserRepositoryImpl is subtype of Repository: {is_sub}")
            
            print("\n3. Import Analysis")
            print("-" * 40)
            # Analyze imports in Application.java
            app_path = Path("src/main/java/com/example/app/Application.java")
            imports = plugin.analyze_imports(app_path)
            print(f"Imports in Application.java: {len(imports)}")
            for imp in imports[:3]:  # Show first 3
                print(f"  - {imp.module_path}")
            
            # Get import graph
            import_graph = plugin.import_resolver.get_import_graph()
            print(f"\nImport graph has {len(import_graph)} nodes")
            
            # Check for circular dependencies
            cycles = plugin.import_resolver.find_circular_dependencies()
            print(f"Circular dependencies found: {len(cycles)}")
            
            print("\n4. Symbol Search and Definition")
            print("-" * 40)
            # Search for User class
            results = list(plugin.search("User"))
            print(f"Search for 'User' returned {len(results)} results")
            
            # Get definition
            definition = plugin.getDefinition("User")
            if definition:
                print(f"\nUser class definition:")
                print(f"  Kind: {definition.get('kind')}")
                print(f"  File: {definition.get('defined_in')}")
                print(f"  Line: {definition.get('line')}")
                
                if 'java_info' in definition:
                    print(f"  Access: {definition['java_info']['access']}")
            
            print("\n5. Cross-File References")
            print("-" * 40)
            # Find references to Entity interface
            refs = list(plugin.findReferences("Entity"))
            print(f"Found {len(refs)} references to Entity interface")
            
            # Get class hierarchy
            hierarchy = plugin.get_class_hierarchy("UserRepositoryImpl")
            print(f"\nClass hierarchy for UserRepositoryImpl:")
            print(f"  Implements: {hierarchy['implements']}")
            print(f"  Extended by: {hierarchy['extended_by']}")
            
            # Impact analysis
            repo_file = "src/main/java/com/example/service/Repository.java"
            impact = plugin.cross_file_analyzer.analyze_impact(repo_file)
            print(f"\nImpact of changing Repository.java:")
            print(f"  Direct dependents: {len(impact['direct_dependents'])}")
            print(f"  Affected tests: {len(impact['affected_tests'])}")
            
            print("\n6. Package Structure")
            print("-" * 40)
            packages = plugin.get_package_structure()
            print(f"Found {len(packages)} packages:")
            for pkg, files in sorted(packages.items()):
                print(f"  - {pkg}: {len(files)} files")
            
            print("\n7. Method Call Graph")
            print("-" * 40)
            call_graph = plugin.cross_file_analyzer.get_call_graph("run")
            print(f"Call graph for 'run' method:")
            for method, calls in call_graph.items():
                if calls:
                    print(f"  {method} calls: {', '.join(calls)}")
            
            print("\n✅ All features demonstrated successfully!")
            
        finally:
            os.chdir(original_dir)


if __name__ == "__main__":
    print("Java Plugin Feature Demonstration")
    print("=" * 50)
    demonstrate_java_plugin()