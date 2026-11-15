from app.core.security import hash_secret, verify_secret, create_access_token, decode_access_token

def test_secret_hash_roundtrip():
    encoded = hash_secret("123456")
    assert verify_secret("123456", encoded)
    assert not verify_secret("000000", encoded)

def test_token_roundtrip():
    token = create_access_token("user-123", ["mechanic"])
    claims = decode_access_token(token)
    assert claims["sub"] == "user-123"
    assert claims["roles"] == ["mechanic"]
