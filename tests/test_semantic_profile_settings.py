"""Tests for semantic profile configuration loading in settings."""

from pathlib import Path

from mcp_server.config.settings import Settings, _expand_env_vars, _find_profiles_yaml


def test_settings_loads_profiles_from_yaml(monkeypatch, tmp_path: Path):
    """YAML profile file should be converted into registry-ready config."""
    yaml_content = """
profiles:
  commercial_high:
    provider: voyage
    model:
      name: voyage-code-3
      output_dimension: 2048
    vector_store:
      collection: code_index__commercial_high__v1
      vector_size: 2048
      distance: dot
    normalization:
      l2_normalize_vectors: false
    metadata:
      chunk_schema_version: 1
      embed_schema_version: 1
  oss_high:
    provider: openai_compatible
    model:
      name: Qwen/Qwen3-Embedding-8B
      output_dimension: 4096
    serving:
      vllm:
        base_url: http://127.0.0.1:8000
    vector_store:
      collection: code_index__oss_high__v1
      vector_size: 4096
      distance: dot
    normalization:
      l2_normalize_vectors: true
    metadata:
      chunk_schema_version: 1
      embed_schema_version: 1
""".strip()

    (tmp_path / "code-index-mcp.profiles.yaml").write_text(yaml_content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        Settings,
        "_detect_treesitter_chunker_version",
        lambda self: "treesitter-chunker@2.2.4",
    )
    settings = Settings()
    profiles = settings.get_semantic_profiles_config()

    assert "commercial_high" in profiles
    assert profiles["commercial_high"]["provider"] == "voyage"
    assert profiles["commercial_high"]["vector_dimension"] == 2048
    assert profiles["commercial_high"]["distance_metric"] == "dot"
    assert profiles["commercial_high"]["chunker_version"] == "treesitter-chunker@2.2.4"
    assert (
        profiles["commercial_high"]["build_metadata"]["collection_name"]
        == "code_index__commercial_high__v1"
    )

    assert profiles["oss_high"]["provider"] == "openai_compatible"
    assert profiles["oss_high"]["vector_dimension"] == 4096
    assert profiles["oss_high"]["normalization_policy"] == "l2"
    assert profiles["oss_high"]["build_metadata"]["openai_api_base"] == "http://127.0.0.1:8000"
    assert profiles["oss_high"]["build_metadata"]["collection_name"] == "code_index__oss_high__v1"


def test_default_profile_resolves_first_yaml_profile_when_legacy_default(
    monkeypatch, tmp_path: Path
):
    """When default is legacy-default, first YAML profile becomes runtime default."""
    yaml_content = """
profiles:
  commercial_high:
    provider: voyage
    model:
      name: voyage-code-3
      output_dimension: 2048
    vector_store:
      vector_size: 2048
      distance: dot
""".strip()

    (tmp_path / "code-index-mcp.profiles.yaml").write_text(yaml_content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        Settings,
        "_detect_treesitter_chunker_version",
        lambda self: "treesitter-chunker@2.2.4",
    )

    settings = Settings(semantic_default_profile="legacy-default")
    assert settings.get_semantic_default_profile() == "commercial_high"


def test_default_profile_validation_fails_when_profile_missing(monkeypatch, tmp_path: Path):
    """Explicit default must exist in configured profile map."""
    yaml_content = """
profiles:
  commercial_high:
    provider: voyage
    model:
      name: voyage-code-3
      output_dimension: 2048
    vector_store:
      vector_size: 2048
      distance: dot
""".strip()

    (tmp_path / "code-index-mcp.profiles.yaml").write_text(yaml_content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        Settings,
        "_detect_treesitter_chunker_version",
        lambda self: "treesitter-chunker@2.2.4",
    )

    settings = Settings(semantic_default_profile="oss_high")

    try:
        settings.get_semantic_default_profile()
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "SEMANTIC_DEFAULT_PROFILE" in str(exc)


# ---------------------------------------------------------------------------
# _find_profiles_yaml() — cascade: env var → CWD → package dir
# ---------------------------------------------------------------------------


def test_find_profiles_yaml_uses_env_var_when_file_exists(monkeypatch, tmp_path):
    """MCP_PROFILES_PATH env var is used when it points to an existing file."""
    yaml_file = tmp_path / "override.yaml"
    yaml_file.write_text("profiles: {}")
    monkeypatch.setenv("MCP_PROFILES_PATH", str(yaml_file))
    monkeypatch.chdir(tmp_path)  # CWD has no profiles.yaml
    result = _find_profiles_yaml()
    assert result == str(yaml_file)


def test_find_profiles_yaml_skips_env_var_when_file_missing(monkeypatch, tmp_path):
    """MCP_PROFILES_PATH pointing to a nonexistent file falls through to CWD."""
    monkeypatch.setenv("MCP_PROFILES_PATH", str(tmp_path / "nonexistent.yaml"))
    cwd_yaml = tmp_path / "code-index-mcp.profiles.yaml"
    cwd_yaml.write_text("profiles: {}")
    monkeypatch.chdir(tmp_path)
    result = _find_profiles_yaml()
    assert result == str(cwd_yaml)


def test_find_profiles_yaml_falls_back_to_cwd(monkeypatch, tmp_path):
    """CWD file is returned when env var is not set."""
    monkeypatch.delenv("MCP_PROFILES_PATH", raising=False)
    cwd_yaml = tmp_path / "code-index-mcp.profiles.yaml"
    cwd_yaml.write_text("profiles: {}")
    monkeypatch.chdir(tmp_path)
    result = _find_profiles_yaml()
    assert result == str(cwd_yaml)


def test_find_profiles_yaml_returns_none_when_nothing_found(monkeypatch, tmp_path):
    """Returns None when env var is unset, CWD has no file, and package file absent."""
    import unittest.mock as mock

    monkeypatch.delenv("MCP_PROFILES_PATH", raising=False)
    monkeypatch.chdir(tmp_path)  # empty tmp — no CWD file

    # Patch Path.exists so the package-dir fallback also reports missing
    original_exists = Path.exists
    def fake_exists(self):
        if self.name == "code-index-mcp.profiles.yaml":
            return False
        return original_exists(self)

    with mock.patch.object(Path, "exists", fake_exists):
        result = _find_profiles_yaml()

    assert result is None


# ---------------------------------------------------------------------------
# _expand_env_vars() — ${VAR} and ${VAR:default} substitution
# ---------------------------------------------------------------------------


def test_expand_env_vars_substitutes_known_variable(monkeypatch):
    monkeypatch.setenv("MY_HOST", "vllm-server")
    assert _expand_env_vars("http://${MY_HOST}:8000/v1") == "http://vllm-server:8000/v1"


def test_expand_env_vars_uses_default_when_var_missing(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    assert _expand_env_vars("http://${MISSING_VAR:localhost}:8000") == "http://localhost:8000"


def test_expand_env_vars_env_overrides_default(monkeypatch):
    monkeypatch.setenv("MY_HOST", "prod-host")
    assert _expand_env_vars("http://${MY_HOST:localhost}:8000") == "http://prod-host:8000"


def test_expand_env_vars_multiple_placeholders(monkeypatch):
    monkeypatch.setenv("HOST", "a")
    monkeypatch.setenv("PORT", "9999")
    assert _expand_env_vars("http://${HOST}:${PORT}/v1") == "http://a:9999/v1"


def test_expand_env_vars_no_placeholders_unchanged():
    assert _expand_env_vars("http://localhost:8080/v1") == "http://localhost:8080/v1"


def test_expand_env_vars_empty_string_unchanged():
    assert _expand_env_vars("") == ""
