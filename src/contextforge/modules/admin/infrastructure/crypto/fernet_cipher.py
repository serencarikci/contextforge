from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from contextforge.modules.admin.domain.exceptions import SecretDecryptionError


class FernetSecretCipher:
    def __init__(self, secret_key: str) -> None:
        digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise SecretDecryptionError("Stored provider secret could not be decrypted.") from exc
