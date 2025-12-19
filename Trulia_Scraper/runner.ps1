# PowerShell script to run Trulia scraper with Zyte API
$env:ZYTE_API_KEY = "e4e968803a7449eea26af6daf9b73a43"
scrapy crawl trulia_spider

