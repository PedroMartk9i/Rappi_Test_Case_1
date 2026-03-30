@echo off
echo ============================================
echo   Rappi Competitive Intelligence - Browser
echo ============================================
echo.
echo Abriendo Chromium con debug port 9222...
echo.
echo INSTRUCCIONES:
echo   1. Inicia sesion en Rappi en el navegador
echo   2. Cuando estes logueado, ejecuta:
echo      python run_demo.py
echo.

start "" "C:\Users\Maest\AppData\Local\ms-playwright\chromium-1161\chrome-win\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\rappi-chrome-profile" "https://www.rappi.com.mx/login"

echo Chromium abierto. Inicia sesion y luego ejecuta: python run_demo.py
pause
