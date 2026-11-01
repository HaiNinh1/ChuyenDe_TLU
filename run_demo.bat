@echo off
REM Mo giao dien demo Streamlit: nhap dup vao file nay la chay.
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

echo Dang mo giao dien. Trinh duyet se tu mo; neu khong, xem dong Local URL ben duoi.
echo Giu nguyen cua so nay trong luc demo. Muon tat: nhan Ctrl + C.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py

REM Chi dung lai de doc thong bao khi chuong trinh bi loi.
if errorlevel 1 pause
