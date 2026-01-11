"""
e-Mutabakat Pro - Authentication Modülü
Kullanıcı doğrulama ve oturum yönetimi
"""

import hashlib
import os

# Flask-Login için User sınıfı
class User:
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def is_admin(self):
        return self.role == 'admin'


def hash_password(password):
    """Şifreyi hash'le (bcrypt yerine hashlib kullanılıyor - daha az bağımlılık)"""
    salt = "e-mutabakat-pro-salt-2024"
    return hashlib.sha256((password + salt).encode()).hexdigest()


def verify_password(password, password_hash):
    """Şifreyi doğrula"""
    return hash_password(password) == password_hash


def authenticate_user(username, password):
    """Kullanıcı doğrulama"""
    from database import get_user_by_username, update_last_login
    
    user_data = get_user_by_username(username)
    
    if user_data and verify_password(password, user_data['password_hash']):
        update_last_login(user_data['id'])
        return User(user_data['id'], user_data['username'], user_data['role'])
    
    return None


def load_user(user_id):
    """Flask-Login için kullanıcı yükle"""
    from database import get_user_by_id
    
    user_data = get_user_by_id(user_id)
    
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['role'])
    
    return None
