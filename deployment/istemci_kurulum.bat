@echo off
chcp 65001 >nul
title e-Mutabakat Pro - İstemci Kurulumu
color 0B

REM ==============================================================
REM e-Mutabakat Pro - Windows İstemci Kurulum ve Kısayol Oluşturucu
REM Çift tıklayarak masaüstüne kısayol oluşturur
REM ==============================================================

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║       e-Mutabakat Pro - İstemci Kurulumu                     ║
echo ║       Masaüstü Kısayolu Oluşturucu                           ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM ==============================================================
REM SUNUCU IP ADRESİNİ BURAYA GİRİN
REM ==============================================================
set "SERVER_IP=192.168.1.100"
set "SERVER_PORT=80"
set "APP_NAME=e-Mutabakat Pro"

REM Kullanıcıya IP sorma seçeneği
echo [?] Sunucu IP adresi: %SERVER_IP%
echo.
set /p "CUSTOM_IP=Farklı bir IP girmek isterseniz yazın (Enter = varsayılan): "
if not "%CUSTOM_IP%"=="" set "SERVER_IP=%CUSTOM_IP%"

REM URL oluştur
if "%SERVER_PORT%"=="80" (
    set "SERVER_URL=http://%SERVER_IP%"
) else (
    set "SERVER_URL=http://%SERVER_IP%:%SERVER_PORT%"
)

echo.
echo [*] Sunucu adresi: %SERVER_URL%
echo.

REM ==============================================================
REM MASAÜSTÜ YOLUNU BUL
REM ==============================================================
set "DESKTOP=%USERPROFILE%\Desktop"
if not exist "%DESKTOP%" set "DESKTOP=%USERPROFILE%\Masaüstü"
if not exist "%DESKTOP%" (
    echo [X] Masaüstü klasörü bulunamadı!
    pause
    exit /b 1
)

REM ==============================================================
REM KISAYOL OLUŞTUR (VBScript kullanarak)
REM ==============================================================
echo [*] Masaüstü kısayolu oluşturuluyor...

set "SHORTCUT_PATH=%DESKTOP%\%APP_NAME%.lnk"
set "VBS_TEMP=%TEMP%\create_shortcut.vbs"

REM VBScript oluştur
(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = "%SHORTCUT_PATH%"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "%SERVER_URL%"
echo oLink.Description = "%APP_NAME% - Fatura ve Defter Mutabakat Sistemi"
echo oLink.IconLocation = "shell32.dll,14"
echo oLink.Save
) > "%VBS_TEMP%"

REM VBScript çalıştır
cscript //nologo "%VBS_TEMP%"
del "%VBS_TEMP%"

if exist "%SHORTCUT_PATH%" (
    echo [✓] Kısayol oluşturuldu: %SHORTCUT_PATH%
) else (
    echo [X] Kısayol oluşturulamadı!
)

REM ==============================================================
REM BAŞLAT MENÜSÜNE DE EKLE (İsteğe bağlı)
REM ==============================================================
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "STARTMENU_SHORTCUT=%STARTMENU%\%APP_NAME%.lnk"

(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = "%STARTMENU_SHORTCUT%"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "%SERVER_URL%"
echo oLink.Description = "%APP_NAME% - Fatura ve Defter Mutabakat Sistemi"
echo oLink.IconLocation = "shell32.dll,14"
echo oLink.Save
) > "%VBS_TEMP%"

cscript //nologo "%VBS_TEMP%"
del "%VBS_TEMP%"

echo [✓] Başlat menüsüne eklendi
echo.

REM ==============================================================
REM BAĞLANTI TESTİ
REM ==============================================================
echo [*] Sunucu bağlantısı test ediliyor...
ping -n 1 %SERVER_IP% >nul 2>&1
if %ERRORLEVEL%==0 (
    echo [✓] Sunucu erişilebilir!
) else (
    echo [!] Sunucuya ulaşılamadı. Lütfen:
    echo     - Sunucunun açık olduğundan
    echo     - IP adresinin doğru olduğundan
    echo     - Aynı ağda olduğunuzdan emin olun.
)
echo.

REM ==============================================================
REM TAMAMLANDI
REM ==============================================================
echo ╔══════════════════════════════════════════════════════════════╗
echo ║              KURULUM BAŞARIYLA TAMAMLANDI!                   ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo   Masaüstündeki "%APP_NAME%" kısayoluna çift tıklayarak
echo   uygulamaya erişebilirsiniz.
echo.
echo   Sunucu Adresi: %SERVER_URL%
echo.
echo   Giriş için IT yöneticinizden kullanıcı bilgisi alın.
echo.

REM Tarayıcıda açma seçeneği
set /p "OPEN_NOW=Şimdi tarayıcıda açılsın mı? [E/H]: "
if /i "%OPEN_NOW%"=="E" (
    start "" "%SERVER_URL%"
)

echo.
echo Kurulum tamamlandı. Bu pencereyi kapatabilirsiniz.
pause
