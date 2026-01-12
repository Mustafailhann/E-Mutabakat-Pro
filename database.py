"""
e-Mutabakat Pro - Veritabanı Modülü
SQLite veritabanı ve kullanıcı yönetimi
"""

import os
import sqlite3
from datetime import datetime

# Veritabanı dosyası
DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')


def get_db_connection():
    """Veritabanı bağlantısı oluştur"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Veritabanını başlat ve tabloları oluştur"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Default admin kullanıcısı oluştur
    create_default_admin()


def create_default_admin():
    """Default admin kullanıcısı oluştur"""
    from auth import hash_password
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Admin var mı kontrol et
    cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone() is None:
        password_hash = hash_password('admin123')
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('admin', password_hash, 'admin')
        )
        conn.commit()
        print("[OK] Default admin kullanicisi olusturuldu")
    
    conn.close()


def get_user_by_id(user_id):
    """ID ile kullanıcı getir"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_username(username):
    """Kullanıcı adı ile kullanıcı getir"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_all_users():
    """Tüm kullanıcıları getir"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, role, created_at, last_login FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    conn.close()
    return users


def create_user(username, password, role='user'):
    """Yeni kullanıcı oluştur"""
    from auth import hash_password
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            (username, password_hash, role)
        )
        conn.commit()
        conn.close()
        return True, "Kullanıcı başarıyla oluşturuldu"
    except sqlite3.IntegrityError:
        return False, "Bu kullanıcı adı zaten mevcut"
    except Exception as e:
        return False, str(e)


def update_user_password(user_id, new_password):
    """Kullanıcı şifresini güncelle"""
    from auth import hash_password
    
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = hash_password(new_password)
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
    conn.commit()
    conn.close()
    return True


def update_user_role(user_id, new_role):
    """Kullanıcı rolünü güncelle"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
    conn.commit()
    conn.close()
    return True


def delete_user(user_id):
    """Kullanıcı sil"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True


def update_last_login(user_id):
    """Son giriş zamanını güncelle"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now(), user_id))
    conn.commit()
    conn.close()
