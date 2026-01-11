@echo off
chcp 65001 >nul
title e-Mutabakat Pro - Sunucu Kurulumu v2.0
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║       e-MUTABAKAT PRO - SUNUCU KURULUM SCRIPTİ               ║
echo ║               Kurumsal Üretim Ortamı v2.0                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: ================================================================
:: ADMIN KONTROLÜ
:: ================================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Bu script YÖNETİCİ olarak çalıştırılmalıdır!
    echo Sağ tık → Yönetici olarak çalıştır
    pause
    exit /b 1
)

:: ================================================================
:: DEĞİŞKENLER
:: ================================================================
set APP_DIR=%~dp0
set VENV_DIR=%APP_DIR%venv
set LOG_DIR=%APP_DIR%logs
set SERVER_PORT=5000
set DOMAIN=emutabakat.local

:: ================================================================
:: 1. PYTHON KONTROLÜ
:: ================================================================
echo [1/10] Python kontrolü...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python bulunamadı. Otomatik kurulum başlıyor...
    echo [!] Python 3.11 indiriliyor...
    
    :: Winget ile kur (Windows 10/11)
    winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements >nul 2>&1
    
    if %errorlevel% neq 0 (
        echo [HATA] Python kurulamadı!
        echo Manuel kurulum: https://python.org/downloads
        pause
        exit /b 1
    )
    
    :: PATH güncelle
    set PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts
    echo [OK] Python kuruldu
) else (
    echo [OK] Python mevcut
)

:: ================================================================
:: 2. VIRTUAL ENVIRONMENT
:: ================================================================
echo.
echo [2/10] Virtual Environment oluşturuluyor...
if not exist "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo [HATA] Venv oluşturulamadı!
        pause
        exit /b 1
    )
)
call "%VENV_DIR%\Scripts\activate.bat"
echo [OK] Venv aktif

:: ================================================================
:: 3. PIP PAKETLERİ
:: ================================================================
echo.
echo [3/10] Pip paketleri yükleniyor...
pip install --upgrade pip >nul 2>&1
pip install flask flask-login waitress python-dateutil openpyxl lxml werkzeug >nul 2>&1
echo [OK] Paketler yüklendi

:: ================================================================
:: 4. LOG DİZİNİ
:: ================================================================
echo.
echo [4/10] Log dizini oluşturuluyor...
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
echo [OK] logs/ dizini hazır

:: ================================================================
:: 5. SECRET KEY OLUŞTURMA
:: ================================================================
echo.
echo [5/10] SECRET_KEY oluşturuluyor...

:: 64 karakter random key üret
for /f "tokens=*" %%a in ('python -c "import secrets; print(secrets.token_hex(32))"') do set SECRET_KEY=%%a

:: Sistem ortam değişkeni olarak kaydet
setx FLASK_SECRET_KEY "%SECRET_KEY%" /M >nul 2>&1
set FLASK_SECRET_KEY=%SECRET_KEY%

echo [OK] SECRET_KEY oluşturuldu ve kayıt edildi

:: ================================================================
:: 6. PRODUCTION CONFIG
:: ================================================================
echo.
echo [6/10] Production config oluşturuluyor...

(
echo """
echo e-Mutabakat Pro - Production Configuration
echo Otomatik oluşturuldu: %date% %time%
echo """
echo.
echo import os
echo from datetime import timedelta
echo.
echo class ProductionConfig:
echo     # Güvenlik
echo     SECRET_KEY = os.environ.get^('FLASK_SECRET_KEY'^) or os.urandom^(32^).hex^(^)
echo.
echo     # Session Güvenliği
echo     SESSION_COOKIE_SECURE = True
echo     SESSION_COOKIE_HTTPONLY = True
echo     SESSION_COOKIE_SAMESITE = 'Strict'
echo     PERMANENT_SESSION_LIFETIME = timedelta^(hours=8^)
echo.
echo     # Dosya Yükleme
echo     MAX_CONTENT_LENGTH = 500 * 1024 * 1024
echo     UPLOAD_FOLDER = os.path.join^(os.getcwd^(^), 'uploads'^)
echo     OUTPUT_FOLDER = os.path.join^(os.getcwd^(^), 'output'^)
echo.
echo     # Üretim Modu
echo     DEBUG = False
echo     TESTING = False
echo     PREFERRED_URL_SCHEME = 'https'
) > "%APP_DIR%config_production.py"

echo [OK] config_production.py oluşturuldu

:: ================================================================
:: 7. WAITRESS BAŞLATICI
:: ================================================================
echo.
echo [7/10] Server başlatıcı oluşturuluyor...

(
echo @echo off
echo chcp 65001 ^>nul
echo title e-Mutabakat Pro Server
echo color 0A
echo.
echo cd /d "%APP_DIR%"
echo call "%VENV_DIR%\Scripts\activate.bat"
echo.
echo set FLASK_ENV=production
echo set FLASK_SECRET_KEY=%SECRET_KEY%
echo.
echo echo ╔══════════════════════════════════════════════════════════════╗
echo echo ║           e-MUTABAKAT PRO - PRODUCTION SERVER                ║
echo echo ║                   Waitress WSGI ^(8 thread^)                   ║
echo echo ╚══════════════════════════════════════════════════════════════╝
echo echo.
echo echo [SERVER] http://localhost:%SERVER_PORT%
echo echo [STATUS] Çalışıyor... ^(Durdurmak için Ctrl+C^)
echo echo.
echo.
echo python -c "from waitress import serve; from web_app import app; serve(app, host='127.0.0.1', port=%SERVER_PORT%, threads=8, url_scheme='https', channel_timeout=120)"
) > "%APP_DIR%start_server.bat"

echo [OK] start_server.bat oluşturuldu

:: ================================================================
:: 8. NSSM SERVİS KURULUMU
:: ================================================================
echo.
echo [8/10] Windows Service scripti oluşturuluyor...

(
echo @echo off
echo chcp 65001 ^>nul
echo title NSSM Service Installer
echo.
echo :: NSSM indir: https://nssm.cc/download
echo :: nssm.exe'yi C:\Windows\System32'e kopyala
echo.
echo echo NSSM ile Windows Service kurulumu...
echo echo.
echo.
echo nssm install eMutabakatPro "%APP_DIR%start_server.bat"
echo nssm set eMutabakatPro AppDirectory "%APP_DIR%"
echo nssm set eMutabakatPro DisplayName "e-Mutabakat Pro Web Server"
echo nssm set eMutabakatPro Description "e-Mutabakat Pro Flask Web Uygulaması - Production"
echo nssm set eMutabakatPro Start SERVICE_AUTO_START
echo nssm set eMutabakatPro AppStdout "%LOG_DIR%\service_stdout.log"
echo nssm set eMutabakatPro AppStderr "%LOG_DIR%\service_stderr.log"
echo nssm set eMutabakatPro AppRotateFiles 1
echo nssm set eMutabakatPro AppRotateBytes 10485760
echo.
echo :: Hata durumunda yeniden başlat
echo nssm set eMutabakatPro AppExit Default Restart
echo nssm set eMutabakatPro AppRestartDelay 5000
echo.
echo nssm start eMutabakatPro
echo.
echo echo.
echo echo [OK] Servis kuruldu ve başlatıldı!
echo echo [INFO] 'services.msc' ile kontrol edebilirsiniz
echo pause
) > "%APP_DIR%install_service.bat"

echo [OK] install_service.bat oluşturuldu

:: ================================================================
:: 9. CADDYFILE
:: ================================================================
echo.
echo [9/10] Caddy reverse proxy config oluşturuluyor...

(
echo # ================================================================
echo # e-Mutabakat Pro - Caddyfile
echo # Kurumsal Üretim Ortamı
echo # ================================================================
echo.
echo # DOMAIN AYARI - DEĞİŞTİRİN!
echo %DOMAIN% {
echo.
echo     # Flask'a reverse proxy
echo     reverse_proxy localhost:%SERVER_PORT% {
echo         header_up X-Real-IP {remote_host}
echo         header_up X-Forwarded-Proto {scheme}
echo     }
echo.
echo     # GÜVENLİK BAŞLIKLARI
echo     header {
echo         # Clickjacking koruması
echo         X-Frame-Options DENY
echo.
echo         # MIME sniffing koruması
echo         X-Content-Type-Options nosniff
echo.
echo         # XSS koruması
echo         X-XSS-Protection "1; mode=block"
echo.
echo         # HSTS - Zorunlu HTTPS
echo         Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
echo.
echo         # Referrer
echo         Referrer-Policy strict-origin-when-cross-origin
echo.
echo         # Server bilgisini gizle
echo         -Server
echo     }
echo.
echo     # Sıkıştırma
echo     encode gzip zstd
echo.
echo     # Login endpoint rate limit
echo     @login path /login
echo     rate_limit @login {
echo         zone login_limit {
echo             key {remote_host}
echo             events 5
echo             window 1m
echo         }
echo     }
echo.
echo     # Loglar
echo     log {
echo         output file %LOG_DIR%/caddy_access.log {
echo             roll_size 10mb
echo             roll_keep 5
echo         }
echo     }
echo }
echo.
echo # HTTP → HTTPS yönlendirme
echo http://%DOMAIN% {
echo     redir https://%DOMAIN%{uri} permanent
echo }
) > "%APP_DIR%Caddyfile"

echo [OK] Caddyfile oluşturuldu

:: ================================================================
:: 10. FIREWALL KURALLARI
:: ================================================================
echo.
echo [10/10] Firewall kuralları ayarlanıyor...

:: Mevcut kuralları temizle
netsh advfirewall firewall delete rule name="e-Mutabakat HTTPS" >nul 2>&1
netsh advfirewall firewall delete rule name="e-Mutabakat Block Flask" >nul 2>&1

:: HTTPS aç
netsh advfirewall firewall add rule name="e-Mutabakat HTTPS" dir=in action=allow protocol=tcp localport=443 >nul 2>&1

:: Flask portunu dışarıya kapat (sadece localhost erişebilir)
netsh advfirewall firewall add rule name="e-Mutabakat Block Flask" dir=in action=block protocol=tcp localport=%SERVER_PORT% remoteip=any >nul 2>&1

echo [OK] Firewall kurallari ayarlandi

:: ================================================================
:: ÖZET
:: ================================================================
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    KURULUM TAMAMLANDI!                       ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo OLUŞTURULAN DOSYALAR:
echo   √ config_production.py  - Flask üretim ayarları
echo   √ start_server.bat      - Waitress server başlatıcı
echo   √ install_service.bat   - Windows Service kurulumu
echo   √ Caddyfile             - Reverse proxy config
echo   √ logs/                 - Log dizini
echo.
echo GÜVENLİK:
echo   √ SECRET_KEY            - 64 karakter random (sistem değişkeni)
echo   √ Firewall 443          - Açık
echo   √ Firewall 5000         - Dışarıya kapalı
echo.
echo SONRAKİ ADIMLAR:
echo   1. Caddy indir: https://caddyserver.com/download
echo   2. NSSM indir: https://nssm.cc/download
echo   3. Caddyfile'da domain/IP'yi düzenle
echo   4. start_server.bat ile test et
echo   5. install_service.bat ile servis olarak kur
echo.
echo SUNUCU URL: https://%DOMAIN%
echo.
pause
