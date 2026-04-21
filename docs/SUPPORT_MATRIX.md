# Code-Index-MCP Support Matrix

This matrix is the canonical P23 support statement for version `1.2.0-rc3`.
The project is in beta/alpha documentation-hardening status: MCP STDIO is the
primary LLM surface, FastAPI is a secondary admin surface, and language support
varies by plugin path and optional dependencies.

Runtime facts are grounded in `mcp_server/plugins/language_registry.py`,
`mcp_server/plugins/plugin_factory.py`, `mcp_server/plugins/plugin_set_registry.py`,
`mcp_server/plugins/sandboxed_plugin.py`, and optional extras in `pyproject.toml`.

| Language | Runtime behavior | Parser status | Sandbox support | Required extras | Symbol quality | Semantic support | Known limitations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bash | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| C | Specialized plugin | Specific parser | Default sandbox module | Core | High for C symbols | Optional provider/API key | Header ownership and macro semantics are best effort |
| C# | Specialized plugin when importable | Specific parser | Default sandbox module | Core | Medium to high | Optional provider/API key | Sandbox map includes `c_sharp`/`csharp`; project references are best effort |
| C++ | Specialized plugin | Specific parser | Default sandbox module | Core | High for common C++ symbols | Optional provider/API key | Template and macro expansion remain best effort |
| CMake | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| CSS | Specialized HTML/CSS plugin | Specific parser | Default sandbox module | Core | Medium selectors/rules | Optional provider/API key | CSS and HTML share one plugin implementation |
| CSV | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Low document-like rows | Optional provider/API key | Treated as text/data, not code symbols |
| Dart | Specialized plugin | Specific parser | Default sandbox module | Core | Medium to high | Optional provider/API key | Flutter semantics are best effort |
| Dockerfile | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic instructions | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Elixir | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Elm | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Erlang | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Fortran | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Go | Specialized plugin when importable | Specific parser | No default import in current env; module mapped | Core | Medium to high | Optional provider/API key | Sandbox module exists but plugin import may depend on local environment |
| GraphQL | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic schema/query symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Haskell | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| HTML | Specialized HTML/CSS plugin | Specific parser | Default sandbox module | Core | Medium elements/ids/classes | Optional provider/API key | HTML and CSS share one plugin implementation |
| Java | Specialized plugin | Specific parser | Default sandbox module | `java` extra recommended for static analysis | Medium to high | Optional provider/API key | Import resolution depends on optional `javalang` |
| JavaScript | Specialized plugin | Specific parser | Default sandbox module | Core | High for common JS/JSX patterns | Optional provider/API key | Framework-specific semantics are best effort |
| JSON | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Low document/data symbols | Optional provider/API key | Treated as structured data, not executable code |
| Julia | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Kotlin | Generic registry path if specific import unavailable | Registry grammar plus sandbox module mapping | Module mapped; import may be unavailable | Core | Basic to medium | Optional provider/API key | P24 should reconcile factory import and sandbox mapping |
| LaTeX | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Low document sections | Optional provider/API key | Document-oriented extraction only |
| Lua | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Makefile | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic targets | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Markdown | Specialized document plugin | Specific parser | Default sandbox module | Core | Headings and document chunks | Optional provider/API key | Not a programming-language symbol index |
| MATLAB | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Objective-C | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| OCaml | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Perl | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| PHP | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Plain Text | Simple text plugin | Text scanner | No default sandbox module | Core | Text chunks only | Optional provider/API key | Sensitive extensions are indexed only inside allowed local roots |
| Python | Specialized plugin | Tree-sitter plus Jedi | Default sandbox module | Core | High for Python symbols | Optional provider/API key | Dynamic runtime behavior is best effort |
| R | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Regular Expression | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Low pattern chunks | Optional provider/API key | Treated as text/pattern data |
| reStructuredText | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Low document sections | Optional provider/API key | Document-oriented extraction only |
| Ruby | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| Rust | Generic registry path if specific import unavailable | Registry grammar plus sandbox module mapping | Module mapped; import may be unavailable | Core | Basic to medium | Optional provider/API key | P24 should reconcile factory import and sandbox mapping |
| Scala | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| SCSS | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic selector/rule symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| SQL | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic query/table references | Optional provider/API key | Dialect semantics are best effort |
| Swift | Specialized plugin | Specific parser | Default sandbox module | Core | Medium to high | Optional provider/API key | Platform SDK semantics are best effort |
| TOML | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Low key/value chunks | Optional provider/API key | Treated as structured data |
| TypeScript | Specialized plugin | Specific parser | Default sandbox module | Core | High for TS/TSX patterns | Optional provider/API key | Type-checker project context is best effort |
| Vim Script | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Basic structural symbols | Optional provider/API key | P24 must add sandbox degradation or module wiring |
| XML | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Low element chunks | Optional provider/API key | Treated as structured data |
| YAML | Generic Tree-sitter registry path | Registry grammar | No default sandbox module | Core | Low key/value chunks | Optional provider/API key | Treated as structured data |

Optional semantic and reranking behavior depends on the `semantic` and `rerank`
extras, provider configuration, and API keys or local model endpoints. It should
not be treated as unconditional support.

P24 runtime-hardening inputs:

- Default sandbox mode raises for registry-only languages without a sandbox
  module instead of automatically degrading to unsandboxed generic parsing.
- Rust and Kotlin have sandbox module mappings but were not importable as
  specific plugins in this environment.
- Plain text has a specific factory path but no default sandbox module mapping.
