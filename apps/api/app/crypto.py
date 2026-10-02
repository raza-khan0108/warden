import json
from typing import Any

from cryptography.fernet import Fernet

from app.config import settings


class EncryptionManager:
    """Encrypt/decrypt sensitive credentials for storage at rest."""

    def __init__(self, key: str | None = None):
        key_to_use = key or settings.encryption_key
        self.cipher = Fernet(key_to_use.encode() if isinstance(key_to_use, str) else key_to_use)

    def encrypt(self, data: dict[str, Any]) -> str:
        """Encrypt a dict to a string for storage."""
        json_str = json.dumps(data)
        return self.cipher.encrypt(json_str.encode()).decode()

    def decrypt(self, encrypted: str) -> dict[str, Any]:
        """Decrypt a stored string back to a dict."""
        decrypted = self.cipher.decrypt(encrypted.encode())
        return json.loads(decrypted.decode())


def get_encryption_manager() -> EncryptionManager:
    """Factory for dependency injection."""
    return EncryptionManager()
