@echo off
REM Mo giao dien demo (server.py + giao dien React): nhap dup vao file nay la chay.
chcp 65001 >nul
REM Luon chay trong thu muc chua file .bat, du mo tu dau.
cd /d "%~dp0"
REM In tieng Viet ra cua so ma khong bi loi ma hoa.
set PYTHONUTF8=1

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay .venv. Hay cai dat theo huong dan trong README.md.
    pause
    exit /b 1
)

echo Dang mo giao dien tai http://127.0.0.1:8000
echo Giu nguyen cua so nay trong luc demo. Muon tat: nhan Ctrl + C.
echo.
REM Mo trinh duyet sau 2 giay (doi server khoi dong xong)
start "" cmd /c "timeout /t 2 >nul & start http://127.0.0.1:8000"
".venv\Scripts\python.exe" server.py

REM Chi dung lai de doc thong bao khi chuong trinh bi loi.
if errorlevel 1 pause
