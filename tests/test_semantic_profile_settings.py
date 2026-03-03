"""Tests for semantic profile configuration loading in settings."""

from pathlib import Path

from mcp_server.config.settings import Settings


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
      vector_size: 4096
      distance: dot
    normalization:
      l2_normalize_vectors: true
    metadata:
      chunk_schema_version: 1
      embed_schema_version: 1
""".strip()

    (tmp_path / "code-index-mcp.profiles.yaml").write_text(
        yaml_content, encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        Settings,
        "_detect_treesitter_chunker_version",
        lambda self: "treesitter-chunker@2.2.2",
    )

    settings = Settings()
    profiles = settings.get_semantic_profiles_config()

    assert "commercial_high" in profiles
    assert profiles["commercial_high"]["provider"] == "voyage"
    assert profiles["commercial_high"]["vector_dimension"] == 2048
    assert profiles["commercial_high"]["distance_metric"] == "dot"
    assert profiles["commercial_high"]["chunker_version"] == "treesitter-chunker@2.2.2"

    assert profiles["oss_high"]["provider"] == "openai_compatible"
    assert profiles["oss_high"]["vector_dimension"] == 4096
    assert profiles["oss_high"]["normalization_policy"] == "l2"
    assert (
        profiles["oss_high"]["build_metadata"]["openai_api_base"]
        == "http://127.0.0.1:8000"
    )


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

    (tmp_path / "code-index-mcp.profiles.yaml").write_text(
        yaml_content, encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        Settings,
        "_detect_treesitter_chunker_version",
        lambda self: "treesitter-chunker@2.2.2",
    )

    settings = Settings()
    assert settings.get_semantic_default_profile() == "commercial_high"


def test_default_profile_validation_fails_when_profile_missing(
    monkeypatch, tmp_path: Path
):
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

    (tmp_path / "code-index-mcp.profiles.yaml").write_text(
        yaml_content, encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        Settings,
        "_detect_treesitter_chunker_version",
        lambda self: "treesitter-chunker@2.2.2",
    )

    settings = Settings(semantic_default_profile="oss_high")

    try:
        settings.get_semantic_default_profile()
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "SEMANTIC_DEFAULT_PROFILE" in str(exc)
