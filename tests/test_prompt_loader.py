from pathlib import Path

import pytest

from orchestrator.prompt_loader import load_prompt


def test_load_prompt_default():
    prompt = load_prompt("feature_generation")
    assert "gestion de backlog" in prompt


def test_load_prompt_local_override(tmp_path):
    base = Path(__file__).resolve().parent.parent
    default = base / "prompts" / "override_test.yaml"
    local_dir = base / "prompts.local"
    local_dir.mkdir(exist_ok=True)
    local = local_dir / "override_test.yaml"
    try:
        default.write_text("template: default")
        local.write_text("template: local")
        assert load_prompt("override_test") == "local"
    finally:
        if default.exists():
            default.unlink()
        if local.exists():
            local.unlink()


def test_load_prompt_missing():
    with pytest.raises(FileNotFoundError):
        load_prompt("missing_prompt")
