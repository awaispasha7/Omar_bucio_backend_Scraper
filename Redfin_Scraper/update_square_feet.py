"""
Script to update square feet data in redfin_listings_rows.csv
by scraping the URLs from the CSV file.
"""
import csv
import re
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# CSV file path
CSV_FILE = Path('outputs/redfin_listings_rows.csv')
TEMP_CSV = Path('outputs/redfin_listings_rows_temp.csv')

# Dictionary to store square feet data by URL
square_feet_data = {}


class SquareFeetSpider(scrapy.Spider):
    name = "square_feet_updater"
    
    def __init__(self, urls=None, *args, **kwargs):
        super(SquareFeetSpider, self).__init__(*args, **kwargs)
        self.urls = urls or []
        self.processed = 0
        self.total = len(self.urls)
    
    def start_requests(self):
        """Generate requests for each URL"""
        for url in self.urls:
            if url and url.strip():
                yield scrapy.Request(
                    url=url.strip(),
                    callback=self.parse,
                    meta={
                        "zyte_api": {
                            "browserHtml": True,
                            "geolocation": "US"
                        }
                    },
                    dont_filter=True
                )
    
    def parse(self, response):
        """Extract square feet from the page"""
        url = response.url
        square_feet = ""
        page_text = response.text
        
        self.logger.info(f"Processing: {url}")
        
        # Method 1: Look for patterns like "X sq ft", "X sqft", "X square feet"
        sqft_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*(?:sq\.?\s*ft\.?|sqft|square\s*feet)',
            r'(\d{1,3}(?:,\d{3})*)\s*(?:sq\.?\s*ft)',
            r'(\d{1,3}(?:,\d{3})*)\s*(?:SF|sf)',
        ]
        
        for pattern in sqft_patterns:
            sqft_match = re.search(pattern, page_text, re.IGNORECASE)
            if sqft_match:
                square_feet = sqft_match.group(1).replace(',', '').strip()
                break
        
        # Method 2: Try CSS selectors for square feet
        if not square_feet:
            sqft_selectors = [
                '[data-testid*="sqft"]::text',
                '[data-testid*="square"]::text',
                '[class*="sqft"]::text',
                '[class*="square"]::text',
            ]
            
            for selector in sqft_selectors:
                sqft_text = response.css(selector).get()
                if sqft_text:
                    sqft_match = re.search(r'(\d{1,3}(?:,\d{3})*)', sqft_text.replace(',', ''))
                    if sqft_match:
                        square_feet = sqft_match.group(1).replace(',', '').strip()
                        break
        
        # Method 3: Try XPath
        if not square_feet:
            sqft_xpath = response.xpath('//span[contains(text(), "sq") or contains(text(), "ft")]/text()').get()
            if sqft_xpath:
                sqft_match = re.search(r'(\d{1,3}(?:,\d{3})*)', sqft_xpath.replace(',', ''))
                if sqft_match:
                    square_feet = sqft_match.group(1).replace(',', '').strip()
        
        # Method 4: Look in stats sections
        if not square_feet:
            stats_elements = response.css('[class*="stats"], [class*="Stats"], [data-testid*="stats"]')
            for elem in stats_elements:
                text = ' '.join(elem.css('::text').getall())
                sqft_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:sq\.?\s*ft\.?|sqft)', text, re.IGNORECASE)
                if sqft_match:
                    square_feet = sqft_match.group(1).replace(',', '').strip()
                    break
        
        # Store the result
        square_feet_data[url] = square_feet or ""
        self.processed += 1
        self.logger.info(f"[{self.processed}/{self.total}] {url}: {square_feet or 'Not found'}")


def read_csv_urls():
    """Read URLs from CSV file"""
    urls = []
    if not CSV_FILE.exists():
        print(f"Error: {CSV_FILE} not found!")
        return urls
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get('Url', '').strip()
            if url:
                urls.append(url)
    
    return urls


def update_csv_with_square_feet():
    """Update CSV file with square feet data"""
    if not CSV_FILE.exists():
        print(f"Error: {CSV_FILE} not found!")
        return
    
    # Read existing CSV
    rows = []
    fieldnames = []
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    
    # Update rows with square feet data
    updated_count = 0
    for row in rows:
        url = row.get('Url', '').strip()
        if url in square_feet_data:
            row['Square Feet'] = square_feet_data[url]
            if square_feet_data[url]:
                updated_count += 1
                print(f"Updated {row.get('Name', 'N/A')}: {square_feet_data[url]}")
    
    if updated_count == 0:
        print("Warning: No square feet data was found. Make sure ZYTE_API_KEY is set in your environment.")
    
    # Write updated CSV
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n[SUCCESS] Updated {CSV_FILE} with square feet data")


def main():
    """Main function"""
    print("=" * 60)
    print("Square Feet Updater for Redfin Listings")
    print("=" * 60)
    
    # Read URLs from CSV
    print("\n1. Reading URLs from CSV...")
    urls = read_csv_urls()
    
    if not urls:
        print("No URLs found in CSV file!")
        return
    
    print(f"Found {len(urls)} URLs to process")
    
    # Configure Scrapy settings
    settings = get_project_settings()
    settings.set('LOG_LEVEL', 'INFO')
    settings.set('CONCURRENT_REQUESTS', 4)  # Limit concurrent requests
    settings.set('DOWNLOAD_DELAY', 1)  # Add delay between requests
    
    # Check if Zyte API key is available
    zyte_key = os.getenv('ZYTE_API_KEY', '')
    if not zyte_key:
        print("\nWARNING: ZYTE_API_KEY not found in environment variables.")
        print("The script requires Zyte API to scrape Redfin pages.")
        print("Please set ZYTE_API_KEY in your environment or .env file.")
        print("\nYou can either:")
        print("1. Set ZYTE_API_KEY environment variable")
        print("2. Create a .env file with: ZYTE_API_KEY=your_key_here")
        print("3. Run the main scraper which will populate square feet for new listings")
        return
    
    # Run spider
    print("\n2. Scraping square feet data...")
    process = CrawlerProcess(settings)
    process.crawl(SquareFeetSpider, urls=urls)
    process.start()
    
    # Update CSV
    print("\n3. Updating CSV file...")
    update_csv_with_square_feet()
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()

