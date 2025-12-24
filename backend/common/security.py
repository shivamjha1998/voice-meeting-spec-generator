import os
import sys
from cryptography.fernet import Fernet

# Use a persistent key from ENV, or generate one (warning: data loss on restart if not set)
KEY_ENV = os.getenv("ENCRYPTION_KEY")
if not KEY_ENV:
    print("❌ FATAL: ENCRYPTION_KEY is not set. Exiting to prevent data loss.")
    sys.exit(1)

key = KEY_ENV.encode() if isinstance(KEY_ENV, str) else KEY_ENV
cipher_suite = Fernet(key)

def encrypt_value(value: str) -> str:
    """Encrypts a string value (e.g. API tokens)."""
    if not value:
        return None
    return cipher_suite.encrypt(value.encode("utf-8")).decode("utf-8")

def decrypt_value(value: str) -> str:
    """Decrypts a string value."""
    if not value:
        return None
    try:
        return cipher_suite.decrypt(value.encode("utf-8")).decode("utf-8")
    except Exception as e:
        print(f"❌ Decryption failed: {e}")
        return None

def encrypt_data(data: bytes) -> bytes:
    """Encrypts raw binary data (e.g. Audio files)."""
    if not data:
        return b""
    return cipher_suite.encrypt(data)

def decrypt_data(data: bytes) -> bytes:
    """Decrypts raw binary data."""
    if not data:
        return b""
    try:
        return cipher_suite.decrypt(data)
    except Exception as e:
        print(f"❌ Binary Decryption failed: {e}")
        return b""
