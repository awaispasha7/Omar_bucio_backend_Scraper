import schedule
import time
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)

def run_scraper():
    logging.info("Starting scheduled scraper run...")
    try:
        # Run the scrapy crawler
        # Using 'call' instead of 'system' is generally safer, but system is fine for simple use cases
        # We'll use os.system as per the recommendation for simplicity
        exit_code = os.system('scrapy crawl trulia_spider')
        
        if exit_code == 0:
            logging.info("Scraper finished successfully.")
        else:
            logging.error(f"Scraper failed with exit code: {exit_code}")
            
    except Exception as e:
        logging.error(f"An error occurred while running the scraper: {e}")

def main():
    logging.info("Scheduler started. The scraper will run every 12 hours.")
    
    # Run immediately on start (optional, but good for verification)
    # run_scraper() 
    
    # Schedule the job every 12 hours
    schedule.every(12).hours.do(run_scraper)
    
    # Also print next run time
    next_run = schedule.next_run()
    logging.info(f"Next run scheduled for: {next_run}")

    while True:
        schedule.run_pending()
        time.sleep(60) # Check every minute

if __name__ == "__main__":
    main()