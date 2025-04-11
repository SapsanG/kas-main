# generate_key.py
from cryptography.fernet import Fernet

key = Fernet.generate_key()
with open("encryption_key.txt", "wb") as key_file:
    key_file.write(key)

print("Ключ успешно сгенерирован и сохранен в encryption_key.txt")