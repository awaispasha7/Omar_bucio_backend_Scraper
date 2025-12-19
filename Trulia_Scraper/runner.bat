@echo off
REM Load Zyte API key from .env file and run scraper
cd /d "%~dp0"
for /f "tokens=2 delims==" %%a in ('findstr /b "ZYTE_API_KEY" trulia_scraper\.env') do set ZYTE_API_KEY=%%a
set ZYTE_API_KEY=%ZYTE_API_KEY:"=%
scrapy crawl trulia_spider
pause