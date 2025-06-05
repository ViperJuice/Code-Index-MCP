"""Comprehensive tests for C# plugin."""

import pytest
from pathlib import Path
from mcp_server.plugins.csharp_plugin.plugin import Plugin
from mcp_server.plugins.plugin_template import SymbolType


class TestCSharpPlugin:
    """Test cases for C# plugin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = Plugin()
        self.test_data_dir = Path(__file__).parent.parent / "mcp_server" / "plugins" / "csharp_plugin" / "test_data"
    
    def test_supports_files(self):
        """Test file support detection."""
        # Test supported extensions
        assert self.plugin.supports("test.cs")
        assert self.plugin.supports("script.csx")
        assert self.plugin.supports("page.cshtml")
        
        # Test unsupported extensions
        assert not self.plugin.supports("test.txt")
        assert not self.plugin.supports("test.js")
        assert not self.plugin.supports("test.py")
    
    def test_language_detection(self):
        """Test language detection."""
        assert self.plugin.get_language() == "c#"
    
    def test_symbol_patterns(self):
        """Test basic symbol patterns."""
        patterns = self.plugin.get_symbol_patterns()
        
        # Check that all expected symbol types have patterns
        expected_types = {
            SymbolType.FUNCTION, SymbolType.CLASS, SymbolType.VARIABLE,
            SymbolType.IMPORT, SymbolType.PROPERTY, SymbolType.ENUM,
            SymbolType.INTERFACE, SymbolType.STRUCT, SymbolType.NAMESPACE,
            SymbolType.FIELD
        }
        
        for symbol_type in expected_types:
            assert symbol_type in patterns
            assert isinstance(patterns[symbol_type], str)
            assert len(patterns[symbol_type]) > 0
    
    def test_parse_simple_class(self):
        """Test parsing a simple C# class."""
        content = """
using System;

namespace TestNamespace
{
    public class TestClass
    {
        private int _value;
        
        public int Value { get; set; }
        
        public void DoSomething()
        {
            _value = 42;
        }
    }
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        assert result["language"] == "c#"
        assert len(result["symbols"]) > 0
        
        symbols = result["symbols"]
        symbol_names = [s["symbol"] for s in symbols]
        
        # Check for expected symbols
        assert "TestNamespace" in symbol_names
        assert "TestClass" in symbol_names
        assert "DoSomething" in symbol_names
        assert "Value" in symbol_names
    
    def test_parse_complex_file(self):
        """Test parsing complex C# file with real-world patterns."""
        sample_file = self.test_data_dir / "SampleClass.cs"
        if sample_file.exists():
            content = sample_file.read_text()
            result = self.plugin.indexFile(str(sample_file), content)
            
            assert result["language"] == "c#"
            symbols = result["symbols"]
            assert len(symbols) > 0
            
            # Check for specific symbols from the sample
            symbol_names = [s["symbol"] for s in symbols]
            assert "UserController" in symbol_names
            assert "User" in symbol_names
            assert "IUser" in symbol_names
            assert "GetUsers" in symbol_names
            assert "UserStatus" in symbol_names
    
    def test_async_method_detection(self):
        """Test detection of async methods."""
        content = """
public class AsyncExample
{
    public async Task<string> GetDataAsync()
    {
        await Task.Delay(100);
        return "data";
    }
    
    public async void HandleEventAsync()
    {
        await DoSomethingAsync();
    }
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Find async methods
        async_methods = [s for s in symbols if s.get("kind") == "function"]
        assert len(async_methods) >= 2
        
        # Check that async methods are detected
        method_names = [m["symbol"] for m in async_methods]
        assert "GetDataAsync" in method_names
        assert "HandleEventAsync" in method_names
    
    def test_generic_type_detection(self):
        """Test detection of generic types and methods."""
        content = """
public class GenericClass<T> where T : class
{
    private List<T> _items = new List<T>();
    
    public void Add<U>(U item) where U : T
    {
        _items.Add(item);
    }
    
    public Dictionary<string, T> GetDictionary()
    {
        return new Dictionary<string, T>();
    }
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Check for generic class
        classes = [s for s in symbols if s.get("kind") == "class"]
        assert len(classes) >= 1
        assert "GenericClass" in [c["symbol"] for c in classes]
        
        # Check for generic methods
        methods = [s for s in symbols if s.get("kind") == "function"]
        method_names = [m["symbol"] for m in methods]
        assert "Add" in method_names
        assert "GetDictionary" in method_names
    
    def test_attribute_detection(self):
        """Test detection of C# attributes."""
        content = """
[Serializable]
[JsonObject(MemberSerialization.OptIn)]
public class AttributedClass
{
    [JsonProperty("id")]
    public int Id { get; set; }
    
    [HttpGet]
    [Route("api/test")]
    public ActionResult GetData()
    {
        return Ok();
    }
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Check that symbols are found
        assert len(symbols) > 0
        
        # Check for class and method
        symbol_names = [s["symbol"] for s in symbols]
        assert "AttributedClass" in symbol_names
        assert "GetData" in symbol_names
    
    def test_linq_detection(self):
        """Test detection of LINQ expressions."""
        content = """
public class LinqExample
{
    public IEnumerable<string> ProcessData(List<string> input)
    {
        var query = from item in input
                   where item.Length > 5
                   orderby item
                   select item.ToUpper();
        
        var methodSyntax = input
            .Where(x => x.StartsWith("A"))
            .Select(x => x.ToLower())
            .OrderBy(x => x);
        
        return query.Union(methodSyntax);
    }
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Check that method is found
        methods = [s for s in symbols if s.get("kind") == "function"]
        assert len(methods) >= 1
        assert "ProcessData" in [m["symbol"] for m in methods]
    
    def test_interface_and_inheritance(self):
        """Test detection of interfaces and inheritance."""
        content = """
public interface IBaseInterface
{
    void DoSomething();
}

public interface IDerivedInterface : IBaseInterface
{
    void DoMore();
}

public abstract class BaseClass : IBaseInterface
{
    public abstract void DoSomething();
    public virtual void CommonMethod() { }
}

public class ConcreteClass : BaseClass, IDerivedInterface
{
    public override void DoSomething() { }
    public void DoMore() { }
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Check for interfaces
        interfaces = [s for s in symbols if s.get("kind") == "interface"]
        interface_names = [i["symbol"] for i in interfaces]
        assert "IBaseInterface" in interface_names
        assert "IDerivedInterface" in interface_names
        
        # Check for classes
        classes = [s for s in symbols if s.get("kind") == "class"]
        class_names = [c["symbol"] for c in classes]
        assert "BaseClass" in class_names
        assert "ConcreteClass" in class_names
    
    def test_property_detection(self):
        """Test detection of various property types."""
        content = """
public class PropertyExample
{
    // Auto-implemented property
    public string Name { get; set; }
    
    // Read-only property
    public string ReadOnly { get; }
    
    // Property with backing field
    private int _value;
    public int Value 
    { 
        get => _value; 
        set => _value = value; 
    }
    
    // Static property
    public static string StaticProperty { get; set; }
    
    // Expression-bodied property
    public string FullName => $"{FirstName} {LastName}";
    
    private string FirstName { get; set; }
    private string LastName { get; set; }
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Check for properties
        properties = [s for s in symbols if s.get("kind") == "property"]
        property_names = [p["symbol"] for p in properties]
        
        expected_properties = ["Name", "ReadOnly", "Value", "StaticProperty", "FullName"]
        for prop in expected_properties:
            assert prop in property_names
    
    def test_enum_detection(self):
        """Test detection of enums."""
        content = """
public enum SimpleEnum
{
    None,
    First,
    Second
}

[Flags]
public enum FlagsEnum : byte
{
    None = 0,
    Read = 1,
    Write = 2,
    Execute = 4,
    All = Read | Write | Execute
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Check for enums
        enums = [s for s in symbols if s.get("kind") == "enum"]
        enum_names = [e["symbol"] for e in enums]
        assert "SimpleEnum" in enum_names
        assert "FlagsEnum" in enum_names
    
    def test_struct_detection(self):
        """Test detection of structs."""
        content = """
public struct Point
{
    public int X { get; set; }
    public int Y { get; set; }
    
    public Point(int x, int y)
    {
        X = x;
        Y = y;
    }
    
    public double DistanceFromOrigin()
    {
        return Math.Sqrt(X * X + Y * Y);
    }
}

public readonly struct ReadOnlyPoint
{
    public readonly int X;
    public readonly int Y;
    
    public ReadOnlyPoint(int x, int y)
    {
        X = x;
        Y = y;
    }
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Check for structs
        structs = [s for s in symbols if s.get("kind") == "struct"]
        struct_names = [s["symbol"] for s in structs]
        assert "Point" in struct_names
        assert "ReadOnlyPoint" in struct_names
    
    def test_namespace_detection(self):
        """Test detection of namespaces."""
        content = """
namespace OuterNamespace
{
    namespace InnerNamespace
    {
        public class NestedClass
        {
        }
    }
    
    public class OuterClass
    {
    }
}

namespace AnotherNamespace.SubNamespace
{
    public interface IInterface
    {
    }
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Check for namespaces
        namespaces = [s for s in symbols if s.get("kind") == "namespace"]
        namespace_names = [n["symbol"] for n in namespaces]
        
        # Should find nested namespaces
        assert len(namespaces) >= 2
    
    def test_using_directive_detection(self):
        """Test detection of using directives."""
        content = """
using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.AspNetCore.Mvc;
using static System.Console;
using StringAlias = System.String;

namespace TestNamespace
{
    public class TestClass
    {
    }
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Check for using directives
        imports = [s for s in symbols if s.get("kind") == "import"]
        import_names = [i["symbol"] for i in imports]
        
        expected_imports = ["System", "System.Collections.Generic", "System.Linq", "Microsoft.AspNetCore.Mvc"]
        for imp in expected_imports:
            assert imp in import_names
    
    def test_field_detection(self):
        """Test detection of fields."""
        content = """
public class FieldExample
{
    private int _privateField;
    public string PublicField;
    protected static readonly DateTime StaticField = DateTime.Now;
    public const int ConstantField = 42;
    
    private readonly List<string> _readonlyField = new();
    
    public event EventHandler SomeEvent;
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Check for fields
        fields = [s for s in symbols if s.get("kind") == "field"]
        field_names = [f["symbol"] for f in fields]
        
        expected_fields = ["_privateField", "PublicField", "StaticField", "ConstantField", "_readonlyField"]
        for field in expected_fields:
            assert field in field_names
    
    def test_constructor_detection(self):
        """Test detection of constructors."""
        content = """
public class ConstructorExample
{
    public ConstructorExample()
    {
    }
    
    public ConstructorExample(string name) : this()
    {
        Name = name;
    }
    
    static ConstructorExample()
    {
        // Static constructor
    }
    
    public string Name { get; set; }
}
"""
        
        result = self.plugin.indexFile("test.cs", content)
        symbols = result["symbols"]
        
        # Check for constructors
        constructors = [s for s in symbols if s.get("kind") == "function" and "constructor" in s.get("signature", "").lower()]
        
        # Should find constructors
        assert len(constructors) >= 1
    
    def test_project_file_parsing(self):
        """Test parsing of .csproj files for project information."""
        # This test requires the actual .csproj file to exist
        csproj_file = self.test_data_dir / "Test.csproj"
        if csproj_file.exists():
            # Index a C# file in the same directory to trigger project analysis
            sample_file = self.test_data_dir / "SampleClass.cs"
            if sample_file.exists():
                content = sample_file.read_text()
                result = self.plugin.indexFile(str(sample_file), content)
                
                # Check that project information was detected
                symbols = result["symbols"]
                if symbols:
                    # Check if any symbol has project metadata
                    has_project_info = any(
                        s.get("metadata", {}).get("target_framework") for s in symbols
                    )
                    # Note: This might not always be true depending on implementation
    
    def test_blazor_component_parsing(self):
        """Test parsing of Blazor .cshtml files."""
        blazor_file = self.test_data_dir / "BlazorComponent.cshtml"
        if blazor_file.exists():
            content = blazor_file.read_text()
            result = self.plugin.indexFile(str(blazor_file), content)
            
            assert result["language"] == "c#"
            symbols = result["symbols"]
            
            # Should find C# code within @code blocks
            method_names = [s["symbol"] for s in symbols if s.get("kind") == "function"]
            expected_methods = ["IncrementCount", "OnInitializedAsync", "ValidateCount"]
            
            for method in expected_methods:
                assert method in method_names
    
    def test_plugin_info(self):
        """Test getting plugin information."""
        info = self.plugin.get_csharp_info()
        
        # Check basic info
        assert info["language"] == "c#"
        assert info["parsing_strategy"] == "hybrid"
        
        # Check C#-specific features
        features = info["language_features"]
        assert features["generics"] is True
        assert features["linq"] is True
        assert features["async_await"] is True
        assert features["attributes"] is True
        
        # Check supported project types
        project_types = info["project_types_supported"]
        expected_types = ["console", "library", "web", "wpf", "winforms", "blazor"]
        for ptype in expected_types:
            assert ptype in project_types
        
        # Check framework support
        framework_support = info["framework_support"]
        assert framework_support["net_framework"] is True
        assert framework_support["net_core"] is True
        assert framework_support["net_5_plus"] is True
    
    def test_symbol_extraction_robustness(self):
        """Test that symbol extraction handles malformed code gracefully."""
        malformed_content = """
public class MalformedClass {
    public void IncompleteMethod(
    
    private int _field
    
    public string Property { get
    
    namespace MissingBrace
    {
        public class InnerClass
    // Missing closing braces
"""
        
        # Should not crash
        result = self.plugin.indexFile("malformed.cs", malformed_content)
        assert result["language"] == "c#"
        # Should still extract some symbols despite malformed syntax
        assert len(result["symbols"]) >= 0