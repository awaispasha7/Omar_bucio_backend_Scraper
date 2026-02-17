"""Parser utilities for extracting data from Trulia pages"""
import json
import logging
import re

logger = logging.getLogger(__name__)


class TruliaJSONParser:
    """Handles JSON extraction from Trulia pages"""
    
    @staticmethod
    def extract_listings(response, location):
        """
        Extract property listings from Trulia search page
        
        Args:
            response: Scrapy response object
            location: Location being scraped
            
        Returns:
            list: List of property listing dictionaries
        """
        try:
            # Trulia uses __NEXT_DATA__ with Next.js
            json_text = response.css("#__NEXT_DATA__::text").get('')
            
            if not json_text:
                logger.warning(f"No __NEXT_DATA__ found for location: {location}")
                # Fallback: Try to extract listings from HTML
                return TruliaJSONParser._extract_listings_from_html(response, location)
            
            json_data = json.loads(json_text)
            
            # Navigate to Trulia's structure: props -> searchData -> homes
            homes_listing = []
            
            if 'props' in json_data:
                props = json_data.get('props', {})
                search_data = props.get('searchData', {})
                homes_listing = search_data.get('homes', [])
            
            logger.info(f"Location {location}: Found {len(homes_listing)} listings in JSON")
            
            if len(homes_listing) == 0:
                logger.warning(f"Location {location}: No listings found in JSON, trying HTML extraction")
                return TruliaJSONParser._extract_listings_from_html(response, location)
            
            # Convert Trulia format to our expected format
            # Trulia homes have 'url' or 'homeUrl' field like '/home/address-id'
            formatted_listings = []
            for home in homes_listing:
                # Get URL - Trulia uses 'url' or 'homeUrl'
                detail_url = home.get('url') or home.get('homeUrl') or home.get('detailUrl', '')
                if detail_url:
                    # Make sure it's a full URL
                    if detail_url.startswith('/'):
                        detail_url = f'https://www.trulia.com{detail_url}'
                    # Preserve the full home data so we can extract beds/baths from search results
                    formatted_listings.append({
                        'detailUrl': detail_url,
                        'homeData': home  # Pass full home data for extracting beds/baths
                    })
            
            logger.info(f"Location {location}: Formatted {len(formatted_listings)} listings")
            return formatted_listings
            
        except json.JSONDecodeError as e:
            logger.error(f"Location {location}: JSON decode error: {e}")
            return TruliaJSONParser._extract_listings_from_html(response, location)
        except Exception as e:
            logger.error(f"Location {location}: Error extracting listings: {e}", exc_info=True)
            return TruliaJSONParser._extract_listings_from_html(response, location)
    
    @staticmethod
    def _extract_listings_from_html(response, location):
        """Extract listing URLs from Trulia HTML"""
        try:
            # First, verify we have the rendered page
            page_text = response.text if hasattr(response, 'text') else response.body.decode('utf-8', errors='ignore')
            logger.info(f"HTML length: {len(page_text)} characters")
            
            # Check if page mentions listings count (e.g., "31 homes")
            if 'homes' in page_text.lower() or 'listings' in page_text.lower():
                logger.info("✅ Page appears to contain listing information")
            else:
                logger.warning("⚠️ Page might not contain listings")
            
            listing_links = []
            
            # Method 1: Trulia home links - Trulia uses /home/address-id format
            # Example: /home/6217-s-mason-ave-chicago-il-60638-3943721
            links1 = response.xpath("//a[contains(@href, '/home/')]/@href").getall()
            listing_links.extend(links1)
            
            # Method 2: Also check for /property/ pattern (legacy)
            links2 = response.xpath("//a[contains(@href, '/property/')]/@href").getall()
            listing_links.extend(links2)
            
            # Method 3: Look for all links and filter for home/property URLs
            all_links = response.xpath("//a/@href").getall()
            logger.info(f"Total <a> tags with href: {len(all_links)}")
            for link in all_links:
                if link and ('/home/' in link or '/property/' in link):
                    listing_links.append(link)
            
            # Method 3: Look for data attributes that Trulia might use
            links3 = response.xpath("//a[@data-testid='property-card-link']/@href | //a[@data-testid='property-link']/@href | //a[@data-testid='search-result-link']/@href").getall()
            listing_links.extend(links3)
            
            # Method 4: Look for Trulia's card containers and extract links
            # Trulia cards might be in divs with specific classes
            card_links = response.xpath("""
                //div[contains(@class, 'Card')]//a/@href |
                //div[contains(@class, 'SearchResult')]//a/@href |
                //div[contains(@class, 'PropertyCard')]//a/@href |
                //article//a/@href |
                //li[contains(@class, 'result')]//a/@href
            """).getall()
            listing_links.extend(card_links)
            
            # Method 5: Look for links within listing containers
            # Trulia might wrap listings in specific containers
            container_links = response.xpath("""
                //div[@data-testid='search-results']//a/@href |
                //div[@id='search-results']//a/@href |
                //ul[contains(@class, 'results')]//a/@href |
                //div[contains(@class, 'results-list')]//a/@href
            """).getall()
            listing_links.extend(container_links)
            
            # Method 6: CSS selector approach
            css_links = response.css("a[href*='/property/']::attr(href)").getall()
            listing_links.extend(css_links)
            
            # Method 7: Look for any link that matches Trulia property URL pattern
            # Pattern: /property/address-slug/number
            try:
                pattern_links = response.xpath("//a[matches(@href, '/property/[^/]+/[0-9]+')]/@href").getall()
                listing_links.extend(pattern_links)
            except:
                # matches() might not be available, use contains instead
                pass
            
            # Method 8: Get ALL links from the main content area (more aggressive)
            # Sometimes listings are in the main content but not clearly marked
            main_content_links = response.xpath("""
                //main//a/@href |
                //div[contains(@class, 'content')]//a/@href |
                //div[contains(@class, 'listings')]//a/@href |
                //section//a/@href
            """).getall()
            # Filter for property-like URLs
            for link in main_content_links:
                if link and ('/property/' in link or '/p/' in link or re.match(r'^/\d{8,}$', link.strip())):
                    listing_links.append(link)
            
            logger.info(f"Total links collected before deduplication: {len(listing_links)}")
            
            # Remove duplicates and normalize URLs
            unique_links = []
            seen = set()
            for url in listing_links:
                if not url:
                    continue
                # Normalize URL - handle relative and absolute URLs
                original_url = url
                if url.startswith('/'):
                    url = f'https://www.trulia.com{url}'
                elif not url.startswith('http'):
                    # Skip non-http URLs
                    continue
                
                # Keep Trulia property URLs - check multiple patterns
                is_property_url = False
                if 'trulia.com' in url:
                    # Pattern 1: /home/address-id (Trulia's current format)
                    if '/home/' in url:
                        is_property_url = True
                    # Pattern 2: /property/address-slug/number (legacy)
                    elif '/property/' in url:
                        is_property_url = True
                    # Pattern 3: /p/number (short form)
                    elif '/p/' in url:
                        is_property_url = True
                
                if is_property_url:
                    # Clean up URL - remove fragments and query params for uniqueness
                    clean_url = url.split('#')[0].split('?')[0]
                    if clean_url not in seen:
                        seen.add(clean_url)
                        unique_links.append(clean_url)
                        logger.debug(f"Found property URL: {clean_url}")
            
            homes_listing = [{'detailUrl': url} for url in unique_links]
            logger.info(f"Location {location}: Extracted {len(homes_listing)} listings from HTML")
            
            # Debug: log first few links if found
            if homes_listing:
                logger.info(f"✅ Sample links found (first 3): {[h['detailUrl'] for h in homes_listing[:3]]}")
            else:
                logger.warning(f"❌ No property links found. Total unique links after filtering: {len(unique_links)}")
                # Try to find what's actually in the HTML
                logger.warning(f"No property links found. Checking HTML structure...")
                # Check for common Trulia elements
                cards = response.xpath("//div[contains(@class, 'Card')] | //article | //div[@data-testid]").getall()
                logger.debug(f"Found {len(cards)} potential card elements")
                # Check for any links at all
                all_links_count = len(response.xpath("//a/@href").getall())
                logger.debug(f"Total links on page: {all_links_count}")
                # Sample some links to see what's there
                all_page_links = response.xpath("//a/@href").getall()
                logger.info(f"Total links on page: {len(all_page_links)}")
                sample_links = all_page_links[:30]
                logger.info(f"Sample links (first 30): {sample_links}")
                
                # Check for property-related keywords in links
                property_related = [link for link in all_page_links if link and ('property' in link.lower() or '/p/' in link)]
                logger.info(f"Links containing 'property' or '/p/': {len(property_related)}")
                if property_related:
                    logger.info(f"Property-related links: {property_related[:10]}")
                
                # Save HTML to file for manual inspection
                try:
                    import os
                    debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'debug_html')
                    os.makedirs(debug_dir, exist_ok=True)
                    html_file = os.path.join(debug_dir, f'trulia_page_{location.replace(" ", "_").replace(",", "_")}.html')
                    html_content = response.text if hasattr(response, 'text') else response.body.decode('utf-8', errors='ignore')
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    logger.info(f"💾 Saved HTML ({len(html_content)} chars) to {html_file} for inspection")
                except Exception as e:
                    logger.debug(f"Could not save HTML: {e}")
            
            return homes_listing
        except Exception as e:
            logger.error(f"Location {location}: Error extracting from HTML: {e}", exc_info=True)
            return []
    
    @staticmethod
    def extract_property_details(response, home_data=None):
        """
        Extract property details from Trulia detail page
        
        Args:
            response: Scrapy response object
            home_data: Optional home data from search results (contains beds/baths/price)
            
        Returns:
            dict: Property details including address, price, beds/baths, etc.
        """
        item = {}
        item['Url'] = response.url
        beds_bath = ""  # Initialize beds_bath
        
        try:
            # First, try to use data from search results (more reliable)
            if home_data:
                # Extract beds and baths from search results
                bedrooms = home_data.get('bedrooms', {})
                bathrooms = home_data.get('bathrooms', {})
                
                beds_value = bedrooms.get('value') if isinstance(bedrooms, dict) else bedrooms
                baths_value = bathrooms.get('value') if isinstance(bathrooms, dict) else bathrooms
                beds_formatted = bedrooms.get('formattedValue', '') if isinstance(bedrooms, dict) else ''
                baths_formatted = bathrooms.get('formattedValue', '') if isinstance(bathrooms, dict) else ''
                
                beds_bath = ""
                if beds_formatted and baths_formatted:
                    beds_bath = f"{beds_formatted} {baths_formatted}"
                elif beds_formatted:
                    beds_bath = beds_formatted
                elif baths_formatted:
                    beds_bath = baths_formatted
                elif beds_value and baths_value:
                    beds_bath = f"{beds_value} Beds {baths_value} Baths"
                elif beds_value:
                    beds_bath = f"{beds_value} Beds"
                elif baths_value:
                    beds_bath = f"{baths_value} Baths"
                
                # Extract price from search results
                price_data = home_data.get('price', {})
                if isinstance(price_data, dict):
                    price_formatted = price_data.get('formattedPrice', '')
                    price_value = price_data.get('price')
                    if price_formatted:
                        item['Asking Price'] = price_formatted
                    elif price_value:
                        item['Asking Price'] = f"${price_value:,}"
                
                # Extract address from search results
                location = home_data.get('location', {})
                if isinstance(location, dict):
                    full_location = location.get('fullLocation') or location.get('formattedLocation', '')
                    if full_location:
                        item["Address"] = full_location
                    else:
                        street = location.get('streetAddress', '')
                        city = location.get('city', '')
                        state = location.get('stateCode', '')
                        zip_code = location.get('zipCode', '')
                        if street and city and state:
                            item["Address"] = f"{street}, {city}, {state} {zip_code or ''}".strip()
                
                # Extract year built from search results features
                features = home_data.get('features', {})
                if isinstance(features, dict):
                    highlighted_info = features.get('highlightedInfoAttributes', [])
                    for attr_info in highlighted_info:
                        if isinstance(attr_info, dict):
                            attribute = attr_info.get('attribute', {})
                            if isinstance(attribute, dict):
                                attr_name = attribute.get('formattedName', '')
                                attr_value = attribute.get('formattedValue', '')
                                if 'Year Built' in attr_name and attr_value:
                                    item['YearBuilt'] = attr_value
                                    break
            
            # Try to extract from detail page JSON
            json_text = response.css("#__NEXT_DATA__::text").get('')
            detail_home = {}
            if json_text:
                try:
                    json_data = json.loads(json_text)
                    # Navigate Trulia's JSON structure
                    props = json_data.get('props', {}).get('pageProps', {})
                    detail_home = props.get('property', {}) or props.get('listing', {}) or props.get('home', {})
                except:
                    pass
            
            # Extract property ID
            property_id = (detail_home.get('propertyId') or 
                          detail_home.get('listingId') or 
                          detail_home.get('zpid') or
                          home_data.get('typedHomeId', '') if home_data else '')
            
            # Extract address from detail page if not already set
            if 'Address' not in item or not item['Address']:
                street = detail_home.get('streetAddress') or detail_home.get('address', {}).get('street', '')
                city = detail_home.get('city') or detail_home.get('address', {}).get('city', '')
                state = detail_home.get('state') or detail_home.get('address', {}).get('state', '')
                zip_code = detail_home.get('zipcode') or detail_home.get('address', {}).get('zip', '')
                
                if street and city and state:
                    item["Address"] = f"{street}, {city}, {state} {zip_code or ''}".strip()
                else:
                    # Fallback to XPath
                    address = response.xpath("//h1[contains(@class, 'address')]//text() | //div[contains(@data-testid, 'address')]//text()").getall()
                    item["Address"] = " ".join([text.strip() for text in address if text.strip()]).strip()
            
            # Extract beds and baths from detail page if not already set
            if not beds_bath:
                beds = detail_home.get('bedrooms') or detail_home.get('beds')
                baths = detail_home.get('bathrooms') or detail_home.get('baths')
                
                if beds and baths:
                    beds_bath = f"{beds} Beds {baths} Baths"
                elif beds:
                    beds_bath = f"{beds} Beds"
                elif baths:
                    beds_bath = f"{baths} Baths"
            
            # Extract price from detail page if not already set
            if 'Asking Price' not in item or not item['Asking Price']:
                price = detail_home.get('price') or detail_home.get('listPrice') or detail_home.get('askingPrice')
                
                if price:
                    if isinstance(price, (int, float)):
                        item['Asking Price'] = f"${price:,}"
                    else:
                        item['Asking Price'] = str(price)
                else:
                    # Fallback to XPath
                    price_text = response.xpath("//div[contains(@data-testid, 'price')]//text() | //span[contains(@class, 'price')]//text()").get('')
                    item['Asking Price'] = price_text.strip() if price_text else ''
            
            # Extract year built from detail page if not already set from search results
            if 'YearBuilt' not in item or not item['YearBuilt']:
                item['YearBuilt'] = (detail_home.get('yearBuilt', '') or 
                                   detail_home.get('yearBuilt', '') or
                                   '')
            
            # Extract days on market from detail page
            item['Days On Trulia'] = (detail_home.get('daysOnMarket', '') or 
                                    detail_home.get('daysOnTrulia', '') or
                                    detail_home.get('daysOnSite', '') or
                                    '')
            
            # Owner/contact: Trulia often does not expose these in JSON; try common keys when present
            contact = (detail_home.get('listingContact') or detail_home.get('contactInfo') or 
                       detail_home.get('ownerInfo') or detail_home.get('agentInfo') or {})
            if isinstance(contact, dict):
                name = contact.get('name') or contact.get('displayName') or contact.get('businessName') or ''
                phone = contact.get('phone') or contact.get('phoneNumber') or contact.get('formattedPhone') or ''
                if name and 'Name' not in item:
                    item['Name'] = name
                if phone and 'Phone Number' not in item:
                    item['Phone Number'] = phone
            
            return item, property_id, beds_bath
            
        except Exception as e:
            logger.error(f"Error extracting property details: {e}", exc_info=True)
            return item, None, ""
    
    @staticmethod
    def build_agent_payload(property_id):
        """
        Build payload for agent info API request (if Trulia has similar API)
        
        Args:
            property_id: Trulia Property ID
            
        Returns:
            dict: Payload for API request
        """
        # Update this based on Trulia's actual API structure
        return {
            'propertyId': f'{property_id}',
            'pageType': 'HDP',
        }