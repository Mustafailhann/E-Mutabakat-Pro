"""
e-Mutabakat Pro - Production Configuration
Güvenlik ve performans ayarları
SQLite veritabanı, dosya tabanlı loglar
"""

import os
from datetime import timedelta

class ProductionConfig:
    """Üretim ortamı konfigürasyonu"""
    
    # ================================================================
    # GÜVENLİK - SECRET KEY
    # ================================================================
    # Ortam değişkeninden al veya random üret
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or os.urandom(32).hex()
    
    # ================================================================
    # SESSION GÜVENLİĞİ
    # ================================================================
    SESSION_COOKIE_SECURE = True        # Sadece HTTPS üzerinden
    SESSION_COOKIE_HTTPONLY = True      # JavaScript erişimi engelli
    SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF koruması
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # 8 saat oturum
    SESSION_REFRESH_EACH_REQUEST = True
    
    # ================================================================
    # DOSYA YÜKLEME
    # ================================================================
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.getcwd(), 'output')
    
    # ================================================================
    # VERİTABANI (SQLite)
    # ================================================================
    DATABASE_PATH = os.path.join(os.getcwd(), 'users.db')
    
    # ================================================================
    # LOG AYARLARI
    # ================================================================
    LOG_FOLDER = os.path.join(os.getcwd(), 'logs')
    AUDIT_LOG = os.path.join(LOG_FOLDER, 'audit.log')
    SECURITY_LOG = os.path.join(LOG_FOLDER, 'security.log')
    
    # ================================================================
    # RATE LIMITING
    # ================================================================
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 5   # Maksimum deneme
    LOGIN_RATE_LIMIT_WINDOW = 300       # 5 dakika (saniye)
    LOGIN_LOCKOUT_DURATION = 900        # 15 dakika kilitlenme (saniye)
    
    # ================================================================
    # ÜRETİM MODU
    # ================================================================
    DEBUG = False
    TESTING = False
    PREFERRED_URL_SCHEME = 'https'
    

class DevelopmentConfig:
    """Geliştirme ortamı konfigürasyonu"""
    
    SECRET_KEY = 'dev-secret-key-do-not-use-in-production'
    
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.getcwd(), 'output')
    
    DATABASE_PATH = os.path.join(os.getcwd(), 'users.db')
    LOG_FOLDER = os.path.join(os.getcwd(), 'logs')
    
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 10
    LOGIN_RATE_LIMIT_WINDOW = 60
    LOGIN_LOCKOUT_DURATION = 60
    
    DEBUG = True
    TESTING = False


def get_config():
    """Ortam değişkenine göre config seç"""
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig
    return DevelopmentConfig
