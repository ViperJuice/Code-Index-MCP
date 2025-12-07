#!/usr/bin/env python3
"""Test script for the Go plugin functionality."""
import os
import shutil
import tempfile
from pathlib import Path

from mcp_server.plugins.go_plugin import Plugin as GoPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


def create_test_go_project():
    """Create a test Go project structure."""
    # Create temporary directory
    test_dir = tempfile.mkdtemp(prefix="go_test_")
    os.chdir(test_dir)

    # Create go.mod
    go_mod = """module github.com/example/testproject

go 1.21

require (
    github.com/gorilla/mux v1.8.0
    github.com/stretchr/testify v1.8.0
)

replace github.com/example/internal => ./internal
"""
    Path("go.mod").write_text(go_mod)

    # Create main.go
    main_go = """package main

import (
    "fmt"
    "log"
    "net/http"
    
    "github.com/gorilla/mux"
    "github.com/example/testproject/internal/handlers"
)

// Server represents the HTTP server
type Server struct {
    router *mux.Router
    port   string
}

// NewServer creates a new server instance
func NewServer(port string) *Server {
    return &Server{
        router: mux.NewRouter(),
        port:   port,
    }
}

// Start starts the HTTP server
func (s *Server) Start() error {
    s.setupRoutes()
    log.Printf("Server starting on port %s", s.port)
    return http.ListenAndServe(":"+s.port, s.router)
}

// setupRoutes configures the server routes
func (s *Server) setupRoutes() {
    s.router.HandleFunc("/", handlers.HomeHandler).Methods("GET")
    s.router.HandleFunc("/api/users", handlers.UsersHandler).Methods("GET")
}

func main() {
    server := NewServer("8080")
    if err := server.Start(); err != nil {
        log.Fatal(err)
    }
}
"""
    Path("main.go").write_text(main_go)

    # Create internal/handlers directory
    os.makedirs("internal/handlers", exist_ok=True)

    # Create handlers.go
    handlers_go = """package handlers

import (
    "encoding/json"
    "net/http"
)

// User represents a user in the system
type User struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
}

// UserService defines the interface for user operations
type UserService interface {
    GetUsers() ([]User, error)
    GetUser(id int) (*User, error)
}

// Handler wraps the UserService
type Handler struct {
    service UserService
}

// HomeHandler handles the home route
func HomeHandler(w http.ResponseWriter, r *http.Request) {
    w.Write([]byte("Welcome to the API"))
}

// UsersHandler handles the users route
func UsersHandler(w http.ResponseWriter, r *http.Request) {
    users := []User{
        {ID: 1, Name: "Alice"},
        {ID: 2, Name: "Bob"},
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(users)
}

// NewHandler creates a new handler with the given service
func NewHandler(service UserService) *Handler {
    return &Handler{service: service}
}
"""
    Path("internal/handlers/handlers.go").write_text(handlers_go)

    # Create service.go
    service_go = """package handlers

import "errors"

// memoryService is an in-memory implementation of UserService
type memoryService struct {
    users []User
}

// NewMemoryService creates a new in-memory user service
func NewMemoryService() UserService {
    return &memoryService{
        users: []User{
            {ID: 1, Name: "Alice"},
            {ID: 2, Name: "Bob"},
            {ID: 3, Name: "Charlie"},
        },
    }
}

// GetUsers returns all users
func (s *memoryService) GetUsers() ([]User, error) {
    return s.users, nil
}

// GetUser returns a user by ID
func (s *memoryService) GetUser(id int) (*User, error) {
    for _, user := range s.users {
        if user.ID == id {
            return &user, nil
        }
    }
    return nil, errors.New("user not found")
}
"""
    Path("internal/handlers/service.go").write_text(service_go)

    return test_dir


def test_go_plugin():
    """Test the Go plugin functionality."""
    print("Creating test Go project...")
    test_dir = create_test_go_project()

    try:
        # Initialize SQLite store
        sqlite_store = SQLiteStore(":memory:")

        # Create Go plugin
        print("\nInitializing Go plugin...")
        plugin = GoPlugin(sqlite_store=sqlite_store, enable_semantic=False)

        # Test 1: Module resolution
        print("\n1. Testing module resolution...")
        module_info = plugin.get_module_info()
        if module_info:
            print(f"   Module: {module_info['name']}")
            print(f"   Go version: {module_info['version']}")
            print(f"   Dependencies: {len(module_info['dependencies'])}")
            for dep in module_info["dependencies"]:
                print(f"     - {dep['module']} {dep['version']}")
            if module_info["replacements"]:
                print("   Replacements:")
                for old, new in module_info["replacements"].items():
                    print(f"     - {old} => {new}")

        # Test 2: Index files
        print("\n2. Indexing Go files...")
        go_files = list(Path(".").rglob("*.go"))
        for go_file in go_files:
            content = go_file.read_text()
            shard = plugin.indexFile(go_file, content)
            print(f"   Indexed {go_file}: {len(shard['symbols'])} symbols")
            for symbol in shard["symbols"][:3]:  # Show first 3 symbols
                print(f"     - {symbol['kind']}: {symbol['symbol']} (line {symbol['line']})")

        # Test 3: Package analysis
        print("\n3. Testing package analysis...")
        package_info = plugin.get_package_info(str(Path("internal/handlers")))
        if package_info:
            print(f"   Package: {package_info['name']}")
            print(f"   Imports: {len(package_info['imports'])}")
            print(f"   Types: {package_info['types']}")
            print(f"   Functions: {package_info['functions']}")
            print(f"   Interfaces: {package_info['interfaces']}")

        # Test 4: Interface satisfaction
        print("\n4. Testing interface satisfaction...")
        result = plugin.check_interface_implementation("memoryService", "UserService")
        if result:
            print(f"   Type: {result['type']}")
            print(f"   Interface: {result['interface']}")
            print(f"   Satisfied: {result['satisfied']}")
            if result["implemented_methods"]:
                print(f"   Implemented methods: {result['implemented_methods']}")
            if result["missing_methods"]:
                print(f"   Missing methods: {result['missing_methods']}")

        # Test 5: Symbol definition
        print("\n5. Testing symbol definition lookup...")
        symbols_to_find = ["Server", "UserService", "NewServer"]
        for symbol in symbols_to_find:
            definition = plugin.getDefinition(symbol)
            if definition:
                print(f"   {symbol}:")
                print(f"     Kind: {definition['kind']}")
                print(f"     File: {definition['defined_in']}")
                print(f"     Line: {definition['line']}")
                print(f"     Signature: {definition['signature']}")

        # Test 6: Find references
        print("\n6. Testing reference finding...")
        refs = plugin.findReferences("User")
        print(f"   Found {len(refs)} references to 'User'")
        for ref in refs[:5]:  # Show first 5
            print(f"     - {ref.file}:{ref.line}")

        # Test 7: Search functionality
        print("\n7. Testing search...")
        search_results = list(plugin.search("Handler", {"limit": 5}))
        print(f"   Found {len(search_results)} results for 'Handler'")
        for result in search_results:
            print(f"     - {result['file']}:{result['line']}")
            print(f"       {result['snippet'][:80]}...")

        print("\n✅ All tests completed successfully!")

    finally:
        # Cleanup
        os.chdir("/")
        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")


if __name__ == "__main__":
    test_go_plugin()
