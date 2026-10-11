"""Encrypt and decrypt service credentials using the configured Fernet key."""

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class CredentialDecryptionError(ValueError):
    """Raised when a stored credential cannot be decrypted."""


def _get_fernet() -> Fernet:
    key = getattr(settings, "CREDENTIALS_ENCRYPTION_KEY", "")
    if not key:
        raise ValueError(
            "CREDENTIALS_ENCRYPTION_KEY must be configured to use credentials."
        )

    try:
        return Fernet(key.encode("ascii"))
    except (UnicodeEncodeError, TypeError, ValueError) as exc:
        raise ValueError("CREDENTIALS_ENCRYPTION_KEY is invalid.") from exc


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext:
        return ""

    try:
        return _get_fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialDecryptionError(
            "Stored credential could not be decrypted; verify the encryption key."
        ) from exc
    except UnicodeDecodeError as exc:
        raise CredentialDecryptionError(
            "Stored credential is not valid UTF-8 after decryption."
        ) from exc
