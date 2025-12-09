import os

# ==================== API Configuration ====================
ZYTE_API_KEY = os.getenv('ZYTE_API_KEY', '')
# Correct proxy format for Zyte API
ZYTE_PROXY = f'http://{ZYTE_API_KEY}:@api.zyte.com:8011' if ZYTE_API_KEY else None

# ==================== Spider Settings ====================
ROBOTSTXT_OBEY = False
RETRY_TIMES = 5
DOWNLOAD_DELAY = 0.1
CONCURRENT_REQUESTS = 32

# ==================== HTTP Headers ====================
HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/json',
    'origin': 'https://www.zillow.com',
    'priority': 'u=1, i',
    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
}

# ==================== Output Configuration ====================
OUTPUT_FIELDS = [
    'Name',
    'Beds / Baths',
    'Phone Number',
    'Asking Price',
    'Days On Zillow',
    'Address',
    'YearBuilt',
    'Agent Name',
    'Url',
]

# ==================== URL Constants ====================
BASE_URL = 'https://www.zillow.com'
AGENT_INFO_URL = 'https://www.zillow.com/rentals/api/rcf/v1/rcf'
