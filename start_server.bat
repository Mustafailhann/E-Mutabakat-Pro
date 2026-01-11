@echo off
chcp 65001 >nul
title e-Mutabakat Pro - Production Server
color 0A

echo =========================================================
echo   e-Mutabakat Pro - Üretim Sunucusu
echo   Waitress WSGI Server
echo =========================================================
echo.

cd /d "%~dp0"

:: Virtual environment aktif et
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment aktif
) else (
    echo [UYARI] venv bulunamadı, sistem Python kullanılıyor
)

:: Ortam değişkenleri
set FLASK_ENV=production
set PYTHONPATH=%~dp0

echo.
echo [SERVER] Başlatılıyor...
echo [SERVER] http://localhost:5000
echo [SERVER] Durdurmak için Ctrl+C
echo.
echo =========================================================
echo.

:: Waitress ile başlat (8 thread, production mode)
python -c "from waitress import serve; from web_app import app; print('✓ Server hazır: http://0.0.0.0:5000'); serve(app, host='0.0.0.0', port=5000, threads=8, url_scheme='https')"

pause
