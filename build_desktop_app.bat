@echo off
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PipelineDesktop desktop_app.py
echo.
echo Da tao dist\PipelineDesktop.exe
echo Copy PipelineDesktop.exe vao thu muc D:\pipeline truoc khi chay.
pause
