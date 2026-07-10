"""Tests for the metadata-only HARDVERIFY admin probe."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import requests

from scripts import admin_browser_smoke


def _response(status: int, *, text: str = "", payload: object | None = None) -> Mock:
    response = Mock(spec=requests.Response)
    response.status_code = status
    response.text = text
    if payload is None:
        response.json.side_effect = ValueError("not JSON")
    else:
        response.json.return_value = payload
    return response


def test_run_probe_records_docs_openapi_and_unauthorized_metadata(monkeypatch) -> None:
    responses = iter(
        [
            _response(200, text='<div id="swagger-ui"></div>'),
            _response(
                200,
                payload={
                    "paths": {"/metrics": {"get": {}}},
                    "components": {"securitySchemes": {"HTTPBearer": {"type": "http"}}},
                },
            ),
            _response(401, text='{"detail":"Not authenticated"}'),
        ]
    )
    monkeypatch.setattr(
        admin_browser_smoke.requests, "get", lambda *_args, **_kwargs: next(responses)
    )

    evidence, errors = admin_browser_smoke.run_probe(
        "http://127.0.0.1:9123",
        expect_unauthorized=True,
    )

    assert errors == []
    assert evidence == {
        "schema": "hardverify_admin_probe.v1",
        "docs": {"path": "/docs", "status": 200, "swagger_ui": True},
        "openapi": {
            "path": "/openapi.json",
            "status": 200,
            "protected_path_present": True,
            "security_scheme_count": 1,
        },
        "protected": {"path": "/metrics", "status": 401, "unauthorized": True},
        "passed": True,
    }


def test_run_probe_fails_closed_without_security_metadata(monkeypatch) -> None:
    responses = iter(
        [
            _response(200, text="plain docs"),
            _response(200, payload={"paths": {}, "components": {}}),
            _response(200, text="unprotected"),
        ]
    )
    monkeypatch.setattr(
        admin_browser_smoke.requests, "get", lambda *_args, **_kwargs: next(responses)
    )

    evidence, errors = admin_browser_smoke.run_probe(
        "http://127.0.0.1:9123",
        expect_unauthorized=True,
    )

    assert evidence["passed"] is False
    assert errors == [
        "docs response did not contain Swagger UI",
        "protected route returned 200",
        "protected route missing from OpenAPI",
        "OpenAPI security schemes missing",
    ]


def test_main_writes_redacted_json_without_response_bodies(
    monkeypatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "admin.json"
    evidence = {
        "schema": "hardverify_admin_probe.v1",
        "docs": {"status": 200},
        "openapi": {"status": 200},
        "protected": {"status": 401},
        "passed": True,
    }
    monkeypatch.setattr(admin_browser_smoke, "run_probe", lambda *_args, **_kwargs: (evidence, []))
    monkeypatch.setattr(
        admin_browser_smoke.sys,
        "argv",
        ["admin_browser_smoke.py", "--base-url", "http://localhost", "--json-output", str(output)],
    )

    assert admin_browser_smoke.main() == 0
    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored == evidence
    assert "authorization" not in output.read_text(encoding="utf-8").lower()
    assert "token" not in output.read_text(encoding="utf-8").lower()
