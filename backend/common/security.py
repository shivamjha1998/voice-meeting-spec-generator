import os
from cryptography.fernet import Fernet

key = os.getenv("ENCRYPTION_KEY")

if not key:
    print("⚠️ WARNING: ENCRYPTION_KEY not set. Using a temporary key (tokens will be lost on restart).")
    key = Fernet.generate_key()

cipher_suite = Fernet(key)

def encrypt_value(value: str) -> str:
    """Encrypts a string value."""
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