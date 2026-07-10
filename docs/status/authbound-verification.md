# AUTHBOUND Verification

- roadmap_sha256: `7741ebf13c8598c35f57eac09bfeccf8bbbec7e202d2709526256c1c99b8966e`
- interface_freeze_gates: `IF-0-AUTHBOUND-1`, `IF-0-AUTHBOUND-2`
- failing_at_base_reproduction: `uv run pytest tests/security/test_auth_boundary.py -q --no-cov`
- targeted_passing_commands:
  - `uv run pytest tests/security/test_auth_boundary.py -q --no-cov`
  - `uv run pytest tests/security/test_auth_startup_wiring.py tests/security/test_startup_config_validation.py -q --no-cov`
  - `uv run pytest tests/security/test_route_auth_coverage.py tests/security/test_metrics_auth.py tests/security/test_mcpauth_boundary.py tests/security/test_openapi_auth_metadata.py tests/test_gateway.py tests/test_gateway_auth_boundary.py -q --no-cov`
  - `uv run pytest tests/docs/test_authbound_security_docs.py tests/docs/test_authbound_verification_record.py -q --no-cov`
- browser_smoke: `uv run python scripts/admin_browser_smoke.py --base-url http://127.0.0.1:8000 --docs-path /docs --protected-path /metrics --expect-unauthorized`
- auth_diff_summary: removed fallback auth, require validated JWTs, register HTTP security middleware before startup, advertise bearer auth in OpenAPI, preserve persisted role and permission state
- targeted_suite_result: `103 passed in 23.09s`
- browser_smoke_result: blocked because local uvicorn startup failed before serving `/docs`; startup reached repository bootstrap and hit `Permission denied: '/workspaces'` during dispatcher bootstrap after auth initialization
- no-new-failures baseline comparison: AUTHBOUND targeted suite passed with no new failures in the covered phase-owned surfaces
- redaction_posture: `metadata_only`
- non-goals: no STDIO handshake changes, no external identity provider integration, no repository-selection changes
