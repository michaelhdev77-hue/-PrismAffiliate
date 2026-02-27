import json
from cryptography.fernet import Fernet


def get_fernet(key: str) -> Fernet:
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_json(data: dict, key: str) -> str:
    return get_fernet(key).encrypt(json.dumps(data).encode()).decode()


def decrypt_json(token: str, key: str) -> dict:
    return json.loads(get_fernet(key).decrypt(token.encode()))
