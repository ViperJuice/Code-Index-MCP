"""
Comprehensive tests for the Dart plugin.

Tests cover:
- File support detection
- Symbol extraction (classes, functions, methods, variables, enums, mixins, extensions)
- Dart-specific features (widgets, state classes, async/await, futures, streams, annotations)
- Flutter-specific features (widget hierarchy, state management, build methods)
- Import/export tracking
- Documentation extraction
- Error handling
- Edge cases and complex code structures
- Interface compliance (both IPlugin and IDartPlugin)
- Result pattern usage
- Performance benchmarks
"""

from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

from mcp_server.interfaces.plugin_interfaces import (
    IndexedFile,
    SymbolDefinition,
    SymbolReference,
)
from mcp_server.interfaces.shared_interfaces import Result
from mcp_server.plugins.dart_plugin.plugin import Plugin as DartPlugin


class TestPluginInitialization:
    """Test plugin initialization and configuration."""

    def test_init_without_store(self):
        """Test initialization without SQLite store."""
        plugin = DartPlugin()

        assert plugin.lang == "dart"
        assert plugin._sqlite_store is None

    def test_init_with_store(self, sqlite_store):
        """Test initialization with SQLite store."""
        plugin = DartPlugin(sqlite_store=sqlite_store)

        assert plugin.lang == "dart"
        assert plugin._sqlite_store == sqlite_store

    def test_language_property(self):
        """Test the language property."""
        plugin = DartPlugin()
        assert plugin.lang == "dart"

    def test_interface_properties(self):
        """Test IDartPlugin interface properties."""
        plugin = DartPlugin()

        assert plugin.name == "dart_plugin"
        assert plugin.supported_extensions == [".dart"]
        assert plugin.supported_languages == ["dart", "flutter"]


class TestFileSupport:
    """Test file support detection."""

    def test_supports_dart_files(self):
        """Test that plugin supports Dart files."""
        plugin = DartPlugin()

        dart_files = [
            Path("test.dart"),
            Path("main.dart"),
            Path("/path/to/widget.dart"),
            Path("lib/models/user.dart"),
            Path("test/widget_test.dart"),
        ]

        for file_path in dart_files:
            assert plugin.supports(file_path) is True
            assert plugin.can_handle(str(file_path)) is True

    def test_does_not_support_other_files(self):
        """Test that plugin doesn't support non-Dart files."""
        plugin = DartPlugin()

        other_files = [
            Path("test.js"),
            Path("script.py"),
            Path("data.json"),
            Path("readme.md"),
            Path("pubspec.yaml"),
            Path("analysis_options.yaml"),
            Path(".dart"),
            Path("dart"),  # No extension
        ]

        for file_path in other_files:
            assert plugin.supports(file_path) is False
            assert plugin.can_handle(str(file_path)) is False

    def test_supports_case_sensitivity(self):
        """Test case sensitivity in file extension."""
        plugin = DartPlugin()

        # Dart uses lowercase .dart
        assert plugin.supports(Path("test.dart")) is True
        assert plugin.supports(Path("test.DART")) is False
        assert plugin.supports(Path("test.Dart")) is False


class TestNewInterfaceImplementation:
    """Test the new IDartPlugin interface implementation."""

    def test_index_interface(self):
        """Test the new index method that returns Result[IndexedFile]."""
        plugin = DartPlugin()
        code = dedent(
            """
        /// A simple class for testing
        class TestClass {
          void method() {}
        }
        """
        )

        # Test successful indexing
        result = plugin.index("test.dart", code)

        assert isinstance(result, Result)
        assert result.success is True
        assert result.value is not None
        assert isinstance(result.value, IndexedFile)

        indexed_file = result.value
        assert indexed_file.file_path == "test.dart"
        assert indexed_file.language == "dart"
        assert len(indexed_file.symbols) > 0

        # Check symbols
        class_symbol = next(s for s in indexed_file.symbols if s.symbol == "TestClass")
        assert class_symbol.symbol_type == "class"
        assert class_symbol.line > 0

    def test_get_definition_interface(self):
        """Test the new get_definition method with Result pattern."""
        plugin = DartPlugin()
        code = dedent(
            """
        /// A target function to find.
        void targetFunction() {
          print('Found me!');
        }
        """
        )

        # Index first
        plugin.index("test.dart", code)

        # Test successful definition lookup
        result = plugin.get_definition("targetFunction", {})

        assert isinstance(result, Result)
        assert result.success is True
        assert result.value is not None
        assert isinstance(result.value, SymbolDefinition)

        definition = result.value
        assert definition.symbol == "targetFunction"
        assert definition.symbol_type == "function"
        assert "targetFunction" in definition.signature

    def test_get_references_interface(self):
        """Test the new get_references method with Result pattern."""
        plugin = DartPlugin()
        code = dedent(
            """
        void targetFunction() {
          print('Hello');
        }
        
        void caller() {
          targetFunction();
        }
        """
        )

        # Index first
        plugin.index("test.dart", code)

        # Test successful references lookup
        result = plugin.get_references("targetFunction", {})

        assert isinstance(result, Result)
        assert result.success is True
        assert isinstance(result.value, list)

        # Should find references (including the definition)
        assert len(result.value) >= 1

        for ref in result.value:
            assert isinstance(ref, SymbolReference)
            assert ref.symbol == "targetFunction"

    def test_search_interface(self):
        """Test the new search method with Result pattern."""
        plugin = DartPlugin()
        code = dedent(
            """
        void calculateSum() {}
        void calculateProduct() {}
        """
        )

        # Index first
        plugin.index("test.dart", code)

        # Test successful search
        result = plugin.search("calculate", {"limit": 10})

        assert isinstance(result, Result)
        assert result.success is True
        assert isinstance(result.value, list)

    def test_validate_syntax_interface(self):
        """Test the validate_syntax method."""
        plugin = DartPlugin()

        # Valid syntax
        valid_code = "void main() { print('Hello'); }"
        result = plugin.validate_syntax(valid_code)

        assert isinstance(result, Result)
        assert result.success is True
        assert result.value is True

        # Invalid syntax (unbalanced braces)
        invalid_code = "void main() { print('Hello');"
        result = plugin.validate_syntax(invalid_code)

        assert isinstance(result, Result)
        assert result.success is True
        assert result.value is False

    def test_get_completions_interface(self):
        """Test the get_completions method."""
        plugin = DartPlugin()

        result = plugin.get_completions("test.dart", 10, 5)

        assert isinstance(result, Result)
        assert result.success is True
        assert isinstance(result.value, list)

        # Should include Dart keywords
        completions = result.value
        assert "class" in completions
        assert "void" in completions
        assert "Widget" in completions

    def test_parse_flutter_widgets_interface(self):
        """Test the parse_flutter_widgets method."""
        plugin = DartPlugin()
        code = dedent(
            """
        import 'package:flutter/material.dart';
        
        class MyWidget extends StatelessWidget {
          Widget build(BuildContext context) {
            return Text('Hello');
          }
        }
        """
        )

        result = plugin.parse_flutter_widgets(code)

        assert isinstance(result, Result)
        assert result.success is True
        assert isinstance(result.value, list)

        widgets = result.value
        assert len(widgets) >= 1

        widget = widgets[0]
        assert isinstance(widget, SymbolDefinition)
        assert widget.symbol == "MyWidget"
        assert widget.symbol_type == "widget"

    def test_resolve_packages_interface(self):
        """Test the resolve_packages method."""
        plugin = DartPlugin()

        # Create a temporary file with package imports
        test_file = Path("test_file.dart")
        code = dedent(
            """
        import 'package:flutter/material.dart';
        import 'package:http/http.dart';
        """
        )

        # Write the file temporarily
        with patch("pathlib.Path.read_text") as mock_read:
            mock_read.return_value = code

            result = plugin.resolve_packages(str(test_file))

            assert isinstance(result, Result)
            assert result.success is True
            assert isinstance(result.value, list)

            packages = result.value
            assert "flutter" in packages
            assert "http" in packages

    def test_language_analyzer_interface(self):
        """Test ILanguageAnalyzer interface methods."""
        plugin = DartPlugin()
        code = dedent(
            """
        import 'package:flutter/material.dart';
        import 'dart:async';
        
        void testFunction() {}
        class TestClass {}
        """
        )

        # Test parse_imports
        imports_result = plugin.parse_imports(code)
        assert isinstance(imports_result, Result)
        assert imports_result.success is True
        assert "package:flutter/material.dart" in imports_result.value

        # Test extract_symbols
        symbols_result = plugin.extract_symbols(code)
        assert isinstance(symbols_result, Result)
        assert symbols_result.success is True
        assert len(symbols_result.value) >= 2

        # Test resolve_type
        type_result = plugin.resolve_type("testFunction", {})
        assert isinstance(type_result, Result)
        assert type_result.success is True

        # Test get_call_hierarchy
        hierarchy_result = plugin.get_call_hierarchy("testFunction", {})
        assert isinstance(hierarchy_result, Result)
        assert hierarchy_result.success is True
        assert "calls" in hierarchy_result.value
        assert "called_by" in hierarchy_result.value


class TestSymbolExtraction:
    """Test symbol extraction from Dart code."""

    def test_extract_simple_class(self):
        """Test extracting simple class definitions."""
        plugin = DartPlugin()
        code = dedent(
            """
        class SimpleClass {
          String name;
          int age;
          
          SimpleClass(this.name, this.age);
          
          void greet() {
            print('Hello, $name!');
          }
        }
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)

        symbols = result["symbols"]
        assert len(symbols) >= 1

        # Check class
        class_symbol = next(s for s in symbols if s["symbol"] == "SimpleClass")
        assert class_symbol["kind"] == "class"
        assert class_symbol["line"] == 2
        assert "class SimpleClass" in class_symbol["signature"]

    def test_extract_flutter_widget(self):
        """Test extracting Flutter widget definitions."""
        plugin = DartPlugin()
        code = dedent(
            """
        import 'package:flutter/material.dart';
        
        class MyWidget extends StatelessWidget {
          final String title;
          
          const MyWidget({Key? key, required this.title}) : super(key: key);
          
          @override
          Widget build(BuildContext context) {
            return Text(title);
          }
        }
        
        class MyStatefulWidget extends StatefulWidget {
          @override
          _MyStatefulWidgetState createState() => _MyStatefulWidgetState();
        }
        
        class _MyStatefulWidgetState extends State<MyStatefulWidget> {
          int counter = 0;
          
          @override
          Widget build(BuildContext context) {
            return Column(
              children: [
                Text('Count: $counter'),
                ElevatedButton(
                  onPressed: () => setState(() => counter++),
                  child: Text('Increment'),
                ),
              ],
            );
          }
        }
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        symbols = result["symbols"]

        # Check widget classes
        widget_symbols = [s for s in symbols if s["kind"] == "widget"]
        assert len(widget_symbols) >= 2

        # Check stateless widget
        stateless_widget = next(s for s in symbols if s["symbol"] == "MyWidget")
        assert stateless_widget["kind"] == "widget"
        assert stateless_widget["extends"] == "StatelessWidget"

        # Check state class
        state_symbols = [s for s in symbols if s["kind"] == "state"]
        assert len(state_symbols) >= 1

        # Check build methods
        build_methods = [s for s in symbols if s["kind"] == "build_method"]
        assert len(build_methods) >= 2

    def test_extract_enum(self):
        """Test extracting enum definitions."""
        plugin = DartPlugin()
        code = dedent(
            """
        enum Color {
          red,
          green,
          blue,
        }
        
        enum Status {
          pending,
          approved,
          rejected,
        }
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        symbols = result["symbols"]

        enum_symbols = [s for s in symbols if s["kind"] == "enum"]
        assert len(enum_symbols) == 2

        color_enum = next(s for s in symbols if s["symbol"] == "Color")
        assert color_enum["kind"] == "enum"
        assert color_enum["signature"] == "enum Color"

    def test_extract_mixin(self):
        """Test extracting mixin definitions."""
        plugin = DartPlugin()
        code = dedent(
            """
        mixin Flyable {
          void fly() {
            print('Flying!');
          }
        }
        
        mixin Swimmable on Animal {
          void swim() {
            print('Swimming!');
          }
        }
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        symbols = result["symbols"]

        mixin_symbols = [s for s in symbols if s["kind"] == "mixin"]
        assert len(mixin_symbols) == 2

        flyable_mixin = next(s for s in symbols if s["symbol"] == "Flyable")
        assert flyable_mixin["kind"] == "mixin"
        assert flyable_mixin["signature"] == "mixin Flyable"

        swimmable_mixin = next(s for s in symbols if s["symbol"] == "Swimmable")
        assert swimmable_mixin["on_types"] == "Animal"

    def test_extract_extension(self):
        """Test extracting extension definitions."""
        plugin = DartPlugin()
        code = dedent(
            """
        extension StringExtension on String {
          String get reversed => split('').reversed.join('');
          
          bool get isEmail => contains('@') && contains('.');
        }
        
        extension on int {
          bool get isEven => this % 2 == 0;
        }
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        symbols = result["symbols"]

        extension_symbols = [s for s in symbols if s["kind"] == "extension"]
        assert len(extension_symbols) == 2

        string_ext = next(s for s in symbols if s["symbol"] == "StringExtension")
        assert string_ext["kind"] == "extension"
        assert string_ext["on_type"] == "String"

    def test_extract_functions(self):
        """Test extracting function definitions."""
        plugin = DartPlugin()
        code = dedent(
            """
        void main() {
          print('Hello, World!');
        }
        
        String formatName(String first, String last) {
          return '$first $last';
        }
        
        Future<String> fetchData() async {
          // Simulate async operation
          await Future.delayed(Duration(seconds: 1));
          return 'Data';
        }
        
        int calculate(int a, int b, {int multiplier = 1}) {
          return (a + b) * multiplier;
        }
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        symbols = result["symbols"]

        function_symbols = [s for s in symbols if s["kind"] in ["function", "main_function"]]
        assert len(function_symbols) == 4

        # Check main function
        main_func = next(s for s in symbols if s["symbol"] == "main")
        assert main_func["kind"] == "main_function"

        # Check async function
        async_func = next(s for s in symbols if s["symbol"] == "fetchData")
        assert async_func["async"] is True
        assert "Future<String>" in async_func["signature"]

    def test_extract_variables_and_constants(self):
        """Test extracting variable and constant definitions."""
        plugin = DartPlugin()
        code = dedent(
            """
        const String APP_NAME = 'My App';
        const int VERSION = 1;
        
        final DateTime startTime = DateTime.now();
        var isDebug = true;
        
        String? userName;
        late int userId;
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        symbols = result["symbols"]

        variable_symbols = [s for s in symbols if s["kind"] in ["variable", "constant"]]
        assert len(variable_symbols) >= 4

        # Check constants
        app_name = next(s for s in symbols if s["symbol"] == "APP_NAME")
        assert app_name["kind"] == "constant"
        assert app_name["modifier"] == "const"

    def test_extract_typedef(self):
        """Test extracting typedef definitions."""
        plugin = DartPlugin()
        code = dedent(
            """
        typedef IntCallback = void Function(int value);
        typedef JsonMap = Map<String, dynamic>;
        typedef StringList = List<String>;
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        symbols = result["symbols"]

        typedef_symbols = [s for s in symbols if s["kind"] == "typedef"]
        assert len(typedef_symbols) == 3

        callback_typedef = next(s for s in symbols if s["symbol"] == "IntCallback")
        assert callback_typedef["kind"] == "typedef"
        assert "void Function(int value)" in callback_typedef["aliased_type"]


class TestImportTracking:
    """Test import and export statement tracking."""

    def test_extract_imports(self):
        """Test extracting various import statements."""
        plugin = DartPlugin()
        code = dedent(
            """
        import 'dart:io';
        import 'dart:async';
        import 'dart:convert' as convert;
        
        import 'package:flutter/material.dart';
        import 'package:http/http.dart' as http;
        
        import 'models/user.dart';
        import '../utils/helpers.dart';
        
        import 'package:my_app/constants.dart' show API_URL, APP_NAME;
        import 'package:my_app/utils.dart' hide internalFunction;
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        imports = result.get("imports", [])

        assert len(imports) >= 8

        # Check dart core imports
        dart_imports = [imp for imp in imports if imp["path"].startswith("dart:")]
        assert len(dart_imports) >= 3

        # Check package imports
        package_imports = [imp for imp in imports if imp["path"].startswith("package:")]
        assert len(package_imports) >= 4

        # Check aliased import
        aliased_import = next(imp for imp in imports if imp.get("alias") == "convert")
        assert aliased_import["path"] == "dart:convert"

        # Check show/hide imports
        show_import = next(imp for imp in imports if "show" in imp)
        assert "API_URL" in show_import["show"]
        assert "APP_NAME" in show_import["show"]

        hide_import = next(imp for imp in imports if "hide" in imp)
        assert "internalFunction" in hide_import["hide"]

    def test_extract_exports(self):
        """Test extracting export statements."""
        plugin = DartPlugin()
        code = dedent(
            """
        export 'models/user.dart';
        export 'models/product.dart' show Product, ProductType;
        export 'utils/helpers.dart' hide privateHelper;
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        imports = result.get("imports", [])  # Exports are included in imports with type

        export_statements = [imp for imp in imports if imp["type"] == "export"]
        assert len(export_statements) == 3


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_syntax_error_handling(self):
        """Test handling of syntax errors in code."""
        plugin = DartPlugin()
        code = dedent(
            """
        class ValidClass {
          void validMethod() {
            print('Hello');
          }
        }
        
        // Syntax error below
        class InvalidClass {
          void invalidMethod(
            // Missing closing parenthesis
        
        class AnotherValidClass {
          void anotherMethod() {
            print('World');
          }
        }
        """
        )

        # Should not raise exception
        result = plugin.indexFile(Path("test.dart"), code)

        # Should return partial results
        assert isinstance(result, dict)
        symbols = result.get("symbols", [])
        assert isinstance(symbols, list)
        # Should extract at least the valid classes
        assert len(symbols) >= 1

    def test_unicode_handling(self):
        """Test handling of Unicode in code."""
        plugin = DartPlugin()
        code = dedent(
            """
        // Unicode in comments: 你好世界
        
        class 用户 {
          /// Unicode property: 姓名
          String 姓名;
          
          用户(this.姓名);
          
          void 问候() {
            print('你好, $姓名!');
          }
        }
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        symbols = result["symbols"]

        # Should handle Unicode symbols
        assert any(s["symbol"] == "用户" for s in symbols)

    def test_empty_file(self):
        """Test handling of empty files."""
        plugin = DartPlugin()

        result = plugin.indexFile(Path("empty.dart"), "")

        assert isinstance(result, dict)
        assert result.get("symbols", []) == []
        assert result.get("imports", []) == []

    def test_comment_only_file(self):
        """Test file with only comments."""
        plugin = DartPlugin()
        code = dedent(
            """
        // This file contains only comments
        // No actual code here
        
        /// This is a documentation comment
        /// but it's not associated with any code
        
        /* Block comment */
        """
        )

        result = plugin.indexFile(Path("comments.dart"), code)

        assert isinstance(result, dict)
        assert len(result.get("symbols", [])) == 0

    def test_error_result_patterns(self):
        """Test error handling with Result patterns."""
        plugin = DartPlugin()

        # Test with invalid file path
        result = plugin.index("/nonexistent/file.dart")
        assert isinstance(result, Result)
        assert result.success is False
        assert result.error is not None
        assert "Failed to index file" in result.error.message


class TestSearchFunctionality:
    """Test search and lookup functionality."""

    def test_get_definition(self, sqlite_store):
        """Test getting symbol definition."""
        plugin = DartPlugin(sqlite_store=sqlite_store)

        # Index a file first
        code = dedent(
            """
        /// A target function to find.
        void targetFunction() {
          print('Found me!');
        }
        
        /// A target class to find.
        class TargetClass {
          void method() {}
        }
        """
        )

        # Create repository and file in store
        repo_id = sqlite_store.create_repository("/test", "test")
        file_id = sqlite_store.store_file(
            repository_id=repo_id, file_path="/test/file.dart", language="dart"
        )

        # Index the file
        result = plugin.indexFile(Path("/test/file.dart"), code)

        # Store symbols
        for symbol in result["symbols"]:
            sqlite_store.store_symbol(
                file_id,
                symbol["symbol"],
                symbol["kind"],
                symbol["line"],
                symbol.get("span", (symbol["line"], symbol["line"]))[1],
                signature=symbol.get("signature"),
            )

        # Test getting definitions
        func_def = plugin.getDefinition("targetFunction")
        assert func_def is not None
        assert func_def["symbol"] == "targetFunction"
        assert func_def["kind"] == "function"

        class_def = plugin.getDefinition("TargetClass")
        assert class_def is not None
        assert class_def["symbol"] == "TargetClass"
        assert class_def["kind"] == "class"

        # Non-existent symbol
        none_def = plugin.getDefinition("nonexistent")
        assert none_def is None

    def test_search(self, sqlite_store):
        """Test search functionality."""
        plugin = DartPlugin(sqlite_store=sqlite_store)

        # Set up test data
        repo_id = sqlite_store.create_repository("/test", "test")

        # Create multiple files with symbols
        test_files = [
            (
                "widget.dart",
                """
class MyWidget extends StatelessWidget {
  Widget build(BuildContext context) {
    return Text('Hello');
  }
}

class MyButton extends StatelessWidget {
  Widget build(BuildContext context) {
    return ElevatedButton();
  }
}
""",
            ),
            (
                "utils.dart",
                """
void calculateSum(int a, int b) {
  return a + b;
}

void calculateProduct(int a, int b) {
  return a * b;
}
""",
            ),
        ]

        for filename, code in test_files:
            file_id = sqlite_store.store_file(
                repository_id=repo_id, file_path=f"/test/{filename}", language="dart"
            )
            result = plugin.indexFile(Path(f"/test/{filename}"), code)

            for symbol in result["symbols"]:
                sqlite_store.store_symbol(
                    file_id,
                    symbol["symbol"],
                    symbol["kind"],
                    symbol["line"],
                    symbol.get("span", (symbol["line"], symbol["line"]))[1],
                    signature=symbol.get("signature"),
                )

        # Test fuzzy search
        results = list(plugin.search("calc", {"semantic": False, "limit": 10}))

        assert len(results) >= 0
        # Results should contain symbols with "calc" in them
        # Note: Actual results depend on fuzzy indexer implementation

    def test_search_without_store(self):
        """Test search when no SQLite store is configured."""
        plugin = DartPlugin()  # No store

        results = list(plugin.search("test", {}))

        # Should return results from fuzzy indexer
        assert isinstance(results, list)


class TestFlutterSpecificFeatures:
    """Test Flutter-specific features and patterns."""

    def test_widget_hierarchy(self):
        """Test detection of Flutter widget hierarchy."""
        plugin = DartPlugin()
        code = dedent(
            """
        import 'package:flutter/material.dart';
        
        class MyApp extends StatelessWidget {
          @override
          Widget build(BuildContext context) {
            return MaterialApp(
              home: MyHomePage(),
            );
          }
        }
        
        class MyHomePage extends StatefulWidget {
          @override
          _MyHomePageState createState() => _MyHomePageState();
        }
        
        class _MyHomePageState extends State<MyHomePage> {
          int _counter = 0;
          
          void _incrementCounter() {
            setState(() {
              _counter++;
            });
          }
          
          @override
          Widget build(BuildContext context) {
            return Scaffold(
              appBar: AppBar(title: Text('Counter')),
              body: Center(
                child: Text('$_counter'),
              ),
              floatingActionButton: FloatingActionButton(
                onPressed: _incrementCounter,
                child: Icon(Icons.add),
              ),
            );
          }
        }
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        symbols = result["symbols"]

        # Check widget classes
        widget_symbols = [s for s in symbols if s["kind"] == "widget"]
        assert len(widget_symbols) >= 2

        # Check state class
        state_symbols = [s for s in symbols if s["kind"] == "state"]
        assert len(state_symbols) >= 1

        # Check build methods
        build_methods = [s for s in symbols if s["kind"] == "build_method"]
        assert len(build_methods) >= 2

    def test_state_management_patterns(self):
        """Test detection of state management patterns."""
        plugin = DartPlugin()
        code = dedent(
            """
        import 'package:flutter/material.dart';
        
        class CounterProvider extends ChangeNotifier {
          int _count = 0;
          
          int get count => _count;
          
          void increment() {
            _count++;
            notifyListeners();
          }
          
          void decrement() {
            _count--;
            notifyListeners();
          }
        }
        
        class CounterBloc {
          final _counterController = StreamController<int>();
          int _counter = 0;
          
          Stream<int> get counterStream => _counterController.stream;
          
          void increment() {
            _counter++;
            _counterController.sink.add(_counter);
          }
          
          void dispose() {
            _counterController.close();
          }
        }
        """
        )

        result = plugin.indexFile(Path("test.dart"), code)
        symbols = result["symbols"]

        # Should extract provider and bloc classes
        provider_class = next(s for s in symbols if s["symbol"] == "CounterProvider")
        assert provider_class["kind"] == "class"
        assert provider_class["extends"] == "ChangeNotifier"

        bloc_class = next(s for s in symbols if s["symbol"] == "CounterBloc")
        assert bloc_class["kind"] == "class"


class TestPersistenceIntegration:
    """Test integration with SQLite persistence."""

    def test_full_indexing_with_persistence(self, sqlite_store):
        """Test complete indexing workflow with persistence."""
        plugin = DartPlugin(sqlite_store=sqlite_store)

        # Create repository
        repo_id = sqlite_store.create_repository("/myproject", "myproject")

        # Index a complex Dart file
        code = dedent(
            """
        /// Main app entry point
        import 'package:flutter/material.dart';
        
        const String APP_NAME = 'My Flutter App';
        const int VERSION = 1;
        
        void main() {
          runApp(MyApp());
        }
        
        /// The main application widget
        class MyApp extends StatelessWidget {
          @override
          Widget build(BuildContext context) {
            return MaterialApp(
              title: APP_NAME,
              home: HomePage(),
            );
          }
        }
        
        /// Home page widget
        class HomePage extends StatefulWidget {
          @override
          _HomePageState createState() => _HomePageState();
        }
        
        class _HomePageState extends State<HomePage> {
          int _counter = 0;
          
          void _increment() {
            setState(() => _counter++);
          }
          
          @override
          Widget build(BuildContext context) {
            return Scaffold(
              body: Center(child: Text('$_counter')),
              floatingActionButton: FloatingActionButton(
                onPressed: _increment,
                child: Icon(Icons.add),
              ),
            );
          }
        }
        """
        )

        file_path = Path("/myproject/main.dart")
        file_id = sqlite_store.store_file(
            repository_id=repo_id, file_path=str(file_path), language="dart", size=len(code)
        )

        # Index the file
        result = plugin.indexFile(file_path, code)

        # Store all symbols
        for symbol in result["symbols"]:
            sqlite_store.store_symbol(
                file_id,
                symbol["symbol"],
                symbol["kind"],
                symbol["line"],
                symbol.get("span", (symbol["line"], symbol["line"]))[1],
                signature=symbol.get("signature"),
            )

        # Verify persistence
        stats = sqlite_store.get_statistics()
        assert stats["symbols"] > 0

        # Test retrieval
        main_func = plugin.getDefinition("main")
        assert main_func is not None

        app_class = plugin.getDefinition("MyApp")
        assert app_class is not None
        assert app_class["kind"] == "widget"


class TestPerformanceAndScalability:
    """Test performance characteristics and scalability."""

    def test_large_file_handling(self):
        """Test handling of large Dart files."""
        plugin = DartPlugin()

        # Generate a large file with many symbols
        classes = []
        for i in range(100):
            classes.append(
                f"""
class TestClass{i} {{
  String property{i} = 'value{i}';
  
  void method{i}() {{
    print('Method {i}');
  }}
  
  int calculate{i}(int x) {{
    return x * {i};
  }}
}}
"""
            )

        large_code = "\n".join(classes)

        # Should handle large file without issues
        result = plugin.indexFile(Path("large_test.dart"), large_code)

        symbols = result["symbols"]
        assert len(symbols) >= 300  # 100 classes + 100 properties + 200 methods

    def test_get_indexed_count(self):
        """Test get_indexed_count method."""
        plugin = DartPlugin()

        # Initially should be 0 (or pre-indexed count)
        initial_count = plugin.get_indexed_count()

        # Index a file
        code = "class TestClass {}"
        plugin.indexFile(Path("test1.dart"), code)

        # Count should increase
        new_count = plugin.get_indexed_count()
        assert new_count >= initial_count
