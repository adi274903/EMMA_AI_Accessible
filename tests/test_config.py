"""Unit tests for config.py (pure dataclasses: no Streamlit, no models, no network)."""

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402


def _reload_config():
    return importlib.reload(config)


def test_defaults_are_repo_relative_and_branded(monkeypatch):
    monkeypatch.delenv("MEDICAL_VECTORSTORE_PATH", raising=False)
    cfg_module = _reload_config()
    cfg = cfg_module.get_default_config()

    # No machine-specific absolute path may be baked in.
    assert cfg.model.vectorstore_path == "./medical_vectorstore"
    assert not os.path.isabs(cfg.model.vectorstore_path)

    assert cfg.ui.app_name == "EMMA AI"
    assert cfg.ui.page_title.startswith("EMMA AI")
    assert cfg.ui.doctor_name == "Clinician"

    # Defaults unchanged from the capstone build.
    assert cfg.generation.top_k_retrieval == 20
    assert cfg.generation.stop_sequences == ["</s>", "<end_of_turn>"]


def test_vectorstore_path_env_override(monkeypatch):
    monkeypatch.setenv("MEDICAL_VECTORSTORE_PATH", "/tmp/some-vectorstore")
    cfg_module = _reload_config()
    assert cfg_module.get_default_config().model.vectorstore_path == "/tmp/some-vectorstore"

    monkeypatch.delenv("MEDICAL_VECTORSTORE_PATH", raising=False)
    _reload_config()


def test_no_credentials_in_config():
    """The config layer must not carry secrets or connection strings."""
    source = open(config.__file__, encoding="utf-8").read().lower()
    for forbidden in ("password=", "pg_conn_str", "api_key", "ghp_", "token="):
        assert forbidden not in source, f"config.py must not contain {forbidden!r}"
