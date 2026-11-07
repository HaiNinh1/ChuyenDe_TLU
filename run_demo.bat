@echo off
REM Mo giao dien demo: nhap dup vao file nay la chay CA backend (server.py) LAN giao dien React (web\dist).
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

if not exist "web\dist\index.html" (
    echo [LOI] Thieu giao dien da build web\dist. Hay chay: git pull
    pause
    exit /b 1
)

REM Lan dau sau khi cap nhat code: tu cai thu vien con thieu (fastapi, uvicorn...) theo requirements.txt
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, dotenv" 2>nul
if errorlevel 1 (
    echo Dang cai thu vien con thieu, chi mat mot lan...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [LOI] Cai thu vien that bai. Kiem tra mang roi chay lai.
        pause
        exit /b 1
    )
)

echo.
echo Dang mo giao dien tai http://127.0.0.1:8000
echo Giu nguyen cua so nay trong luc demo. Muon tat: nhan Ctrl + C.
echo.
REM Mo trinh duyet sau 3 giay (doi server khoi dong xong)
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000"
".venv\Scripts\python.exe" server.py

REM Chi dung lai de doc thong bao khi chuong trinh bi loi (vi du cong 8000 dang bi chiem).
if errorlevel 1 pause
