"""Main Trulia FSBO property spider - Refactored"""
import csv
import json
import logging
import os
import re
import scrapy

# Import configuration and utilities
from .trulia_config import (
    HEADERS, OUTPUT_FIELDS, 
    RETRY_TIMES, DOWNLOAD_DELAY, AGENT_INFO_URL
)
from .trulia_parsers import TruliaJSONParser
from ..utils.url_builder import build_rental_url, build_detail_url

logger = logging.getLogger(__name__)


class TruliaSpider(scrapy.Spider):
    """Spider for scraping Trulia FSBO property listings"""
    
    name = "trulia_spider"
    unique_list = []
    
    # Get absolute path to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        # CSV export disabled - data goes directly to Supabase
        # Uncomment below if you want CSV backup
        # 'FEEDS': {
        #     os.path.join(project_root, 'output', 'Trulia_Data.csv'): {
        #         'format': 'csv',
        #         'overwrite': True,
        #         'encoding': 'utf-8',
        #         'fields': OUTPUT_FIELDS,
        #     }
        # },
        'RETRY_TIMES': RETRY_TIMES,
        'DOWNLOAD_DELAY': DOWNLOAD_DELAY,
    }

    def read_input_file(self):
        """Read locations from input/input.csv"""
        input_file_path = os.path.join(self.project_root, 'input', 'input.csv')
        
        if not os.path.exists(input_file_path):
            logger.error(f"Input file not found at {input_file_path}")
            return []

        with open(input_file_path, 'r') as rfile:
            data = list(csv.DictReader(rfile))
            logger.info(f"Loaded {len(data)} locations from input file")
            return data

    def start_requests(self):
        """Generate initial requests for each location or URL"""
        # Check for direct URL from argument or environment variable
        direct_url = getattr(self, 'start_url', None) or os.getenv('TRULIA_FRBO_URL')
        if direct_url:
            logger.info(f"Using Direct URL: {direct_url}")
            meta = {'zipcode': 'Direct URL'}
            meta["zyte_api"] = {"browserHtml": True, "geolocation": "US"}
            yield scrapy.Request(url=direct_url, headers=HEADERS, meta=meta, dont_filter=True)
            return

        file_data = self.read_input_file()
        try:
            for each_row in file_data:
                # Check for direct URL first
                custom_url = each_row.get('url', '').strip()
                location = each_row.get('location', '').strip() or each_row.get('zipcode', '').strip()
                
                if custom_url:
                    final_url = custom_url
                    current_location = "Custom URL" 
                    logger.info(f"Starting request for Custom URL")
                elif location:
                    final_url = build_rental_url(location)
                    current_location = location
                    logger.info(f"Starting request for Location: {location}")
                else:
                    continue
                
                meta = {'zipcode': current_location}
                meta["zyte_api"] = {"browserHtml": True, "geolocation": "US"}
                    
                yield scrapy.Request(url=final_url, headers=HEADERS, meta=meta, dont_filter=True)
                
        except Exception as e:
            logger.error(f"Error in start_requests: {e}", exc_info=True)

    def parse(self, response, **kwargs):
        """Parse search results page"""
        zipcode = response.meta.get('zipcode', 'unknown')
        logger.info(f"Parsing response for location: {zipcode}, Status: {response.status}")
        
        # Log response info for debugging
        if response.status == 403:
            logger.warning(f"Received 403 for {response.url}, but attempting to parse anyway")
            logger.debug(f"Response body length: {len(response.body)}")
            logger.debug(f"Response body preview: {response.body[:500]}")
        
        # Use parser utility to extract listings
        homes_listing = TruliaJSONParser.extract_listings(response, zipcode)
        
        # Process each listing
        for home in homes_listing:
            detail_url = build_detail_url(home)
            if not detail_url:
                continue
            # Pass home data from search results (contains beds/baths/price)
            home_data = home.get('homeData', {})
            meta = {
                'new_detailUrl': detail_url,
                'homeData': home_data  # Pass search results data
            }
            meta["zyte_api"] = {"browserHtml": True, "geolocation": "US"}
            yield response.follow(url=detail_url, headers=HEADERS, callback=self.detail_page, meta=meta)

        # Handle pagination - Update for Trulia
        next_page = response.xpath("//a[contains(@aria-label, 'Next') or contains(text(), 'Next')]/@href").get('')
        if not next_page:
            next_page = response.xpath("//a[@data-testid='pagination-next']/@href").get('')
        if not next_page:
            # Try finding next page number in URL pattern
            current_match = re.search(r'/(\d+)_als/', response.url)
            if current_match:
                current_page = int(current_match.group(1))
                next_page = response.url.replace(f'/{current_page}_als/', f'/{current_page + 1}_als/')
        
        if next_page:
            logger.info(f"Location {zipcode}: Found next page")
            meta = {'zipcode': zipcode}
            meta["zyte_api"] = {"browserHtml": True, "geolocation": "US"}
            yield scrapy.Request(response.urljoin(next_page), headers=HEADERS, callback=self.parse, meta=meta, dont_filter=True)

    def detail_page(self, response):
        """Parse property detail page"""
        try:
            # Get home data from search results (contains beds/baths/price)
            home_data = response.meta.get('homeData', {})
            
            # Use parser utility to extract property details
            item, property_id, beds_bath = TruliaJSONParser.extract_property_details(response, home_data)
            
            if not property_id:
                logger.warning(f"No property ID found for {response.url}")
            
            # Build payload for agent info request (if Trulia has API)
            payload = TruliaJSONParser.build_agent_payload(property_id) if property_id else {}
            
            # Request agent information (if Trulia has similar API)
            meta = {'item': item, 'beds_bath': beds_bath, 'property_id': property_id}
            meta["zyte_api"] = {"browserHtml": True, "geolocation": "US"}
            
            # If Trulia doesn't have agent API, skip this step
            if AGENT_INFO_URL and property_id:
                yield scrapy.Request(
                    url=AGENT_INFO_URL,
                    method='POST',
                    body=json.dumps(payload),
                    headers=HEADERS,
                    callback=self.parse_agent_info,
                    meta=meta,
                    dont_filter=True
                )
            else:
                # Skip agent info, yield item directly
                item['Beds / Baths'] = beds_bath
                item['zpid'] = property_id or ''
                final_item = self._finalize_item(item)
                if final_item:
                    yield final_item

        except Exception as e:
            logger.error(f"Error in detail_page: {e}", exc_info=True)

    def parse_agent_info(self, response):
        """Parse agent information from API response"""
        try:
            item = response.meta['item']
            beds_bath = response.meta['beds_bath']
            property_id = response.meta.get('property_id')
            
            agent_json = response.text
            agent_data = json.loads(agent_json)
            # Update path based on Trulia's API structure
            agentInfo = agent_data.get('propertyInfo', {}).get('agentInfo', {}) or agent_data.get('agentInfo', {})

            item['Name'] = agentInfo.get('businessName', '') or agentInfo.get('name', '')
            item['Beds / Baths'] = beds_bath
            item['Phone Number'] = agentInfo.get('phoneNumber', '') or agentInfo.get('phone', '')
            item['Agent Name'] = agentInfo.get('displayName', '') or agentInfo.get('agentName', '')
            item['zpid'] = property_id or ''
            
            final_item = self._finalize_item(item)
            if final_item:
                yield final_item
                
        except Exception as e:
            logger.error(f"Error in parse_agent_info: {e}", exc_info=True)
    
    def _finalize_item(self, item):
        """Finalize item before yielding"""
        # Normalize whitespace in Address
        if 'Address' in item and item['Address']:
             item['Address'] = " ".join(str(item['Address']).split())
        
        # Strict Filtering: Skip if not in Illinois
        addr = item.get('Address', '')
        if "IL" not in addr and "Illinois" not in addr:
             logger.info(f"⛔ Skipping non-IL listing: {addr}")
             return None
        
        # Remove duplicates using property_id if available, otherwise URL
        unique_id = item.get('zpid') or item.get('Url', '')
        
        if unique_id not in self.unique_list:
            self.unique_list.append(unique_id)
            logger.info(f"SCRAPED: {item.get('Address', 'N/A')} | Price: {item.get('Asking Price', 'N/A')} | Agent: {item.get('Agent Name', 'N/A')}")
            return item
        
        return None