"""Shared token estimation helpers."""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Approximate token count without vendor-specific tokenizers."""
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, (len(stripped) + 3) // 4)


__all__ = ["estimate_tokens"]
