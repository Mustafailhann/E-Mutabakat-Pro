@echo off
chcp 65001 >nul
title e-Mutabakat Pro - Hızlı Kurulum
color 0A

REM ==============================================================
REM e-Mutabakat Pro - Tek Tık İstemci Kurulum
REM IT yöneticisi için: SERVER_IP'yi değiştirip dağıtın
REM ==============================================================

REM ╔══════════════════════════════════════════════════════════╗
REM ║  BU DEĞERI SUNUCU IP'NIZE GÖRE DEĞİŞTİRİN!              ║
REM ╚══════════════════════════════════════════════════════════╝
set "SERVER_IP=192.168.1.100"

REM Sessiz kurulum - kullanıcıya sormadan kısayol oluşturur
set "SERVER_URL=http://%SERVER_IP%"
set "APP_NAME=e-Mutabakat Pro"
set "DESKTOP=%USERPROFILE%\Desktop"
if not exist "%DESKTOP%" set "DESKTOP=%USERPROFILE%\Masaüstü"

REM Kısayol oluştur
set "VBS=%TEMP%\shortcut.vbs"
(
echo Set ws = WScript.CreateObject^("WScript.Shell"^)
echo Set sc = ws.CreateShortcut^("%DESKTOP%\%APP_NAME%.lnk"^)
echo sc.TargetPath = "%SERVER_URL%"
echo sc.Description = "e-Mutabakat Pro - Fatura Mutabakat Sistemi"
echo sc.IconLocation = "shell32.dll,14"
echo sc.Save
) > "%VBS%"
cscript //nologo "%VBS%"
del "%VBS%"

REM Başlat menüsüne ekle
set "SM=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
(
echo Set ws = WScript.CreateObject^("WScript.Shell"^)
echo Set sc = ws.CreateShortcut^("%SM%\%APP_NAME%.lnk"^)
echo sc.TargetPath = "%SERVER_URL%"
echo sc.IconLocation = "shell32.dll,14"
echo sc.Save
) > "%VBS%"
cscript //nologo "%VBS%"
del "%VBS%"

REM Bildirim göster
echo.
echo ══════════════════════════════════════════════════════════════
echo   e-Mutabakat Pro kuruldu!
echo   Masaüstündeki kısayolu kullanarak erişebilirsiniz.
echo   Sunucu: %SERVER_URL%
echo ══════════════════════════════════════════════════════════════
echo.

REM Otomatik aç
start "" "%SERVER_URL%"

timeout /t 5
