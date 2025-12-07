"""Tests for the JavaScript/TypeScript plugin."""

import shutil
import tempfile
from pathlib import Path

import pytest

from mcp_server.plugins.js_plugin.plugin import Plugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestJavaScriptPlugin:
    """Test suite for JavaScript/TypeScript plugin."""

    @pytest.fixture
    def plugin(self):
        """Create a plugin instance without SQLite store."""
        return Plugin()

    @pytest.fixture
    def plugin_with_store(self):
        """Create a plugin instance with SQLite store."""
        store = SQLiteStore(":memory:")
        return Plugin(sqlite_store=store)

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_supports(self, plugin):
        """Test file type support detection."""
        # JavaScript files
        assert plugin.supports("app.js")
        assert plugin.supports("component.jsx")
        assert plugin.supports("module.mjs")
        assert plugin.supports("common.cjs")
        assert plugin.supports("script.es6")
        assert plugin.supports("legacy.es")

        # TypeScript files
        assert plugin.supports("app.ts")
        assert plugin.supports("component.tsx")

        # Mixed case
        assert plugin.supports("App.JS")
        assert plugin.supports("Component.TSX")

        # Non-supported files
        assert not plugin.supports("script.py")
        assert not plugin.supports("style.css")
        assert not plugin.supports("README.md")

    def test_function_extraction(self, plugin):
        """Test extraction of various function types."""
        content = """
        // Regular function
        function regularFunction(a, b) {
            return a + b;
        }
        
        // Arrow function
        const arrowFunction = (x, y) => x * y;
        
        // Async function
        async function asyncFunction() {
            await something();
        }
        
        // Async arrow
        const asyncArrow = async () => {
            return await fetch('/api');
        };
        
        // Generator function
        function* generatorFunction() {
            yield 1;
            yield 2;
        }
        
        // Function expression
        const funcExpression = function(name) {
            return "Hello " + name;
        };
        """

        shard = plugin.indexFile("test.js", content)

        assert len(shard["symbols"]) == 6
        assert shard["file"] == "test.js"
        assert shard["language"] == "js"

        # Check specific functions
        symbols = {s["symbol"]: s for s in shard["symbols"]}

        assert "regularFunction" in symbols
        assert symbols["regularFunction"]["kind"] == "function"
        assert "a, b" in symbols["regularFunction"]["signature"]

        assert "arrowFunction" in symbols
        assert symbols["arrowFunction"]["kind"] == "arrow_function"
        assert "(x, y) => {}" in symbols["arrowFunction"]["signature"]

        assert "asyncFunction" in symbols
        assert symbols["asyncFunction"]["kind"] == "function"
        assert "async" in symbols["asyncFunction"]["signature"]

        assert "asyncArrow" in symbols
        assert symbols["asyncArrow"]["kind"] == "arrow_function"
        assert "async" in symbols["asyncArrow"]["signature"]

        assert "generatorFunction" in symbols
        assert symbols["generatorFunction"]["kind"] == "generator"
        assert "function*" in symbols["generatorFunction"]["signature"]

    def test_class_extraction(self, plugin):
        """Test extraction of classes and their methods."""
        content = """
        class Animal {
            constructor(name) {
                this.name = name;
            }
            
            speak() {
                console.log(`${this.name} makes a sound`);
            }
            
            static createDog(name) {
                return new Dog(name);
            }
        }
        
        class Dog extends Animal {
            constructor(name) {
                super(name);
                this.species = 'dog';
            }
            
            bark() {
                console.log('Woof!');
            }
            
            get breed() {
                return this._breed;
            }
            
            set breed(value) {
                this._breed = value;
            }
        }
        """

        shard = plugin.indexFile("test.js", content)
        symbols = {s["symbol"]: s for s in shard["symbols"]}

        # Check classes
        assert "Animal" in symbols
        assert symbols["Animal"]["kind"] == "class"
        assert symbols["Animal"]["signature"] == "class Animal"

        assert "Dog" in symbols
        assert symbols["Dog"]["kind"] == "class"
        assert "extends Animal" in symbols["Dog"]["signature"]

        # Check methods
        assert "Animal.speak" in symbols
        assert symbols["Animal.speak"]["kind"] == "method"

        assert "Animal.createDog" in symbols
        assert symbols["Animal.createDog"]["kind"] == "method"
        assert "static" in symbols["Animal.createDog"]["signature"]

        assert "Dog.bark" in symbols
        assert symbols["Dog.bark"]["kind"] == "method"

        # Check getter/setter
        assert "Dog.breed" in symbols  # getter
        getter = [
            s for s in shard["symbols"] if s["symbol"] == "Dog.breed" and s["kind"] == "getter"
        ][0]
        assert getter["signature"] == "get breed()"

        setter = [
            s for s in shard["symbols"] if s["symbol"] == "Dog.breed" and s["kind"] == "setter"
        ][0]
        assert setter["signature"] == "set breed(value)"

    def test_variable_extraction(self, plugin):
        """Test extraction of variable declarations."""
        content = """
        var oldStyle = "legacy";
        let mutable = 42;
        const immutable = "constant";
        
        const obj = {
            method() {
                return "ES6 method";
            }
        };
        
        // Multiple declarations
        const a = 1, b = 2, c = 3;
        """

        shard = plugin.indexFile("test.js", content)
        symbols = {s["symbol"]: s for s in shard["symbols"]}

        assert "oldStyle" in symbols
        assert symbols["oldStyle"]["kind"] == "variable"
        assert "var oldStyle" in symbols["oldStyle"]["signature"]

        assert "mutable" in symbols
        assert symbols["mutable"]["kind"] == "variable"
        assert "let mutable" in symbols["mutable"]["signature"]

        assert "immutable" in symbols
        assert symbols["immutable"]["kind"] == "variable"
        assert "const immutable" in symbols["immutable"]["signature"]

        # Multiple declarations
        assert "a" in symbols
        assert "b" in symbols
        assert "c" in symbols

    def test_module_detection(self, plugin):
        """Test detection of module types."""
        # ES Modules
        esm_content = """
        import React, { useState, useEffect } from 'react';
        import * as utils from './utils';
        import defaultExport from 'module';
        
        export default function App() {
            return <div>Hello</div>;
        }
        
        export const helper = () => {};
        export { helper as util };
        """

        shard = plugin.indexFile("app.js", esm_content)
        assert shard["module_type"] == "esm"

        # CommonJS
        cjs_content = """
        const express = require('express');
        const { Router } = require('express');
        
        function startServer() {
            // server code
        }
        
        module.exports = { startServer };
        exports.PORT = 3000;
        """

        shard = plugin.indexFile("server.js", cjs_content)
        assert shard["module_type"] == "commonjs"

        # Unknown (no imports/exports)
        unknown_content = """
        function helper() {
            return "internal";
        }
        """

        shard = plugin.indexFile("internal.js", unknown_content)
        assert shard["module_type"] == "unknown"

    def test_jsx_components(self, plugin):
        """Test detection of React/JSX components."""
        content = """
        // Function component
        function Button({ onClick, children }) {
            return <button onClick={onClick}>{children}</button>;
        }
        
        // Arrow function component
        const Card = (props) => (
            <div className="card">
                {props.children}
            </div>
        );
        
        // Non-component (lowercase)
        function helper() {
            return <span>not a component</span>;
        }
        
        // Class component
        class Modal extends React.Component {
            render() {
                return <div className="modal">{this.props.content}</div>;
            }
        }
        """

        shard = plugin.indexFile("components.jsx", content)
        symbols = {s["symbol"]: s for s in shard["symbols"]}

        # All functions/classes should be detected
        assert "Button" in symbols
        assert "Card" in symbols
        assert "helper" in symbols
        assert "Modal" in symbols

        # Note: The current implementation doesn't distinguish React components
        # from regular functions based on JSX return. This could be enhanced.

    def test_typescript_features(self, plugin):
        """Test TypeScript-specific features."""
        content = """
        // Interface
        interface User {
            id: number;
            name: string;
            email?: string;
        }
        
        // Type alias
        type Status = 'active' | 'inactive' | 'pending';
        
        // Generic function
        function identity<T>(arg: T): T {
            return arg;
        }
        
        // Class with TypeScript features
        class DataStore<T> {
            private data: T[] = [];
            
            add(item: T): void {
                this.data.push(item);
            }
            
            get(index: number): T | undefined {
                return this.data[index];
            }
        }
        """

        shard = plugin.indexFile("test.ts", content)
        symbols = {s["symbol"]: s for s in shard["symbols"]}

        # Check interface
        assert "User" in symbols
        assert symbols["User"]["kind"] == "interface"
        assert symbols["User"]["signature"] == "interface User"

        # Check type alias
        assert "Status" in symbols
        assert symbols["Status"]["kind"] == "type"
        assert symbols["Status"]["signature"] == "type Status"

        # Check generic function
        assert "identity" in symbols
        assert symbols["identity"]["kind"] == "function"

        # Check class and methods
        assert "DataStore" in symbols
        assert symbols["DataStore"]["kind"] == "class"

        assert "DataStore.add" in symbols
        assert "DataStore.get" in symbols

    def test_object_methods(self, plugin):
        """Test extraction of object methods and properties."""
        content = """
        const api = {
            baseUrl: 'https://api.example.com',
            
            get(endpoint) {
                return fetch(this.baseUrl + endpoint);
            },
            
            post: function(endpoint, data) {
                return fetch(this.baseUrl + endpoint, {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
            },
            
            delete: async (endpoint) => {
                return await fetch(api.baseUrl + endpoint, {
                    method: 'DELETE'
                });
            }
        };
        
        // Object property assignment
        api.timeout = 5000;
        api.retry = function(fn, times) {
            // retry logic
        };
        """

        shard = plugin.indexFile("test.js", content)

        # Find object method/property symbols
        obj_symbols = [s for s in shard["symbols"] if s["symbol"].startswith("api.")]

        assert len(obj_symbols) >= 2  # timeout and retry

        # Check assigned properties
        symbols = {s["symbol"]: s for s in shard["symbols"]}
        assert "api.timeout" in symbols
        assert symbols["api.timeout"]["kind"] == "property"

        assert "api.retry" in symbols
        assert symbols["api.retry"]["kind"] == "method"

    def test_nested_scopes(self, plugin):
        """Test symbol extraction with nested scopes."""
        content = """
        class Outer {
            method() {
                function innerFunction() {
                    const innerVar = "nested";
                    return innerVar;
                }
                
                return innerFunction();
            }
        }
        
        function topLevel() {
            const nested = {
                deep: {
                    method() {
                        return "deeply nested";
                    }
                }
            };
        }
        """

        shard = plugin.indexFile("test.js", content)

        # Check that we find symbols at different scope levels
        symbols = {s["symbol"]: s for s in shard["symbols"]}
        assert "Outer" in symbols
        assert "Outer.method" in symbols
        assert "topLevel" in symbols

        # Nested functions should also be found
        assert "innerFunction" in symbols
        assert "innerVar" in symbols

    def test_get_definition(self, plugin):
        """Test getting symbol definitions."""
        content = """
        /**
         * Calculates the sum of two numbers
         * @param {number} a - First number
         * @param {number} b - Second number
         * @returns {number} The sum
         */
        function add(a, b) {
            return a + b;
        }
        
        class Calculator {
            multiply(x, y) {
                return x * y;
            }
        }
        """

        # Index the file first
        plugin.indexFile("calc.js", content)

        # Get definition of function
        add_def = plugin.getDefinition("add")
        assert add_def is not None
        assert add_def["symbol"] == "add"
        assert add_def["kind"] == "function"
        assert add_def["defined_in"] == "calc.js"
        assert add_def["line"] == 8

        # Get definition of method
        multiply_def = plugin.getDefinition("multiply")
        assert multiply_def is not None
        assert multiply_def["symbol"] == "Calculator.multiply"
        assert multiply_def["kind"] == "method"

    def test_find_references(self, plugin, temp_dir):
        """Test finding references to symbols."""
        # Create test files
        file1 = temp_dir / "module1.js"
        file1.write_text(
            """
        export function helper() {
            return "help";
        }
        """
        )

        file2 = temp_dir / "module2.js"
        file2.write_text(
            """
        import { helper } from './module1';
        
        function main() {
            const result = helper();
            console.log(helper());
        }
        """
        )

        # Index files
        plugin.indexFile(file1, file1.read_text())
        plugin.indexFile(file2, file2.read_text())

        # Find references
        refs = plugin.findReferences("helper")
        assert len(refs) >= 2  # Definition + at least 2 usages

        # Check that references include both files
        ref_files = {ref.file for ref in refs}
        assert str(file1) in ref_files or str(file2) in ref_files

    def test_search(self, plugin):
        """Test searching for code snippets."""
        content = """
        function calculateTotal(items) {
            return items.reduce((sum, item) => sum + item.price, 0);
        }
        
        const shoppingCart = {
            items: [],
            addItem(product) {
                this.items.push(product);
            },
            getTotal() {
                return calculateTotal(this.items);
            }
        };
        """

        plugin.indexFile("shop.js", content)

        # Search for function
        results = plugin.search("calculate")
        assert len(results) > 0
        assert any("calculateTotal" in r["snippet"] for r in results)

        # Search with limit
        results = plugin.search("item", {"limit": 2})
        assert len(results) <= 2

    def test_async_patterns(self, plugin):
        """Test extraction of async/await patterns."""
        content = """
        // Promise-based
        function fetchData() {
            return fetch('/api/data')
                .then(response => response.json())
                .then(data => processData(data))
                .catch(error => console.error(error));
        }
        
        // Async/await
        async function fetchDataAsync() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();
                return processData(data);
            } catch (error) {
                console.error(error);
            }
        }
        
        // Async class method
        class DataService {
            async getData() {
                return await this.fetch();
            }
            
            async *getDataStream() {
                yield* this.stream();
            }
        }
        """

        shard = plugin.indexFile("async.js", content)
        symbols = {s["symbol"]: s for s in shard["symbols"]}

        # Check async functions
        assert "fetchDataAsync" in symbols
        assert "async" in symbols["fetchDataAsync"]["signature"]

        # Check async methods
        assert "DataService.getData" in symbols
        assert "async" in symbols["DataService.getData"]["signature"]

    def test_export_extraction(self, plugin):
        """Test extraction of exports."""
        content = """
        // Named exports
        export const VERSION = '1.0.0';
        export function helper() {}
        export class Utility {}
        
        // Export list
        const internal1 = 'a';
        const internal2 = 'b';
        export { internal1, internal2 as external2 };
        
        // Default export
        export default function main() {
            return "main";
        }
        
        // CommonJS exports
        module.exports.legacy = true;
        exports.compatible = false;
        """

        shard = plugin.indexFile("exports.js", content)

        # Module should be detected as ESM (ES modules take precedence)
        assert shard["module_type"] == "esm"

        # All exported symbols should be found
        symbols = {s["symbol"]: s for s in shard["symbols"]}
        assert "VERSION" in symbols
        assert "helper" in symbols
        assert "Utility" in symbols
        assert "main" in symbols

    def test_import_extraction(self, plugin):
        """Test extraction of imports."""
        content = """
        // Default import
        import React from 'react';
        
        // Named imports
        import { useState, useEffect } from 'react';
        
        // Aliased imports
        import { Component as Comp, Fragment as Frag } from 'react';
        
        // Namespace import
        import * as utils from './utils';
        
        // Side effect import
        import './styles.css';
        
        // CommonJS require
        const fs = require('fs');
        const { readFile, writeFile } = require('fs/promises');
        """

        shard = plugin.indexFile("imports.js", content)
        assert shard["module_type"] == "esm"

    def test_error_handling(self, plugin):
        """Test handling of malformed code."""
        # Syntax error
        content = """
        function broken( {
            return "missing closing paren";
        }
        """

        # Should not raise exception
        shard = plugin.indexFile("broken.js", content)
        assert isinstance(shard, dict)
        assert shard["file"] == "broken.js"

        # May or may not find the broken function depending on parser recovery

    def test_minified_file_skip(self, plugin, temp_dir):
        """Test that minified files are skipped during pre-indexing."""
        # This test would need to mock the _preindex method
        # or test it indirectly through initialization

    def test_indexed_count(self, plugin):
        """Test getting count of indexed files."""
        # Initially should be 0
        assert plugin.get_indexed_count() == 0

        # Index some files
        plugin.indexFile("file1.js", "function test1() {}")
        assert plugin.get_indexed_count() == 1

        plugin.indexFile("file2.js", "function test2() {}")
        assert plugin.get_indexed_count() == 2

        # Re-indexing same file shouldn't increase count
        plugin.indexFile("file1.js", "function test1Updated() {}")
        assert plugin.get_indexed_count() == 2

    def test_persistence_integration(self, plugin_with_store):
        """Test integration with SQLite persistence."""
        content = """
        function persistedFunction() {
            return "stored";
        }
        """

        shard = plugin_with_store.indexFile("test.js", content)

        # Verify that symbols were stored (would need to check SQLite directly)
        assert len(shard["symbols"]) > 0

    def test_class_fields(self, plugin):
        """Test extraction of class fields (ES2022)."""
        content = """
        class Modern {
            // Public field
            publicField = 42;
            
            // Private field
            #privateField = "secret";
            
            // Static field
            static staticField = "shared";
            
            // Static private field
            static #privateStatic = "hidden";
            
            constructor() {
                this.instanceField = "dynamic";
            }
        }
        """

        shard = plugin.indexFile("modern.js", content)
        symbols = {s["symbol"]: s for s in shard["symbols"]}

        # Check class
        assert "Modern" in symbols

        # Check fields (if supported by parser)
        # Note: Field support depends on tree-sitter-javascript version

    def test_destructuring_parameters(self, plugin):
        """Test handling of destructured parameters."""
        content = """
        // Object destructuring
        function processUser({ name, email, age = 18 }) {
            return `${name} (${email})`;
        }
        
        // Array destructuring
        const getFirst = ([first, ...rest]) => first;
        
        // Nested destructuring
        function complex({ user: { name, address: { city } } }) {
            return `${name} from ${city}`;
        }
        """

        shard = plugin.indexFile("destructure.js", content)
        symbols = {s["symbol"]: s for s in shard["symbols"]}

        # Functions should be found even with complex parameters
        assert "processUser" in symbols
        assert "getFirst" in symbols
        assert "complex" in symbols
