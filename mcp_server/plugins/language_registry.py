"""Registry of all supported languages with their configurations."""

# Tree-sitter query strings for common symbol types
COMMON_QUERIES = {
    "function": "(function_declaration name: (identifier) @function)",
    "class": "(class_declaration name: (identifier) @class)",
    "method": "(method_declaration name: (identifier) @method)",
    "type": "(type_declaration name: (identifier) @type)",
}

LANGUAGE_CONFIGS = {
    # System Programming Languages
    "c": {
        "code": "c",
        "name": "C",
        "extensions": [".c", ".h"],
        "symbols": [
            "function_definition",
            "struct_specifier",
            "enum_specifier",
            "type_definition",
        ],
        "query": """
            (function_definition declarator: (function_declarator declarator: (identifier) @function))
            (struct_specifier name: (type_identifier) @struct)
            (enum_specifier name: (type_identifier) @enum)
            (type_definition declarator: (type_identifier) @typedef)
        """,
    },
    "cpp": {
        "code": "cpp",
        "name": "C++",
        "extensions": [
            ".cpp",
            ".cc",
            ".cxx",
            ".c++",
            ".hpp",
            ".h",
            ".hh",
            ".h++",
            ".hxx",
        ],
        "symbols": [
            "function_definition",
            "class_specifier",
            "struct_specifier",
            "namespace_definition",
        ],
        "query": """
            (function_definition declarator: (function_declarator declarator: (identifier) @function))
            (class_specifier name: (type_identifier) @class)
            (struct_specifier name: (type_identifier) @struct)
            (namespace_definition name: (identifier) @namespace)
        """,
    },
    "rust": {
        "code": "rust",
        "name": "Rust",
        "extensions": [".rs"],
        "symbols": [
            "function_item",
            "struct_item",
            "enum_item",
            "trait_item",
            "impl_item",
            "mod_item",
            "const_item",
            "static_item",
            "type_item",
        ],
        "query": """
            (function_item name: (identifier) @function)
            (struct_item name: (type_identifier) @struct)
            (enum_item name: (type_identifier) @enum)
            (trait_item name: (type_identifier) @trait)
            (impl_item trait: (type_identifier) @impl)
            (impl_item type: (type_identifier) @impl)
            (mod_item name: (identifier) @module)
            (const_item name: (identifier) @constant)
            (static_item name: (identifier) @static)
            (type_item name: (type_identifier) @type_alias)
            (macro_definition name: (identifier) @macro)
        """,
    },
    "go": {
        "code": "go",
        "name": "Go",
        "extensions": [".go"],
        "symbols": [
            "function_declaration",
            "method_declaration",
            "type_declaration",
            "const_declaration",
            "var_declaration",
        ],
        "query": """
            (function_declaration name: (identifier) @function)
            (method_declaration name: (field_identifier) @method)
            (type_declaration (type_spec name: (type_identifier) @type))
            (const_declaration (const_spec name: (identifier) @constant))
            (var_declaration (var_spec name: (identifier) @variable))
            (interface_type (method_spec name: (field_identifier) @interface_method))
        """,
    },
    # Scripting Languages
    "python": {
        "code": "python",
        "name": "Python",
        "extensions": [".py", ".pyw"],
        "symbols": [
            "function_definition",
            "class_definition",
            "import_statement",
            "import_from_statement",
            "global_statement",
        ],
        "query": """
            (function_definition name: (identifier) @function)
            (class_definition name: (identifier) @class)
            (decorated_definition (function_definition name: (identifier) @decorated_function))
            (decorated_definition (class_definition name: (identifier) @decorated_class))
            (import_statement name: (dotted_name) @import)
            (import_from_statement module_name: (dotted_name) @import_from)
            (global_statement (identifier) @global_var)
            (assignment left: (identifier) @variable)
        """,
    },
    "javascript": {
        "code": "javascript",
        "name": "JavaScript",
        "extensions": [".js", ".mjs", ".cjs"],
        "symbols": [
            "function_declaration",
            "class_declaration",
            "method_definition",
            "variable_declarator",
            "arrow_function",
        ],
        "query": """
            (function_declaration name: (identifier) @function)
            (class_declaration name: (identifier) @class)
            (method_definition name: (property_identifier) @method)
            (variable_declarator name: (identifier) @variable)
            (lexical_declaration (variable_declarator name: (identifier) @const_var))
            (export_statement (function_declaration name: (identifier) @exported_function))
            (export_statement (class_declaration name: (identifier) @exported_class))
            (import_statement (import_clause (identifier) @import))
        """,
    },
    "typescript": {
        "code": "typescript",
        "name": "TypeScript",
        "extensions": [".ts", ".tsx"],
        "symbols": [
            "function_declaration",
            "class_declaration",
            "interface_declaration",
            "type_alias_declaration",
        ],
        "query": """
            (function_declaration name: (identifier) @function)
            (class_declaration name: (identifier) @class)
            (interface_declaration name: (identifier) @interface)
            (type_alias_declaration name: (identifier) @type)
        """,
    },
    "ruby": {
        "code": "ruby",
        "name": "Ruby",
        "extensions": [".rb", ".rake"],
        "symbols": ["method", "class", "module", "singleton_method"],
        "query": """
            (method name: (identifier) @method)
            (class name: (constant) @class)
            (module name: (constant) @module)
            (singleton_method name: (identifier) @singleton_method)
        """,
    },
    "php": {
        "code": "php",
        "name": "PHP",
        "extensions": [".php", ".php3", ".php4", ".php5", ".phtml"],
        "symbols": ["function_definition", "class_declaration", "method_declaration"],
        "query": """
            (function_definition name: (name) @function)
            (class_declaration name: (name) @class)
            (method_declaration name: (name) @method)
        """,
    },
    "perl": {
        "code": "perl",
        "name": "Perl",
        "extensions": [".pl", ".pm", ".t"],
        "symbols": ["subroutine_declaration"],
        "query": """
            (subroutine_declaration name: (identifier) @function)
        """,
    },
    "lua": {
        "code": "lua",
        "name": "Lua",
        "extensions": [".lua"],
        "symbols": ["function_declaration", "function_definition"],
        "query": """
            (function_declaration name: (identifier) @function)
            (function_definition name: (identifier) @function)
        """,
    },
    "bash": {
        "code": "bash",
        "name": "Bash",
        "extensions": [".sh", ".bash", ".zsh", ".fish"],
        "symbols": ["function_definition", "variable_assignment"],
        "query": """
            (function_definition name: (word) @function)
            (variable_assignment name: (variable_name) @variable)
        """,
    },
    # JVM Languages
    "java": {
        "code": "java",
        "name": "Java",
        "extensions": [".java"],
        "symbols": [
            "class_declaration",
            "interface_declaration",
            "method_declaration",
            "constructor_declaration",
            "enum_declaration",
        ],
        "query": """
            (class_declaration name: (identifier) @class)
            (interface_declaration name: (identifier) @interface)
            (method_declaration name: (identifier) @method)
            (constructor_declaration name: (identifier) @constructor)
            (enum_declaration name: (identifier) @enum)
        """,
    },
    "kotlin": {
        "code": "kotlin",
        "name": "Kotlin",
        "extensions": [".kt", ".kts"],
        "symbols": [
            "class_declaration",
            "function_declaration",
            "object_declaration",
            "suspend_function",
            "data_class",
            "sealed_class",
            "extension_function",
        ],
        "query": """
            (class_declaration name: (type_identifier) @class)
            (function_declaration name: (simple_identifier) @function)
            (object_declaration name: (type_identifier) @object)
            (function_declaration
                (modifiers (modifier) @suspend (#eq? @suspend "suspend"))
                name: (simple_identifier) @suspend_function
            )
            (class_declaration
                (modifiers (modifier) @data (#eq? @data "data"))
                name: (type_identifier) @data_class
            )
            (class_declaration
                (modifiers (modifier) @sealed (#eq? @sealed "sealed"))
                name: (type_identifier) @sealed_class
            )
            (function_declaration
                receiver: (function_value_parameters)
                name: (simple_identifier) @extension_function
            )
        """,
    },
    "scala": {
        "code": "scala",
        "name": "Scala",
        "extensions": [".scala", ".sc"],
        "symbols": [
            "class_definition",
            "object_definition",
            "trait_definition",
            "function_definition",
        ],
        "query": """
            (class_definition name: (identifier) @class)
            (object_definition name: (identifier) @object)
            (trait_definition name: (identifier) @trait)
            (function_definition name: (identifier) @function)
        """,
    },
    # .NET Languages
    "c_sharp": {
        "code": "c_sharp",
        "name": "C#",
        "extensions": [".cs"],
        "symbols": [
            "class_declaration",
            "interface_declaration",
            "method_declaration",
            "property_declaration",
        ],
        "query": """
            (class_declaration name: (identifier) @class)
            (interface_declaration name: (identifier) @interface)
            (method_declaration name: (identifier) @method)
            (property_declaration name: (identifier) @property)
        """,
    },
    # Functional Languages
    "haskell": {
        "code": "haskell",
        "name": "Haskell",
        "extensions": [".hs", ".lhs"],
        "symbols": ["function", "type_synonym", "data", "newtype", "class"],
        "query": """
            (function name: (variable) @function)
            (type_synonym name: (type) @type)
            (data name: (type) @data)
        """,
    },
    "ocaml": {
        "code": "ocaml",
        "name": "OCaml",
        "extensions": [".ml", ".mli"],
        "symbols": ["value_definition", "type_definition", "module_definition"],
        "query": """
            (value_definition (value_name) @function)
            (type_definition (type_constructor) @type)
            (module_definition (module_name) @module)
        """,
    },
    "elixir": {
        "code": "elixir",
        "name": "Elixir",
        "extensions": [".ex", ".exs"],
        "symbols": ["function", "module"],
        "query": """
            (def name: (identifier) @function)
            (defmodule name: (alias) @module)
        """,
    },
    "erlang": {
        "code": "erlang",
        "name": "Erlang",
        "extensions": [".erl", ".hrl"],
        "symbols": ["function", "module_attribute"],
        "query": """
            (function name: (atom) @function)
            (module_attribute name: (atom) @attribute)
        """,
    },
    "elm": {
        "code": "elm",
        "name": "Elm",
        "extensions": [".elm"],
        "symbols": [
            "function_declaration",
            "type_declaration",
            "type_alias_declaration",
        ],
        "query": """
            (function_declaration_left (lower_case_identifier) @function)
            (type_declaration (upper_case_identifier) @type)
            (type_alias_declaration name: (upper_case_identifier) @alias)
        """,
    },
    # Web Technologies
    "html": {
        "code": "html",
        "name": "HTML",
        "extensions": [".html", ".htm", ".xhtml"],
        "symbols": ["element", "script_element", "style_element"],
        "query": """
            (element (start_tag (tag_name) @tag))
            (script_element) @script
            (style_element) @style
        """,
    },
    "css": {
        "code": "css",
        "name": "CSS",
        "extensions": [".css"],
        "symbols": ["rule_set", "media_statement", "keyframes_statement"],
        "query": """
            (rule_set (selectors) @selector)
            (media_statement) @media
            (keyframes_statement (keyframes_name) @keyframes)
        """,
    },
    "scss": {
        "code": "scss",
        "name": "SCSS",
        "extensions": [".scss"],
        "symbols": ["rule_set", "mixin_statement", "function_statement"],
        "query": """
            (rule_set (selectors) @selector)
            (mixin_statement name: (identifier) @mixin)
            (function_statement name: (identifier) @function)
        """,
    },
    # Data Formats
    "json": {
        "code": "json",
        "name": "JSON",
        "extensions": [".json", ".jsonc"],
        "symbols": ["pair"],
        "query": """
            (pair key: (string) @key)
        """,
    },
    "yaml": {
        "code": "yaml",
        "name": "YAML",
        "extensions": [".yaml", ".yml"],
        "symbols": ["block_mapping_pair", "flow_pair"],
        "query": """
            (block_mapping_pair key: (flow_node) @key)
            (flow_pair key: (flow_node) @key)
        """,
    },
    "toml": {
        "code": "toml",
        "name": "TOML",
        "extensions": [".toml"],
        "symbols": ["table", "pair"],
        "query": """
            (table (bare_key) @section)
            (pair (bare_key) @key)
        """,
    },
    "xml": {
        "code": "xml",
        "name": "XML",
        "extensions": [".xml", ".xsd", ".xsl"],
        "symbols": ["element", "attribute"],
        "query": """
            (element (start_tag (tag_name) @tag))
            (attribute (attribute_name) @attribute)
        """,
    },
    # Config Languages
    "dockerfile": {
        "code": "dockerfile",
        "name": "Dockerfile",
        "extensions": ["Dockerfile", ".dockerfile"],
        "symbols": ["from_instruction", "run_instruction", "cmd_instruction"],
        "query": """
            (from_instruction) @from
            (run_instruction) @run
            (cmd_instruction) @cmd
        """,
    },
    "make": {
        "code": "make",
        "name": "Makefile",
        "extensions": ["Makefile", ".mk", "makefile", "GNUmakefile"],
        "symbols": ["rule"],
        "query": """
            (rule (targets) @target)
        """,
    },
    "cmake": {
        "code": "cmake",
        "name": "CMake",
        "extensions": [".cmake", "CMakeLists.txt"],
        "symbols": ["function_def", "macro_def"],
        "query": """
            (function_def name: (argument) @function)
            (macro_def name: (argument) @macro)
        """,
    },
    # Query Languages
    "sql": {
        "code": "sql",
        "name": "SQL",
        "extensions": [".sql"],
        "symbols": ["create_table", "create_function", "create_view"],
        "query": """
            (create_table (table_reference name: (identifier) @table))
            (create_function (identifier) @function)
            (create_view (identifier) @view)
        """,
    },
    "graphql": {
        "code": "graphql",
        "name": "GraphQL",
        "extensions": [".graphql", ".gql"],
        "symbols": [
            "object_type_definition",
            "interface_type_definition",
            "field_definition",
        ],
        "query": """
            (object_type_definition name: (name) @type)
            (interface_type_definition name: (name) @interface)
            (field_definition name: (name) @field)
        """,
    },
    # Mobile Development
    "swift": {
        "code": "swift",
        "name": "Swift",
        "extensions": [".swift"],
        "symbols": [
            "function_declaration",
            "class_declaration",
            "protocol_declaration",
        ],
        "query": """
            (function_declaration name: (simple_identifier) @function)
            (class_declaration name: (type_identifier) @class)
            (protocol_declaration name: (type_identifier) @protocol)
        """,
    },
    "objc": {
        "code": "objc",
        "name": "Objective-C",
        "extensions": [".m", ".mm", ".h"],
        "symbols": ["class_interface", "category_interface", "method_declaration"],
        "query": """
            (class_interface name: (identifier) @class)
            (category_interface name: (identifier) @category)
            (method_declaration) @method
        """,
    },
    "dart": {
        "code": "dart",
        "name": "Dart",
        "extensions": [".dart"],
        "symbols": ["class_definition", "function_signature", "method_signature"],
        "query": """
            (class_definition name: (identifier) @class)
            (function_signature name: (identifier) @function)
            (method_signature name: (identifier) @method)
        """,
    },
    # Scientific Computing
    "r": {
        "code": "r",
        "name": "R",
        "extensions": [".r", ".R"],
        "symbols": ["function_definition", "assignment"],
        "query": """
            (function_definition name: (identifier) @function)
            (assignment left: (identifier) @variable)
        """,
    },
    "julia": {
        "code": "julia",
        "name": "Julia",
        "extensions": [".jl"],
        "symbols": ["function_definition", "struct_definition", "module_definition"],
        "query": """
            (function_definition name: (identifier) @function)
            (struct_definition name: (identifier) @struct)
            (module_definition name: (identifier) @module)
        """,
    },
    "matlab": {
        "code": "matlab",
        "name": "MATLAB",
        "extensions": [".m"],
        "symbols": ["function_definition", "class_definition"],
        "query": """
            (function_definition name: (identifier) @function)
            (class_definition name: (identifier) @class)
        """,
    },
    "fortran": {
        "code": "fortran",
        "name": "Fortran",
        "extensions": [".f", ".f90", ".f95", ".f03", ".f08"],
        "symbols": ["function", "subroutine", "module"],
        "query": """
            (function name: (identifier) @function)
            (subroutine name: (identifier) @subroutine)
            (module name: (identifier) @module)
        """,
    },
    # Documentation
    "markdown": {
        "code": "markdown",
        "name": "Markdown",
        "extensions": [".md", ".markdown"],
        "symbols": ["atx_heading", "setext_heading"],
        "query": """
            (atx_heading (heading_content) @heading)
            (setext_heading (heading_content) @heading)
        """,
    },
    "plaintext": {
        "code": "plaintext",
        "name": "Plain Text",
        "extensions": [
            ".txt",
            ".text",
            ".log",
            ".readme",
            ".env",
            ".key",
            ".pem",
            ".crt",
            ".cer",
            ".pfx",
            ".p12",
            ".pub",
            ".pri",
            ".license",
            ".version",
            ".gitignore",
            ".dockerignore",
            ".npmignore",
        ],
        "symbols": [],  # Plain text doesn't use tree-sitter
        "query": "",
    },
    "rst": {
        "code": "rst",
        "name": "reStructuredText",
        "extensions": [".rst"],
        "symbols": ["section", "directive"],
        "query": """
            (section (title) @section)
            (directive name: (type) @directive)
        """,
    },
    "latex": {
        "code": "latex",
        "name": "LaTeX",
        "extensions": [".tex", ".ltx"],
        "symbols": ["section", "environment", "new_command"],
        "query": """
            (section (curly_group) @section)
            (environment (begin name: (curly_group_text) @env))
            (new_command_definition name: (curly_group) @command)
        """,
    },
    # Other Languages
    "vim": {
        "code": "vim",
        "name": "Vim Script",
        "extensions": [".vim", ".vimrc"],
        "symbols": ["function_definition", "command_definition"],
        "query": """
            (function_definition name: (identifier) @function)
            (command_definition name: (command_name) @command)
        """,
    },
    "regex": {
        "code": "regex",
        "name": "Regular Expression",
        "extensions": [".regex"],
        "symbols": ["pattern"],
        "query": """
            (pattern) @pattern
        """,
    },
    "csv": {
        "code": "csv",
        "name": "CSV",
        "extensions": [".csv", ".tsv"],
        "symbols": [],  # CSV doesn't have traditional symbols
        "query": "",
    },
}


# Helper function to get all supported extensions
def get_all_extensions() -> set[str]:
    """Get all supported file extensions."""
    extensions = set()
    for config in LANGUAGE_CONFIGS.values():
        extensions.update(config["extensions"])
    return extensions


# Helper function to get language by extension
def get_language_by_extension(extension: str) -> str | None:
    """Get language code by file extension."""
    for lang_code, config in LANGUAGE_CONFIGS.items():
        if extension in config["extensions"]:
            return lang_code
    return None
