"""Registry of all supported languages with their configurations.

Note: Tree-sitter parsing is now handled by the treesitter-chunker package.
This registry only maintains language codes, names, and file extensions.
"""

LANGUAGE_CONFIGS = {
    # System Programming Languages
    "c": {
        "code": "c",
        "name": "C",
        "extensions": [".c", ".h"],
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
    },
    "rust": {
        "code": "rust",
        "name": "Rust",
        "extensions": [".rs"],
    },
    "go": {
        "code": "go",
        "name": "Go",
        "extensions": [".go"],
    },
    # Scripting Languages
    "python": {
        "code": "python",
        "name": "Python",
        "extensions": [".py", ".pyw"],
    },
    "javascript": {
        "code": "javascript",
        "name": "JavaScript",
        "extensions": [".js", ".mjs", ".cjs"],
    },
    "typescript": {
        "code": "typescript",
        "name": "TypeScript",
        "extensions": [".ts", ".tsx"],
    },
    "ruby": {
        "code": "ruby",
        "name": "Ruby",
        "extensions": [".rb", ".rake"],
    },
    "php": {
        "code": "php",
        "name": "PHP",
        "extensions": [".php", ".php3", ".php4", ".php5", ".phtml"],
    },
    "perl": {
        "code": "perl",
        "name": "Perl",
        "extensions": [".pl", ".pm", ".t"],
    },
    "lua": {
        "code": "lua",
        "name": "Lua",
        "extensions": [".lua"],
    },
    "bash": {
        "code": "bash",
        "name": "Bash",
        "extensions": [".sh", ".bash", ".zsh", ".fish"],
    },
    # JVM Languages
    "java": {
        "code": "java",
        "name": "Java",
        "extensions": [".java"],
    },
    "kotlin": {
        "code": "kotlin",
        "name": "Kotlin",
        "extensions": [".kt", ".kts"],
    },
    "scala": {
        "code": "scala",
        "name": "Scala",
        "extensions": [".scala", ".sc"],
    },
    # .NET Languages
    "c_sharp": {
        "code": "c_sharp",
        "name": "C#",
        "extensions": [".cs"],
    },
    # Functional Languages
    "haskell": {
        "code": "haskell",
        "name": "Haskell",
        "extensions": [".hs", ".lhs"],
    },
    "ocaml": {
        "code": "ocaml",
        "name": "OCaml",
        "extensions": [".ml", ".mli"],
    },
    "elixir": {
        "code": "elixir",
        "name": "Elixir",
        "extensions": [".ex", ".exs"],
    },
    "erlang": {
        "code": "erlang",
        "name": "Erlang",
        "extensions": [".erl", ".hrl"],
    },
    "elm": {
        "code": "elm",
        "name": "Elm",
        "extensions": [".elm"],
    },
    # Web Technologies
    "html": {
        "code": "html",
        "name": "HTML",
        "extensions": [".html", ".htm", ".xhtml"],
    },
    "css": {
        "code": "css",
        "name": "CSS",
        "extensions": [".css"],
    },
    "scss": {
        "code": "scss",
        "name": "SCSS",
        "extensions": [".scss"],
    },
    # Data Formats
    "json": {
        "code": "json",
        "name": "JSON",
        "extensions": [".json", ".jsonc"],
    },
    "yaml": {
        "code": "yaml",
        "name": "YAML",
        "extensions": [".yaml", ".yml"],
    },
    "toml": {
        "code": "toml",
        "name": "TOML",
        "extensions": [".toml"],
    },
    "xml": {
        "code": "xml",
        "name": "XML",
        "extensions": [".xml", ".xsd", ".xsl"],
    },
    # Config Languages
    "dockerfile": {
        "code": "dockerfile",
        "name": "Dockerfile",
        "extensions": ["Dockerfile", ".dockerfile"],
    },
    "make": {
        "code": "make",
        "name": "Makefile",
        "extensions": ["Makefile", ".mk", "makefile", "GNUmakefile"],
    },
    "cmake": {
        "code": "cmake",
        "name": "CMake",
        "extensions": [".cmake", "CMakeLists.txt"],
    },
    # Query Languages
    "sql": {
        "code": "sql",
        "name": "SQL",
        "extensions": [".sql"],
    },
    "graphql": {
        "code": "graphql",
        "name": "GraphQL",
        "extensions": [".graphql", ".gql"],
    },
    # Mobile Development
    "swift": {
        "code": "swift",
        "name": "Swift",
        "extensions": [".swift"],
    },
    "objc": {
        "code": "objc",
        "name": "Objective-C",
        "extensions": [".m", ".mm", ".h"],
    },
    "dart": {
        "code": "dart",
        "name": "Dart",
        "extensions": [".dart"],
    },
    # Scientific Computing
    "r": {
        "code": "r",
        "name": "R",
        "extensions": [".r", ".R"],
    },
    "julia": {
        "code": "julia",
        "name": "Julia",
        "extensions": [".jl"],
    },
    "matlab": {
        "code": "matlab",
        "name": "MATLAB",
        "extensions": [".m"],
    },
    "fortran": {
        "code": "fortran",
        "name": "Fortran",
        "extensions": [".f", ".f90", ".f95", ".f03", ".f08"],
    },
    # Documentation
    "markdown": {
        "code": "markdown",
        "name": "Markdown",
        "extensions": [".md", ".markdown"],
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
    },
    "rst": {
        "code": "rst",
        "name": "reStructuredText",
        "extensions": [".rst"],
    },
    "latex": {
        "code": "latex",
        "name": "LaTeX",
        "extensions": [".tex", ".ltx"],
    },
    # Other Languages
    "vim": {
        "code": "vim",
        "name": "Vim Script",
        "extensions": [".vim", ".vimrc"],
    },
    "regex": {
        "code": "regex",
        "name": "Regular Expression",
        "extensions": [".regex"],
    },
    "csv": {
        "code": "csv",
        "name": "CSV",
        "extensions": [".csv", ".tsv"],
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
