"""
Legacy/Alternative spider for scraping apartments.com FRBO listings.

NOTE: This is an alternative implementation that differs from apartments_frbo.py:
- Uses direct HTTP requests with custom headers (no Zyte API)
- Reads cities from input/location.csv file
- Slower scraping (CONCURRENT_REQUESTS=1, DOWNLOAD_DELAY=4.0)
- Different extraction logic and output format

The main spider is apartments_frbo.py which uses Zyte API and is recommended for production use.
This spider is kept for reference or as a fallback option.
"""

import json
import pandas as pd
import scrapy
import re


class ApartmentsSpider(scrapy.Spider):
    name = 'apartments_scraper'
    # Keep per-spider settings so this project is self-contained
    custom_settings = {
        # apartments.com has anti-bot protection: crawl gently
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 4.0,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 3.0,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 0.5,
        "RETRY_HTTP_CODES": [412, 404, 429, 520, 500, 502, 503, 504, 522, 524, 520],
        "FEEDS": {
            "output/Apartments_Data.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf-8-sig",
            }
        },
    }
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }

    def clean_phone(self, phone: str) -> str:
        """
        Normalize a phone string to digits and '+' only.
        Returns an empty string if nothing useful is found.
        """
        if not phone:
            return ""
        phone = re.sub(r"[^0-9+]", "", phone)
        phone = phone.lstrip("=-")
        # Basic sanity check: require at least 7 digits
        if len(re.sub(r"[^0-9]", "", phone)) < 7:
            return ""
        return phone

    def start_requests(self):
        df = pd.read_csv("input/location.csv")
        for location in df['location']:
            url = f"https://www.apartments.com/{location}/for-rent-by-owner/"
            # url = f"https://www.apartments.com/{location}/for-rent-by-owner/?bb=lth1kggt0J4qwv7lc"
            yield scrapy.Request(url=url, headers=self.headers, callback=self.parse)

    def parse(self, response):
        """
        Parse the search results page and yield one item per listing.

        We now rely primarily on the visible listing cards instead of JSON-LD,
        because the JSON-LD structure on apartments.com can change and is not
        stable across all pages.
        """
        # Try to capture most listing card structures on apartments.com
        listings = response.xpath(
            "//article[contains(@class,'placard') or contains(@class,'property-card')]"
            " | //section[@class='placard-content']//div[contains(@class,'property-wrapper') or contains(@class,'property-actions')]"
        )

        for li in listings:
            # Listing id (from data-listingid when available)
            listing_id = li.xpath("./@data-listingid").get(default="").strip()

            # Name / title
            name = li.xpath(
                ".//a[contains(@class,'property-link')]/text()"
                " | .//a[contains(@class,'placardTitle')]/text()"
            ).get(default="").strip()

            # Detail URL
            url = li.xpath(
                ".//a[contains(@class,'property-link')]/@href"
                " | .//a[contains(@class,'placardTitle')]/@href"
            ).get(default="").strip()

            # Address text on the card (usually a location / address block)
            address = li.xpath(
                ".//div[contains(@class,'location')]/text()"
                " | .//div[contains(@class,'property-address')]/text()"
            ).get(default="").strip()

            # Beds / baths info
            beds_baths = li.xpath(
                ".//div[contains(@class,'bed-range')]/text()"
                " | .//div[contains(@class,'beds')]/text()"
            ).get(default="").strip()

            # Price info
            price = li.xpath(
                ".//div[contains(@class,'price-range')]/text()"
                " | .//div[contains(@class,'price')]/text()"
            ).get(default="").strip()

            # Phone number on the card, if present
            raw_phone = "".join(
                li.xpath(
                    ".//button[contains(@class,'phone') or contains(@class,'phone-link')]//text()"
                ).getall()
            ).strip()
            phone = self.clean_phone(raw_phone)

            # Build base item from card data
            item = {
                "id": listing_id,
                "Name": name,
                "Beds / Baths": beds_baths,
                "Phone Number": phone,
                "Address": address,
                "Price": price,
                "Url": url,
            }

            # If we have a detail URL, follow it to enrich the item with
            # owner contact details and better address/phone information.
            if url:
                yield scrapy.Request(
                    url=url,
                    headers=self.headers,
                    callback=self.parse_detail,
                    meta={"item": item},
                )
            else:
                # No detail URL – still export the card-level data
                yield item

        next_page = response.xpath("//a[@class='next']/@href").get()
        if next_page:
            print("Move to next Page")
            yield scrapy.Request(
                url=next_page,
                headers=self.headers,
                callback=self.parse,
            )

    def parse_detail(self, response):
        """
        Enrich a listing with contact details from the property detail page.

        This method augments the base item created in ``parse`` with:
        - A more reliable phone number
        - Owner / manager / agent name
        - Owner email (when exposed)
        - Mailing / property address
        - Listing time (\"Last updated\" text), when available
        """
        item = dict(response.meta.get("item", {}))

        # -------- PHONE --------
        phone = item.get("Phone Number", "") or ""

        # 1) tel: links
        tel_href = response.xpath("//a[starts-with(@href, 'tel:')]/@href").get()
        if tel_href:
            phone_candidate = self.clean_phone(tel_href.replace("tel:", ""))
            if phone_candidate:
                phone = phone_candidate

        # 2) Elements that look like phone buttons/links
        if not phone:
            phone_texts = response.xpath(
                "//*[contains(translate(@class,'PHONE','phone'),'phone') or "
                "contains(translate(@class,'CALL','call'),'call')]//text()"
            ).getall()
            phone_text = " ".join(t.strip() for t in phone_texts if t.strip())
            phone_candidate = self.clean_phone(phone_text)
            if phone_candidate:
                phone = phone_candidate

        # 3) Fallback: regex over the whole page for a US-style phone number
        if not phone:
            full_text = " ".join(response.xpath("//text()").getall())
            match = re.search(
                r"(\+?1[\s\-\.]?)?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}", full_text
            )
            if match:
                phone_candidate = self.clean_phone(match.group(0))
                if phone_candidate:
                    phone = phone_candidate

        if phone:
            item["Phone Number"] = phone

        # -------- EMAIL --------
        email = ""
        mailto_href = response.xpath(
            "//a[starts-with(@href, 'mailto:')]/@href"
        ).get()
        if mailto_href:
            email = mailto_href.replace("mailto:", "").strip()
            # Strip off any query parameters
            if "?" in email:
                email = email.split("?", 1)[0]

        if not email:
            possible_email = response.xpath(
                "//input[@type='email']/@value | "
                "//input[contains(@name,'email')]/@value"
            ).get()
            if possible_email:
                email = possible_email.strip()

        item["Owner Email"] = email

        # -------- OWNER / MANAGER NAME --------
        owner_name = ""

        name_texts = response.xpath(
            "//*[contains(translate(@class,'CONTACT','contact'),'contact') or "
            "contains(translate(@class,'AGENT','agent'),'agent') or "
            "contains(translate(@class,'MANAGER','manager'),'manager')]"
            "[self::h2 or self::h3 or self::div or self::span]/text()"
        ).getall()
        owner_name = " ".join(t.strip() for t in name_texts if t.strip())

        if not owner_name:
            managed_by = response.xpath(
                "//*[contains(., 'Managed by')]/following::strong[1]/text()"
            ).get()
            if managed_by:
                owner_name = managed_by.strip()

        if not owner_name:
            contact_section = response.xpath(
                "//div[contains(@class,'contact') or contains(@class,'manager')]//text()"
            ).getall()
            owner_name = " ".join(
                t.strip()
                for t in contact_section[:3]
                if t.strip() and len(t.strip()) > 2
            )

        item["Owner Name"] = owner_name

        # -------- MAILING / PROPERTY ADDRESS --------
        addr_parts = response.xpath(
            "//div[contains(@class,'property-address') or "
            "contains(@class,'propertyAddress') or "
            "contains(@class,'addressWrapper')]//text()"
        ).getall()
        mailing_address = " ".join(t.strip() for t in addr_parts if t.strip())

        if not mailing_address:
            address_text = response.xpath(
                "//h1//text() | //div[contains(@class,'breadcrumb')]//text()"
            ).getall()
            mailing_address = " ".join(
                t.strip() for t in address_text[:5] if t.strip()
            )

        item["Mailing Address"] = mailing_address

        # -------- LISTING TIME (freshness) --------
        listing_time = response.xpath(
            "//div[@class='freshnessContainer']"
            "/span[@class='lastUpdated']/span/text()"
        ).get(default="").strip()
        item["Listing Time"] = listing_time

        yield item

