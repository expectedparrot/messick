"""Loaders for the META / AGENT / README docs surfaced by macaw."""
from __future__ import annotations

from importlib import resources


def _read(name: str) -> str:
    return resources.files(__name__).joinpath(name).read_text(encoding="utf-8")


def load_meta() -> str:
    return _read("META.md")


def load_agent() -> str:
    return _read("AGENT.md")


def load_readme() -> str:
    return _read("README.md")
