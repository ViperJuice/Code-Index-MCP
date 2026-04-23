# Code-Index-MCP Support Matrix

This matrix is the canonical P23 support statement for version `1.2.0-rc5`.
The project is in beta/alpha documentation-hardening status: MCP STDIO is the
primary LLM surface, FastAPI is a secondary admin surface, and language support
varies by plugin path and optional dependencies.

Repository-topology support is separate from language/runtime support. The v3
public-alpha model supports many unrelated repositories on one machine, with one
registered worktree per git common directory. Only the tracked/default branch is
indexed automatically. Same-repo sibling worktrees and non-default branch
queries return `index_unavailable` with `safe_fallback: "native_search"` until
readiness remediation completes; indexed MCP results are authoritative only when
readiness is `ready`.

Runtime facts are grounded in `mcp_server/plugins/language_registry.py`,
`mcp_server/plugins/plugin_factory.py`, `mcp_server/plugins/plugin_set_registry.py`,
`mcp_server/plugins/sandboxed_plugin.py`, and optional extras in `pyproject.toml`.

| Language | Runtime behavior | Parser status | Sandbox support | Required extras | Symbol quality | Semantic support | Known limitations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bash | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| C | Specialized plugin | Specific parser | Default sandbox module | Core | High for C symbols | Optional provider/API key | Header ownership and macro semantics are best effort |
| C# | Specialized plugin when importable | Specific parser | Default sandbox module | Core | Medium to high | Optional provider/API key | Sandbox map includes `c_sharp`/`csharp`; project references are best effort |
| C++ | Specialized plugin | Specific parser | Default sandbox module | Core | High for common C++ symbols | Optional provider/API key | Template and macro expansion remain best effort |
| CMake | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| CSS | Specialized HTML/CSS plugin | Specific parser | Default sandbox module | Core | Medium selectors/rules | Optional provider/API key | CSS and HTML share one plugin implementation |
| CSV | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low document-like rows | Optional provider/API key | Treated as text/data, not code symbols |
| Dart | Specialized plugin | Specific parser | Default sandbox module | Core | Medium to high | Optional provider/API key | Flutter semantics are best effort |
| Dockerfile | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic instructions | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Elixir | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Elm | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Erlang | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Fortran | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Go | Specialized plugin when importable | Specific parser | No default import in current env; module mapped | Core | Medium to high | Optional provider/API key | Sandbox module exists but plugin import may depend on local environment |
| GraphQL | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic schema/query symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Haskell | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| HTML | Specialized HTML/CSS plugin | Specific parser | Default sandbox module | Core | Medium elements/ids/classes | Optional provider/API key | HTML and CSS share one plugin implementation |
| Java | Specialized plugin | Specific parser | Default sandbox module | `java` extra recommended for static analysis | Medium to high | Optional provider/API key | Import resolution depends on optional `javalang` |
| JavaScript | Specialized plugin | Specific parser | Default sandbox module | Core | High for common JS/JSX patterns | Optional provider/API key | Framework-specific semantics are best effort |
| JSON | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low document/data symbols | Optional provider/API key | Treated as structured data, not executable code |
| Julia | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Kotlin | Specialized plugin | Specific parser | Default sandbox module | Core | Basic to medium | Optional provider/API key | `Plugin` export is normalized; language semantics remain best effort |
| LaTeX | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low document sections | Optional provider/API key | Document-oriented extraction only |
| Lua | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Makefile | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic targets | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Markdown | Specialized document plugin | Specific parser | Default sandbox module | Core | Headings and document chunks | Optional provider/API key | Not a programming-language symbol index |
| MATLAB | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Objective-C | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| OCaml | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Perl | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| PHP | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Plain Text | Simple text plugin | Text scanner | Reported as `unsupported` in default sandbox mode | Core | Text chunks only | Optional provider/API key | Sensitive extensions are indexed only inside allowed local roots |
| Python | Specialized plugin | Tree-sitter plus Jedi | Default sandbox module | Core | High for Python symbols | Optional provider/API key | Dynamic runtime behavior is best effort |
| R | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Regular Expression | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low pattern chunks | Optional provider/API key | Treated as text/pattern data |
| reStructuredText | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low document sections | Optional provider/API key | Document-oriented extraction only |
| Ruby | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Rust | Specialized plugin | Specific parser | Default sandbox module | Core | Basic to medium | Optional provider/API key | `Plugin` export is normalized; language semantics remain best effort |
| Scala | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| SCSS | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic selector/rule symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| SQL | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic query/table references | Optional provider/API key | Dialect semantics are best effort |
| Swift | Specialized plugin | Specific parser | Default sandbox module | Core | Medium to high | Optional provider/API key | Platform SDK semantics are best effort |
| TOML | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low key/value chunks | Optional provider/API key | Treated as structured data |
| TypeScript | Specialized plugin | Specific parser | Default sandbox module | Core | High for TS/TSX patterns | Optional provider/API key | Type-checker project context is best effort |
| Vim Script | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| XML | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low element chunks | Optional provider/API key | Treated as structured data |
| YAML | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low key/value chunks | Optional provider/API key | Treated as structured data |

Optional semantic and reranking behavior depends on the `semantic` and `rerank`
extras, provider configuration, and API keys or local model endpoints. It should
not be treated as unconditional support.

P24 runtime-hardening state:

- Sandbox mode is enabled by default. Registry-only languages without a hardened
  sandbox module are reported as `unsupported` through `list_plugins` and skipped
  quietly during indexing; they are not loaded through an unsandboxed fallback.
- Optional dependency misses are reported as `missing_extra` with remediation.
  Java static analysis requires `javalang`; install it with
  `uv sync --locked --extra java`.
- `list_plugins` is the canonical detailed capability surface. Each
  `plugin_availability` row includes `language`, `state`, `sandbox_supported`,
  `specific_plugin`, `plugin_module`, `required_extras`, `remediation`, and
  `error_type`.
- Rust, Kotlin, and both C# aliases (`c_sharp`, `csharp`) have normalized
  sandbox construction paths. Plain text remains a specific in-process plugin
  and is reported as `unsupported` in default sandbox mode until a hardened
  sandbox module is added.
