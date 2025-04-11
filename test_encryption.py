# test_encryption.py

from app.database import encryption_manager

test_api_key = "mx0vgleGPgIA7yWT3b"
test_api_secret = "19376472889e46828ac65bb6f8ba6923"

# Шифруем тестовые ключи
encrypted_key = encryption_manager.encrypt(test_api_key)
encrypted_secret = encryption_manager.encrypt(test_api_secret)

print(f"Зашифрованный API Key: {encrypted_key}")
print(f"Зашифрованный API Secret: {encrypted_secret}")

# Расшифровываем их обратно
decrypted_key = encryption_manager.decrypt(encrypted_key)
decrypted_secret = encryption_manager.decrypt(encrypted_secret)

print(f"Расшифрованный API Key: {decrypted_key}")
print(f"Расшифрованный API Secret: {decrypted_secret}")