"""Port for encrypting provider secrets at rest."""

from __future__ import annotations

from typing import Protocol


class SecretCipherPort(Protocol):
    """Symmetric encryption for API keys and similar secrets."""

    def encrypt(self, plaintext: str) -> str:
        """Return a ciphertext string safe to persist."""
        ...

    def decrypt(self, ciphertext: str) -> str:
        """Recover the original plaintext from a ciphertext string."""
        ...
