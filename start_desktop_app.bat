@echo off
cd /d "%~dp0"

rem Dung Python 3.13 (da cai feedparser/trafilatura/mcp/imagehash)
set PY=C:\Users\cuongle\AppData\Local\Programs\Python\Python313\python.exe
if not exist "%PY%" set PY=python

rem Chay app trong cua so rieng, khong hien cmd den khi nhan launcher bang VBS
start "" "%PY%" desktop_app.py
