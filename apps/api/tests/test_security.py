from app.core.security import decrypt_field, encrypt_field, hash_identifier


def test_encrypt_decrypt_roundtrip() -> None:
    original = "+911234567890"
    encrypted = encrypt_field(original)
    assert encrypted != original
    assert decrypt_field(encrypted) == original


def test_hash_identifier_is_deterministic() -> None:
    assert hash_identifier("+911234567890") == hash_identifier("+911234567890")


def test_hash_identifier_normalizes_email_case_and_whitespace() -> None:
    assert hash_identifier("A@Example.com") == hash_identifier(" a@example.com ")


def test_hash_identifier_differs_for_different_input() -> None:
    assert hash_identifier("+911234567890") != hash_identifier("+919999999999")
