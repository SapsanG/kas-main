# utils/encryption.py
from cryptography.fernet import Fernet

# Генерация ключа шифрования
def generate_key():
    return Fernet.generate_key()

# Шифрование данных
def encrypt_data(data: str, key: bytes) -> bytes:
    cipher_suite = Fernet(key)
    return cipher_suite.encrypt(data.encode())

# Дешифрование данных
def decrypt_data(encrypted_data: bytes, key: bytes) -> str:
    cipher_suite = Fernet(key)
    return cipher_suite.decrypt(encrypted_data).decode()