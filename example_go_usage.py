#!/usr/bin/env python3
"""Example usage of the Go plugin."""

from mcp_server.plugins.go_plugin import Plugin as GoPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


def main():
    # Initialize the Go plugin with SQLite storage
    sqlite_store = SQLiteStore(":memory:")
    go_plugin = GoPlugin(sqlite_store=sqlite_store, enable_semantic=False)  # Disable semantic for now
    
    # Example Go code to analyze
    go_code = """
package main

import (
    "context"
    "fmt"
    "io"
)

// Handler defines the interface for request handlers
type Handler interface {
    Handle(ctx context.Context, req Request) Response
}

// Request represents an incoming request
type Request struct {
    Method  string
    Path    string
    Headers map[string]string
    Body    io.Reader
}

// Response represents the handler response
type Response struct {
    StatusCode int
    Headers    map[string]string
    Body       []byte
}

// LoggingHandler implements Handler with logging
type LoggingHandler struct {
    next Handler
}

// NewLoggingHandler creates a new logging handler
func NewLoggingHandler(next Handler) *LoggingHandler {
    return &LoggingHandler{next: next}
}

// Handle processes the request with logging
func (h *LoggingHandler) Handle(ctx context.Context, req Request) Response {
    fmt.Printf("Handling request: %s %s\\n", req.Method, req.Path)
    resp := h.next.Handle(ctx, req)
    fmt.Printf("Response status: %d\\n", resp.StatusCode)
    return resp
}

// SimpleHandler is a basic implementation
type SimpleHandler struct{}

// Handle processes the request
func (s *SimpleHandler) Handle(ctx context.Context, req Request) Response {
    return Response{
        StatusCode: 200,
        Headers:    map[string]string{"Content-Type": "text/plain"},
        Body:       []byte("OK"),
    }
}

func main() {
    handler := NewLoggingHandler(&SimpleHandler{})
    
    req := Request{
        Method: "GET",
        Path:   "/hello",
    }
    
    resp := handler.Handle(context.Background(), req)
    fmt.Printf("Final response: %s\\n", string(resp.Body))
}
"""
    
    # Index the code
    print("Indexing Go code...")
    shard = go_plugin.indexFile("example.go", go_code)
    
    print(f"\nFound {len(shard['symbols'])} symbols:")
    for symbol in shard['symbols']:
        print(f"  - {symbol['kind']}: {symbol['symbol']} (line {symbol['line']})")
        if 'metadata' in symbol and 'implements' in symbol['metadata']:
            print(f"    Implements: {symbol['metadata']['implements']}")
    
    # Check interface implementations
    print("\n\nInterface Implementation Analysis:")
    
    # This would work if we had proper package context
    result = go_plugin.check_interface_implementation("LoggingHandler", "Handler")
    if result:
        print(f"\nLoggingHandler implements Handler: {result['satisfied']}")
        if result['implemented_methods']:
            print(f"Implemented methods: {result['implemented_methods']}")
    
    result = go_plugin.check_interface_implementation("SimpleHandler", "Handler")
    if result:
        print(f"\nSimpleHandler implements Handler: {result['satisfied']}")
        if result['implemented_methods']:
            print(f"Implemented methods: {result['implemented_methods']}")
    
    # Find symbol definitions
    print("\n\nSymbol Definitions:")
    for symbol_name in ["Handler", "LoggingHandler", "NewLoggingHandler"]:
        definition = go_plugin.getDefinition(symbol_name)
        if definition:
            print(f"\n{symbol_name}:")
            print(f"  Type: {definition['kind']}")
            print(f"  Signature: {definition['signature']}")
    
    # Search for references
    print("\n\nReferences to 'Handler':")
    refs = go_plugin.findReferences("Handler")
    for ref in refs[:5]:  # Show first 5
        print(f"  - Line {ref.line}")
    
    # Traditional search
    print("\n\nSearch results for 'Handle':")
    results = list(go_plugin.search("Handle", {"limit": 5}))
    for result in results:
        print(f"  - Line {result['line']}: {result['snippet'].strip()}")
    
    # Module info (if in a real project)
    module_info = go_plugin.get_module_info()
    if module_info:
        print(f"\n\nModule Information:")
        print(f"  Name: {module_info['name']}")
        print(f"  Go Version: {module_info['version']}")


if __name__ == "__main__":
    main()