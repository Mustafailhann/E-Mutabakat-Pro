@echo off
chcp 65001 >nul
title e-Mutabakat Pro - İstemci Kurulumu
color 0B

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║       e-MUTABAKAT PRO - İSTEMCİ KURULUMU                     ║
echo ║            Masaüstü Kısayol Oluşturucu                       ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: ================================================================
:: AYARLAR - SİSTEM YÖNETİCİSİ BU KISMI DÜZENLEMELİ
:: ================================================================
set SERVER_URL=https://emutabakat.local
set SHORTCUT_NAME=e-Mutabakat Pro

:: ================================================================
:: MASAÜSTÜ YOLU
:: ================================================================
set DESKTOP=%USERPROFILE%\Desktop

echo [1/3] Kısayol oluşturuluyor...

:: ================================================================
:: KISA YOL OLUŞTUR (VBScript ile)
:: ================================================================
set VBS_FILE=%TEMP%\emutabakat_shortcut.vbs

(
echo Set WshShell = WScript.CreateObject^("WScript.Shell"^)
echo strDesktop = WshShell.SpecialFolders^("Desktop"^)
echo Set oShortcut = WshShell.CreateShortcut^(strDesktop ^& "\%SHORTCUT_NAME%.lnk"^)
echo oShortcut.TargetPath = "%SERVER_URL%"
echo oShortcut.Description = "e-Mutabakat Pro - Fatura ve KDV Analizi"
echo oShortcut.IconLocation = "shell32.dll,13"
echo oShortcut.Save
) > "%VBS_FILE%"

cscript //nologo "%VBS_FILE%" 2>nul
del "%VBS_FILE%" >nul 2>&1

:: Kontrol
if exist "%DESKTOP%\%SHORTCUT_NAME%.lnk" (
    echo [OK] Kısayol oluşturuldu
) else (
    :: Alternatif yöntem - URL kısayolu
    echo [URL] > "%DESKTOP%\%SHORTCUT_NAME%.url"
    echo URL=%SERVER_URL% >> "%DESKTOP%\%SHORTCUT_NAME%.url"
    echo IconIndex=0 >> "%DESKTOP%\%SHORTCUT_NAME%.url"
    echo IconFile=shell32.dll >> "%DESKTOP%\%SHORTCUT_NAME%.url"
    
    if exist "%DESKTOP%\%SHORTCUT_NAME%.url" (
        echo [OK] URL kısayolu oluşturuldu
    ) else (
        echo [HATA] Kısayol oluşturulamadı!
        pause
        exit /b 1
    )
)

echo.
echo [2/3] Kısayol doğrulanıyor...
echo [OK] Masaüstü: %DESKTOP%\%SHORTCUT_NAME%

echo.
echo [3/3] Kurulum tamamlandı!

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    KURULUM TAMAMLANDI!                       ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo Masaüstünüzde "%SHORTCUT_NAME%" kısayolu oluşturuldu.
echo.
echo KULLANIM:
echo   1. Masaüstündeki "%SHORTCUT_NAME%" simgesine çift tıklayın
echo   2. Tarayıcınız otomatik açılacak
echo   3. Kullanıcı adı ve şifrenizle giriş yapın
echo.
echo SUNUCU: %SERVER_URL%
echo.
echo ═══════════════════════════════════════════════════════════════
echo.
pause
