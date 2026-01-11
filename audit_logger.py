"""
e-Mutabakat Pro - Audit & Security Logger
Dosya tabanlı JSONL loglama (append-only)

LOG YAPISI:
- logs/audit.log    : Başarılı giriş/çıkış
- logs/security.log : Başarısız giriş, güvenlik olayları

FORMAT: Her satır bir JSON objesi (JSONL)
"""

import os
import json
from datetime import datetime
from threading import Lock
from collections import defaultdict
import time

# ================================================================
# AYARLAR
# ================================================================
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
AUDIT_LOG = os.path.join(LOG_DIR, 'audit.log')
SECURITY_LOG = os.path.join(LOG_DIR, 'security.log')

# Rate limiting için bellek içi cache
_failed_attempts = defaultdict(list)
_lockouts = {}
_lock = Lock()

# Rate limit ayarları
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 dakika
LOCKOUT_SECONDS = 900  # 15 dakika


# ================================================================
# LOG DİZİNİ OLUŞTUR
# ================================================================
os.makedirs(LOG_DIR, exist_ok=True)


# ================================================================
# YARDIMCI FONKSİYONLAR
# ================================================================
def _write_log(filepath, entry):
    """Log dosyasına yaz (append-only, thread-safe)"""
    try:
        with _lock:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"[LOG ERROR] {filepath}: {e}")


def _get_timestamp():
    """ISO formatında timestamp"""
    return datetime.now().isoformat()


# ================================================================
# RATE LIMITING
# ================================================================
def check_rate_limit(ip_address, username):
    """
    Rate limit kontrolü
    Returns: (allowed: bool, remaining_lockout: int)
    """
    key = f"{ip_address}:{username}"
    now = time.time()
    
    with _lock:
        # Kilitlenme kontrolü
        if key in _lockouts:
            lockout_until = _lockouts[key]
            if now < lockout_until:
                remaining = int(lockout_until - now)
                return False, remaining
            else:
                # Kilitlenme süresi doldu
                del _lockouts[key]
                _failed_attempts[key] = []
        
        # Pencere dışındaki denemeleri temizle
        _failed_attempts[key] = [
            t for t in _failed_attempts[key] 
            if now - t < WINDOW_SECONDS
        ]
        
        return True, 0


def record_failed_attempt(ip_address, username):
    """
    Başarısız deneme kaydet
    Returns: (locked: bool, lockout_duration: int)
    """
    key = f"{ip_address}:{username}"
    now = time.time()
    
    with _lock:
        _failed_attempts[key].append(now)
        
        # Limit aşıldı mı?
        if len(_failed_attempts[key]) >= MAX_ATTEMPTS:
            _lockouts[key] = now + LOCKOUT_SECONDS
            _failed_attempts[key] = []
            return True, LOCKOUT_SECONDS
        
        remaining = MAX_ATTEMPTS - len(_failed_attempts[key])
        return False, remaining


def clear_failed_attempts(ip_address, username):
    """Başarılı girişte denemeleri temizle"""
    key = f"{ip_address}:{username}"
    with _lock:
        if key in _failed_attempts:
            del _failed_attempts[key]
        if key in _lockouts:
            del _lockouts[key]


# ================================================================
# AUDIT LOGGING
# ================================================================
def log_login_success(username, ip_address, user_agent=None):
    """Başarılı giriş logla"""
    entry = {
        'timestamp': _get_timestamp(),
        'event': 'LOGIN_SUCCESS',
        'username': username,
        'ip': ip_address,
        'user_agent': user_agent or 'Unknown'
    }
    _write_log(AUDIT_LOG, entry)
    clear_failed_attempts(ip_address, username)
    print(f"[AUDIT] Giriş: {username} ({ip_address})")


def log_logout(username, ip_address):
    """Çıkış logla"""
    entry = {
        'timestamp': _get_timestamp(),
        'event': 'LOGOUT',
        'username': username,
        'ip': ip_address
    }
    _write_log(AUDIT_LOG, entry)
    print(f"[AUDIT] Çıkış: {username} ({ip_address})")


def log_password_change(username, ip_address, success=True):
    """Şifre değişikliği logla"""
    entry = {
        'timestamp': _get_timestamp(),
        'event': 'PASSWORD_CHANGE_SUCCESS' if success else 'PASSWORD_CHANGE_FAILED',
        'username': username,
        'ip': ip_address
    }
    log_file = AUDIT_LOG if success else SECURITY_LOG
    _write_log(log_file, entry)


# ================================================================
# SECURITY LOGGING
# ================================================================
def log_login_failure(username, ip_address, reason='Invalid credentials'):
    """Başarısız giriş logla"""
    locked, info = record_failed_attempt(ip_address, username)
    
    entry = {
        'timestamp': _get_timestamp(),
        'event': 'LOGIN_FAILURE',
        'username': username,
        'ip': ip_address,
        'reason': reason,
        'locked': locked,
        'lockout_duration': info if locked else None,
        'remaining_attempts': None if locked else info
    }
    _write_log(SECURITY_LOG, entry)
    
    if locked:
        print(f"[SECURITY] HESAP KİLİTLENDİ: {username} ({ip_address}) - {LOCKOUT_SECONDS}s")
    else:
        print(f"[SECURITY] Başarısız giriş: {username} ({ip_address}) - {info} deneme kaldı")
    
    return locked, info


def log_rate_limit_exceeded(ip_address, username):
    """Rate limit aşımı logla"""
    entry = {
        'timestamp': _get_timestamp(),
        'event': 'RATE_LIMIT_EXCEEDED',
        'username': username,
        'ip': ip_address
    }
    _write_log(SECURITY_LOG, entry)
    print(f"[SECURITY] Rate limit aşıldı: {username} ({ip_address})")


def log_security_event(event_type, details, ip_address, username=None):
    """Genel güvenlik olayı logla"""
    entry = {
        'timestamp': _get_timestamp(),
        'event': event_type,
        'username': username,
        'ip': ip_address,
        'details': details
    }
    _write_log(SECURITY_LOG, entry)
    print(f"[SECURITY] {event_type}: {details}")


# ================================================================
# LOG OKUMA (Admin panel için)
# ================================================================
def get_recent_logins(limit=50):
    """Son başarılı girişleri getir"""
    return _read_logs(AUDIT_LOG, ['LOGIN_SUCCESS', 'LOGOUT'], limit)


def get_failed_logins(limit=50):
    """Son başarısız girişleri getir"""
    return _read_logs(SECURITY_LOG, ['LOGIN_FAILURE', 'RATE_LIMIT_EXCEEDED'], limit)


def get_all_security_events(limit=100):
    """Tüm güvenlik olaylarını getir"""
    return _read_logs(SECURITY_LOG, None, limit)


def _read_logs(filepath, event_filter=None, limit=50):
    """Log dosyasından oku"""
    try:
        if not os.path.exists(filepath):
            return []
        
        entries = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if event_filter is None or entry.get('event') in event_filter:
                        entries.append(entry)
                except:
                    pass
        
        # Son N kayıt, en yeni başta
        return entries[-limit:][::-1]
    except Exception as e:
        print(f"[LOG ERROR] Okuma hatası: {e}")
        return []
