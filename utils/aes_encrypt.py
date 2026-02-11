import base64
import os

from base64 import b64encode, b64decode

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from config import configer


def aes_passwd():
    return configer.aes_key


def validate_key_length(key):
    if len(key) not in [16, 24, 32]:
        raise ValueError("Invalid key length. Key must be 16, 24, or 32 bytes long.")


# 使用PBKDF2算法从一个强密码派生出一个密钥
def generate_key(password, filename='aes_key.key'):
    salt = os.urandom(16)  # 盐值应该每次不同，以增加安全性
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 生成一个32字节 (256位) 的密钥
        salt=salt,
        iterations=100000,  # 增加迭代次数可以提高安全性
        backend=default_backend()
    )

    key = kdf.derive(password.encode('utf-8'))

    # 将盐值编码为base64字符串以便存储或传输
    salt_b64 = base64.urlsafe_b64encode(salt).decode('utf-8')

    with open(filename, "w") as file:
        file.write(salt_b64)

    return key


def load_key(password, filename='aes_key.key'):
    try:
        with open(filename, 'r') as f:
            salt_b64 = f.read().strip()

        salt = base64.urlsafe_b64decode(salt_b64)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 生成一个32字节 (256位) 的密钥
            salt=salt,
            iterations=100000,  # 必须与生成密钥时相同
            backend=default_backend()
        )

        # 重新派生密钥
        key = kdf.derive(password.encode('utf-8'))
        return key

    except Exception as e:
        raise ValueError("Failed to load key: " + str(e))


# AES加密函数
def aes_encrypt(key, plaintext):
    validate_key_length(key)  # 确保密钥长度正确

    iv = os.urandom(16)  # 初始化向量
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(plaintext.encode('utf-8')) + padder.finalize()

    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(iv + ciphertext).decode('utf-8')


# AES解密函数
def aes_decrypt(key, ciphertext_b64):
    validate_key_length(key)  # 确保密钥长度正确

    try:
        ciphertext = base64.b64decode(ciphertext_b64)
    except Exception as e:
        raise ValueError("Invalid base64-encoded string") from e

    iv = ciphertext[:16]
    actual_ciphertext = ciphertext[16:]

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    padded_plaintext = decryptor.update(actual_ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

    try:
        return plaintext.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError("Decrypted data is not valid UTF-8 text")
