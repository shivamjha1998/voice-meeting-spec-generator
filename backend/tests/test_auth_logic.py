import pytest
from datetime import timedelta
from jose import jwt
from backend.api.auth import create_access_token, SECRET_KEY, ALGORITHM

def test_create_access_token_structure():
    data = {"sub": "123"}
    token = create_access_token(data)

    # Decode manually to verify
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["sub"] == "123"
    assert "exp" in payload

def test_token_expiration():
    # Ideally we'd mock datetime, but checking if exp is roughly correct works too
    data = {"sub": "test_user"}
    token = create_access_token(data)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    # Check if exp is in the future
    import time
    assert payload["exp"] > time.time()

def test_invalid_token_decode():
    invalid_token = "invalid_token"

    with pytest.raises(Exception):
        jwt.decode(invalid_token, SECRET_KEY, algorithms=[ALGORITHM])
