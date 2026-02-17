@echo off
echo ============================================
echo  SCRAPER BACKEND (port 8080)
echo  Logs from api_server.py appear BELOW.
echo  Keep this window open when using Find Listings.
echo ============================================
cd /d "%~dp0"
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
set PYTHONUNBUFFERED=1
python api_server.py
pause
