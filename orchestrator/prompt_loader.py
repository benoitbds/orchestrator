"""Utility for loading system prompts from YAML files."""
from __future__ import annotations

from pathlib import Path
from typing import Final

import yaml

# Base directory of the project (repository root)
_BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent


def load_prompt(prompt_name: str) -> str:
    """Load a prompt template by name.

    The function searches for a YAML file in two locations:

    1. ``prompts.local/{prompt_name}.yaml`` – for local overrides.
    2. ``prompts/{prompt_name}.yaml`` – the default prompts committed to Git.

    The YAML file must contain a ``template`` key whose value is returned.

    Args:
        prompt_name: Name of the prompt file without extension.

    Returns:
        The prompt template string.

    Raises:
        FileNotFoundError: If no matching file is found in either directory.
        KeyError: If the YAML file exists but does not define ``template``.
    """
    for folder in ("prompts.local", "prompts"):
        path = _BASE_DIR / folder / f"{prompt_name}.yaml"
        if path.exists():
            data = yaml.safe_load(path.read_text()) or {}
            template = data.get("template")
            if template is None:
                raise KeyError(f"'template' key missing in {path}")
            return str(template)
    raise FileNotFoundError(
        f"Prompt '{prompt_name}' not found in 'prompts.local' or 'prompts' directories"
    )
