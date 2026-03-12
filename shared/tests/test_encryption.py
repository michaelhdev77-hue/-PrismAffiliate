import pytest
from cryptography.fernet import Fernet, InvalidToken

from shared.encryption import encrypt_json, decrypt_json, get_fernet


# Generate valid Fernet keys for testing
KEY_1 = Fernet.generate_key().decode()
KEY_2 = Fernet.generate_key().decode()


class TestGetFernet:
    def test_returns_fernet_instance(self):
        f = get_fernet(KEY_1)
        assert isinstance(f, Fernet)

    def test_str_key(self):
        f = get_fernet(KEY_1)
        assert isinstance(f, Fernet)

    def test_bytes_key(self):
        f = get_fernet(KEY_1.encode())
        assert isinstance(f, Fernet)


class TestRoundtrip:
    def test_simple_dict(self):
        data = {"name": "test", "value": 42}
        encrypted = encrypt_json(data, KEY_1)
        assert isinstance(encrypted, str)
        assert encrypted != str(data)

        decrypted = decrypt_json(encrypted, KEY_1)
        assert decrypted == data

    def test_nested_dict(self):
        data = {
            "user": {
                "name": "Alice",
                "settings": {
                    "theme": "dark",
                    "notifications": True,
                },
            },
        }
        encrypted = encrypt_json(data, KEY_1)
        decrypted = decrypt_json(encrypted, KEY_1)
        assert decrypted == data

    def test_list_values(self):
        data = {"items": [1, 2, 3], "tags": ["a", "b", "c"]}
        encrypted = encrypt_json(data, KEY_1)
        decrypted = decrypt_json(encrypted, KEY_1)
        assert decrypted == data

    def test_mixed_types(self):
        data = {
            "string": "hello",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, "two", 3.0],
            "nested": {"key": "value"},
        }
        encrypted = encrypt_json(data, KEY_1)
        decrypted = decrypt_json(encrypted, KEY_1)
        assert decrypted == data

    def test_empty_dict(self):
        data = {}
        encrypted = encrypt_json(data, KEY_1)
        decrypted = decrypt_json(encrypted, KEY_1)
        assert decrypted == data

    def test_unicode_values(self):
        data = {"message": "Привет, мир! 🌍", "emoji": "🎉"}
        encrypted = encrypt_json(data, KEY_1)
        decrypted = decrypt_json(encrypted, KEY_1)
        assert decrypted == data

    def test_large_data(self):
        data = {"items": list(range(1000))}
        encrypted = encrypt_json(data, KEY_1)
        decrypted = decrypt_json(encrypted, KEY_1)
        assert decrypted == data


class TestCrossKeyDecryption:
    def test_different_key_cannot_decrypt(self):
        data = {"secret": "classified"}
        encrypted = encrypt_json(data, KEY_1)

        with pytest.raises(InvalidToken):
            decrypt_json(encrypted, KEY_2)

    def test_same_key_can_decrypt(self):
        data = {"secret": "classified"}
        encrypted = encrypt_json(data, KEY_1)
        decrypted = decrypt_json(encrypted, KEY_1)
        assert decrypted == data


class TestInvalidData:
    def test_invalid_token_string(self):
        with pytest.raises(Exception):
            decrypt_json("not-a-valid-fernet-token", KEY_1)

    def test_empty_string(self):
        with pytest.raises(Exception):
            decrypt_json("", KEY_1)

    def test_tampered_token(self):
        data = {"key": "value"}
        encrypted = encrypt_json(data, KEY_1)
        # Tamper with the encrypted data
        tampered = encrypted[:-5] + "XXXXX"
        with pytest.raises(Exception):
            decrypt_json(tampered, KEY_1)

    def test_encrypt_produces_different_tokens(self):
        """Each encryption should produce a different token (due to timestamp/IV)."""
        data = {"key": "value"}
        token1 = encrypt_json(data, KEY_1)
        token2 = encrypt_json(data, KEY_1)
        assert token1 != token2
        # But both decrypt to the same data
        assert decrypt_json(token1, KEY_1) == decrypt_json(token2, KEY_1)
