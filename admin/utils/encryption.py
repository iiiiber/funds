"""加密工具"""
import hashlib
import secrets
import base64
from cryptography.fernet import Fernet

# 生成密钥
_key = base64.urlsafe_b64encode(hashlib.sha256(b'fundquant_admin_key_2026').digest())
_fernet = Fernet(_key)

def generate_salt():
    """生成盐值"""
    return secrets.token_hex(16)

def hash_password(password, salt):
    """密码哈希"""
    return hashlib.sha256(f'{password}{salt}'.encode()).hexdigest()

def verify_password(password, salt, hashed):
    """验证密码"""
    return hash_password(password, salt) == hashed

def encrypt_api_key(key):
    """加密API密钥"""
    return _fernet.encrypt(key.encode()).decode()

def decrypt_api_key(encrypted_key):
    """解密API密钥"""
    try:
        return _fernet.decrypt(encrypted_key.encode()).decode()
    except:
        return ''
