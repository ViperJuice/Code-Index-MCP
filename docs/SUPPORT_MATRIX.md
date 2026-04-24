# Code-Index-MCP Support Matrix

This matrix is the canonical GASUPPORT support statement for version
`1.2.0-rc6`. The product release posture is still RC/public-alpha and beta:
MCP STDIO is the primary LLM surface, FastAPI is a secondary admin surface,
and the GA-hardening roadmap is reducing claims rather than widening the
product.

Repository-topology support is separate from language/runtime support. The v3
public-alpha model supports many unrelated repositories on one machine, with one
registered worktree per git common directory. Only the tracked/default branch is
indexed automatically. Same-repo sibling worktrees and non-default branch
queries return `index_unavailable` with `safe_fallback: "native_search"` until
readiness remediation completes; indexed MCP results are authoritative only when
readiness is `ready`.

Runtime facts are grounded in `mcp_server/plugins/language_registry.py`,
`mcp_server/plugins/plugin_factory.py`, `mcp_server/plugins/plugin_set_registry.py`,
`mcp_server/plugins/sandboxed_plugin.py`, `mcp_server/cli/tool_handlers.py`,
and `mcp_server/cli/stdio_runner.py`. The canonical release-boundary and
evidence checklist is `docs/validation/ga-readiness-checklist.md`.

## Claim tiers

- **Public-alpha**: `v1.2.0-rc6` is the active RC/public-alpha package
  contract. It is suitable for outside-developer validation of the documented
  STDIO, readiness, repository-topology, and Docker package surfaces.
- **Beta**: Multi-repo support, STDIO, and secondary tool readiness remain beta
  surfaces. Passing TOOLRDY evidence is readiness evidence, not a GA support
  claim or a support-matrix expansion.
- **GA**: GA claims require a separate hardening roadmap with enforced release
  governance, current end-to-end production evidence, and explicit support-tier
  acceptance for every advertised language/runtime surface.

Product-level release posture continues to use the shared GABASE labels
`public-alpha`, `beta`, `GA`, `experimental`, `unsupported`, and
`disabled-by-default`. The row-level support tiers below use the frozen
GASUPPORT labels `GA-supported`, `beta`, `experimental`, `unsupported`, and
`disabled-by-default`.

## Machine-checkable support facts

`PluginFactory.get_plugin_availability()` and `list_plugins` are the canonical
machine-readable support-fact surfaces. Each `plugin_availability` row exposes:

- `state` for default availability in the current sandbox posture.
- `sandbox_supported` for whether a hardened sandbox module exists.
- `specific_plugin` and `availability_basis` for specialized-plugin versus
  registry-only behavior.
- `activation_mode` for default, extra-required, or disabled-by-default paths.
- `plugin_module`, `required_extras`, `remediation`, and `error_type` for
  exact module and optional-dependency posture.

These fields are support evidence, not marketing copy. Secondary-tool readiness
evidence in `docs/validation/secondary-tool-readiness-evidence.md` remains
readiness evidence only and must not be used as proof of broader language,
topology, or install-surface support expansion.

## Language and runtime support

| Language | Support tier | Runtime behavior | Parser status | Sandbox support | Required extras | Symbol quality | Semantic support | Known limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bash | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| C | GA-supported | Specialized plugin | Specific parser | Default sandbox module | Core | High for C symbols | Optional provider/API key | Header ownership and macro semantics are best effort |
| C# | beta | Specialized plugin when importable | Specific parser | Default sandbox module | Core | Medium to high | Optional provider/API key | Sandbox map includes `c_sharp`/`csharp`; project references are best effort |
| C++ | GA-supported | Specialized plugin | Specific parser | Default sandbox module | Core | High for common C++ symbols | Optional provider/API key | Template and macro expansion remain best effort |
| CMake | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| CSS | GA-supported | Specialized HTML/CSS plugin | Specific parser | Default sandbox module | Core | Medium selectors/rules | Optional provider/API key | CSS and HTML share one plugin implementation |
| CSV | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low document-like rows | Optional provider/API key | Treated as text/data, not code symbols |
| Dart | beta | Specialized plugin | Specific parser | Default sandbox module | Core | Medium to high | Optional provider/API key | Flutter semantics are best effort |
| Dockerfile | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic instructions | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Elixir | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Elm | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Erlang | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Fortran | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Go | beta | Specialized plugin when importable | Specific parser | Sandbox module exists; current env importability can vary | Core | Medium to high | Optional provider/API key | Plugin import may depend on the local environment |
| GraphQL | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic schema/query symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Haskell | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| HTML | GA-supported | Specialized HTML/CSS plugin | Specific parser | Default sandbox module | Core | Medium elements/ids/classes | Optional provider/API key | HTML and CSS share one plugin implementation |
| Java | beta | Specialized plugin | Specific parser | Default sandbox module | `java` extra recommended for static analysis | Medium to high | Optional provider/API key | Import resolution depends on optional `javalang` |
| JavaScript | GA-supported | Specialized plugin | Specific parser | Default sandbox module | Core | High for common JS/JSX patterns | Optional provider/API key | Framework-specific semantics are best effort |
| JSON | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low document/data symbols | Optional provider/API key | Treated as structured data, not executable code |
| Julia | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Kotlin | beta | Specialized plugin | Specific parser | Default sandbox module | Core | Basic to medium | Optional provider/API key | `Plugin` export is normalized; language semantics remain best effort |
| LaTeX | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low document sections | Optional provider/API key | Document-oriented extraction only |
| Lua | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Makefile | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic targets | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Markdown | beta | Specialized document plugin | Specific parser | Default sandbox module | Core | Headings and document chunks | Optional provider/API key | Not a programming-language symbol index |
| MATLAB | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Objective-C | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| OCaml | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Perl | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| PHP | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Plain Text | disabled-by-default | Simple text plugin | Text scanner | Reported as `unsupported` in default sandbox mode | Core | Text chunks only | Optional provider/API key | Sensitive extensions are indexed only inside allowed local roots |
| Python | GA-supported | Specialized plugin | Tree-sitter plus Jedi | Default sandbox module | Core | High for Python symbols | Optional provider/API key | Dynamic runtime behavior is best effort |
| R | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Regular Expression | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low pattern chunks | Optional provider/API key | Treated as text/pattern data |
| reStructuredText | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low document sections | Optional provider/API key | Document-oriented extraction only |
| Ruby | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| Rust | beta | Specialized plugin | Specific parser | Default sandbox module | Core | Basic to medium | Optional provider/API key | `Plugin` export is normalized; language semantics remain best effort |
| Scala | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| SCSS | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic selector/rule symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| SQL | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic query/table references | Optional provider/API key | Dialect semantics are best effort |
| Swift | beta | Specialized plugin | Specific parser | Default sandbox module | Core | Medium to high | Optional provider/API key | Platform SDK semantics are best effort |
| TOML | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low key/value chunks | Optional provider/API key | Treated as structured data |
| TypeScript | GA-supported | Specialized plugin | Specific parser | Default sandbox module | Core | High for TS/TSX patterns | Optional provider/API key | Type-checker project context is best effort |
| Vim Script | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Basic structural symbols | Optional provider/API key | Available only when sandbox is explicitly disabled |
| XML | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low element chunks | Optional provider/API key | Treated as structured data |
| YAML | disabled-by-default | Generic Tree-sitter registry path | Registry grammar | Reported as `unsupported` in default sandbox mode | Core | Low key/value chunks | Optional provider/API key | Treated as structured data |

## Install and tool surfaces

| Surface | Support tier | Default posture | Evidence basis | Notes |
| --- | --- | --- | --- | --- |
| STDIO query tools (`search_code`, `symbol_lookup`, `get_status`, `list_plugins`) | beta | Primary LLM surface | `stdio_runner._build_tool_list()`, readiness-gated tool descriptions, `plugin_availability` facts | Indexed query results are authoritative only when readiness is `ready` |
| STDIO mutation and summarization tools (`reindex`, `write_summaries`, `summarize_sample`) | beta | Secondary tool surfaces behind readiness gates | `tool_handlers.py`, TOOLRDY evidence, readiness-refusal tests | Non-ready repos fail closed; the artifact is readiness evidence, not support expansion |
| FastAPI admin and diagnostics surface | beta | Secondary/admin surface | `README.md`, `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md` | Do not treat FastAPI as the primary LLM interface |
| Native source install via `uv sync --locked` | beta | Canonical local development and operator path | `pyproject.toml`, `uv.lock`, install docs | This is the preferred local install path while the release remains pre-GA |
| Pre-release package install (`index-it-mcp==1.2.0rc5`) | beta | Opt-in release artifact path | package naming and install docs | Keep tied to the RC/public-alpha release boundary until later GA evidence exists |
| Docker image `ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc6` | beta | Supported container path | Docker guide, release evidence, image naming tests | Container docs must keep the same topology and readiness limits as native docs |
| Semantic search (`uv sync --locked --extra semantic` plus provider config) | experimental | Optional extra and provider-dependent | extras docs, config env vars, support-fact notes | Requires provider credentials or a compatible local endpoint; not unconditional support |
| Reranking (`uv sync --locked --extra rerank` plus provider/model config) | experimental | Optional extra and provider-dependent | extras docs and support-fact notes | Treat as opt-in ranking improvement, not baseline query behavior |
| Default sandboxed plugin execution | beta | Default security posture | `sandbox_supported`, `activation_mode`, sandbox docs | Coverage varies by language and is authoritative through `plugin_availability` |
| Unsandboxed or sandbox-disabled plugin path | disabled-by-default | Explicit operator opt-in only | `activation_mode=disabled_by_default`, sandbox docs | Enabling unsandboxed fallback does not widen documented default support |
| Same-repo sibling worktrees and non-default indexed routing | unsupported | Outside the indexed-routing contract | readiness classifier, v3 topology docs, failure-matrix tests | Use native search or readiness remediation instead of treating this as indexed support |

## Notes

- Optional semantic and reranking behavior depends on extras, provider
  configuration, and API keys or local model endpoints. It should not be
  treated as unconditional support.
- `list_plugins` is the canonical detailed capability surface. Each
  `plugin_availability` row includes `language`, `state`, `sandbox_supported`,
  `specific_plugin`, `plugin_module`, `availability_basis`,
  `activation_mode`, `required_extras`, `remediation`, and `error_type`.
- Registry-only languages remain bounded by the default sandbox posture. If a
  language is reported as `unsupported` with `activation_mode` set to
  `disabled_by_default`, that is evidence for the row above, not permission to
  advertise the language as default-on support.
- TOOLRDY evidence in
  `docs/validation/secondary-tool-readiness-evidence.md` remains readiness
  evidence only. It can justify readiness wording for existing secondary tools
  but must not be used as proof of broader support expansion.
