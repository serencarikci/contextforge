from __future__ import annotations

from typing import Protocol


class SecretCipherPort(Protocol):
    def encrypt(self, plaintext: str) -> str: ...

    def decrypt(self, ciphertext: str) -> str: ...
