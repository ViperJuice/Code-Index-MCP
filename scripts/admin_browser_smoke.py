"""Metadata-only admin probe used alongside the HARDVERIFY browser smoke."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests

EVIDENCE_SCHEMA = "hardverify_admin_probe.v1"
UNAUTHORIZED_STATUSES = {401, 403}


def run_probe(
    base_url: str,
    *,
    docs_path: str = "/docs",
    openapi_path: str = "/openapi.json",
    protected_path: str = "/metrics",
    timeout: float = 10.0,
    expect_unauthorized: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Probe public docs metadata and one protected route without credentials."""
    root = base_url.rstrip("/")
    errors: list[str] = []

    docs_response = requests.get(f"{root}{docs_path}", timeout=timeout)
    swagger_visible = "swagger-ui" in docs_response.text.lower()
    if docs_response.status_code != 200:
        errors.append(f"docs returned {docs_response.status_code}")
    if not swagger_visible:
        errors.append("docs response did not contain Swagger UI")

    openapi_response = requests.get(f"{root}{openapi_path}", timeout=timeout)
    openapi: dict[str, Any] = {}
    if openapi_response.status_code == 200:
        try:
            payload = openapi_response.json()
            if isinstance(payload, dict):
                openapi = payload
        except ValueError:
            errors.append("OpenAPI response was not JSON")
    else:
        errors.append(f"OpenAPI returned {openapi_response.status_code}")

    protected_response = requests.get(f"{root}{protected_path}", timeout=timeout)
    unauthorized = protected_response.status_code in UNAUTHORIZED_STATUSES
    if expect_unauthorized and not unauthorized:
        errors.append(f"protected route returned {protected_response.status_code}")

    paths = openapi.get("paths", {})
    components = openapi.get("components", {})
    security_schemes = components.get("securitySchemes", {}) if isinstance(components, dict) else {}
    protected_path_present = isinstance(paths, dict) and protected_path in paths
    if not protected_path_present:
        errors.append("protected route missing from OpenAPI")
    if not security_schemes:
        errors.append("OpenAPI security schemes missing")

    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "docs": {
            "path": docs_path,
            "status": docs_response.status_code,
            "swagger_ui": swagger_visible,
        },
        "openapi": {
            "path": openapi_path,
            "status": openapi_response.status_code,
            "protected_path_present": protected_path_present,
            "security_scheme_count": len(security_schemes),
        },
        "protected": {
            "path": protected_path,
            "status": protected_response.status_code,
            "unauthorized": unauthorized,
        },
        "passed": not errors,
    }
    return evidence, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--docs-path", default="/docs")
    parser.add_argument("--openapi-path", default="/openapi.json")
    parser.add_argument("--protected-path", default="/metrics")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--expect-unauthorized", action="store_true")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    try:
        evidence, errors = run_probe(
            args.base_url,
            docs_path=args.docs_path,
            openapi_path=args.openapi_path,
            protected_path=args.protected_path,
            timeout=args.timeout,
            expect_unauthorized=args.expect_unauthorized,
        )
    except requests.RequestException as exc:
        print(f"admin probe request failed: {type(exc).__name__}", file=sys.stderr)
        return 1

    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")

    print(
        f"docs_status={evidence['docs']['status']} "
        f"openapi_status={evidence['openapi']['status']} "
        f"protected_status={evidence['protected']['status']} "
        f"passed={str(evidence['passed']).lower()}"
    )
    if errors:
        for error in errors:
            print(f"error={error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
