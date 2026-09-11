"""Cryptographic integrity signature for generated reports.

This signs the report's SHA-256 hash with an RSA key controlled by this
platform, so any tampering with a downloaded PDF is detectable by
re-hashing it and verifying against the embedded signature. It is NOT a
qualified electronic signature under eIDAS — for a signature with that
legal standing, the report hash would need to be submitted to a licensed
Trust Service Provider (e.g. via a PAdES-compliant signing API), which
requires a paid TSP account this project does not yet have.
"""

import base64
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.config import settings


def _load_or_create_key() -> rsa.RSAPrivateKey:
    path = settings.REPORT_SIGNING_KEY_PATH
    if os.path.exists(path):
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    return key


_signing_key = _load_or_create_key()


def sign_message(message: bytes) -> str:
    """Signs an arbitrary message (e.g. a hex-encoded SHA-256 digest) and
    returns the base64-encoded signature."""
    signature = _signing_key.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def public_key_pem() -> str:
    public_key = _signing_key.public_key()
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
