# Scrapy settings for trulia_scraper project
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root or trulia_scraper/.env
# This must happen early so scrapy-zyte-api can find ZYTE_API_KEY
project_root = Path(__file__).resolve().parents[2]  # Go up to Scraper_backend
env_path = project_root / '.env'
if not env_path.exists():
    # Try trulia_scraper/.env
    env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)

# Ensure ZYTE_API_KEY is set in environment for scrapy-zyte-api
# scrapy-zyte-api reads directly from os.environ['ZYTE_API_KEY']
# load_dotenv should have already set it, but ensure it's there
zyte_key = os.getenv('ZYTE_API_KEY')
if zyte_key:
    os.environ['ZYTE_API_KEY'] = zyte_key  # Ensure it's set even if load_dotenv didn't work

BOT_NAME = "trulia_scraper"

SPIDER_MODULES = ["trulia_scraper.spiders"]
NEWSPIDER_MODULE = "trulia_scraper.spiders"

ROBOTSTXT_OBEY = False

# Handle 403 errors - don't ignore them, try to parse anyway
HTTPERROR_ALLOWED_CODES = [403]

CONCURRENT_REQUESTS = 1
DOWNLOAD_DELAY = 2
CONCURRENT_REQUESTS_PER_DOMAIN = 1
RANDOMIZE_DOWNLOAD_DELAY = 0.5

ITEM_PIPELINES = {
    # Supabase pipeline enabled - data uploaded directly to Supabase
    'trulia_scraper.pipelines.supabase_pipeline.SupabasePipeline': 400,
}

FEED_EXPORT_ENCODING = "utf-8"

# ==================== Zyte API Configuration ====================
ZYTE_API_KEY = os.getenv('ZYTE_API_KEY')

DOWNLOAD_HANDLERS = {
    "http": "scrapy_zyte_api.ScrapyZyteAPIDownloadHandler",
    "https": "scrapy_zyte_api.ScrapyZyteAPIDownloadHandler",
}

DOWNLOADER_MIDDLEWARES = {
    "scrapy_zyte_api.ScrapyZyteAPIDownloaderMiddleware": 1000,
}

REQUEST_FINGERPRINTER_CLASS = "scrapy_zyte_api.ScrapyZyteAPIRequestFingerprinter"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"