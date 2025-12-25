import os
import sys
import json
import logging
from typing import Optional, Dict, List, Any
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Add parent dir to path to import utils
sys.path.append(str(Path(__file__).resolve().parents[1]))
from utils.address_utils import normalize_address, generate_address_hash
from utils.placeholder_utils import clean_owner_data

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnrichmentManager:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    def process_listing(self, listing_data: Dict[str, Any], listing_source: Optional[str] = None) -> str:
        """
        Main entry point for scrapers after inserting a listing.
        Checks for existing owner data or creates an enrichment task.
        Returns the generated address_hash.
        """
        raw_address = listing_data.get('address')
        if not raw_address:
            logger.warning("Listing missing address, skipping enrichment check.")
            return None

        normalized = normalize_address(raw_address)
        address_hash = generate_address_hash(normalized)

        # 1. Clean scraped owner data
        scraped_name = listing_data.get('owner_name')
        scraped_email = listing_data.get('owner_email')
        scraped_phone = listing_data.get('owner_phone')
        
        # Handle lists if they were passed (some scrapers return lists)
        if isinstance(scraped_email, list): scraped_email = scraped_email[0] if scraped_email else None
        if isinstance(scraped_phone, list): scraped_phone = scraped_phone[0] if scraped_phone else None

        clean_name, clean_email, clean_phone = clean_owner_data(scraped_name, scraped_email, scraped_phone)

        # 2. Determine if we have "valid" scraped owner data
        has_valid_scraped_data = any([clean_name, clean_email, clean_phone])

        # 3. Handle property_owners table
        if has_valid_scraped_data:
            self._upsert_owner(address_hash, clean_name, clean_email, clean_phone, listing_data.get('mailing_address'), source='scraped', listing_source=listing_source)
            status = 'enriched'
            locked = True
            source_used = 'scraped'
        else:
            status = 'never_checked'
            locked = False
            source_used = None

        # 4. Handle property_owner_enrichment_state table
        self._set_enrichment_state(address_hash, normalized, status, locked, source_used, listing_source=listing_source)
        
        return address_hash

    def _upsert_owner(self, address_hash: str, name: str, email: str, phone: str, mailing: str, source: str, listing_source: Optional[str] = None):
        try:
            data = {
                "address_hash": address_hash,
                "owner_name": name,
                "owner_email": email,
                "owner_phone": phone,
                "mailing_address": mailing,
                "source": source,
                "listing_source": listing_source
            }
            # Only update if fields were None before or if coming from BatchData (Phase 5)
            self.supabase.table("property_owners").upsert(data, on_conflict="address_hash").execute()
            logger.info(f"Upserted owner data for {address_hash[:8]}...")
        except Exception as e:
            logger.error(f"Error upserting owner: {e}")

    def _set_enrichment_state(self, address_hash: str, normalized: str, status: str, locked: bool, source_used: str, listing_source: Optional[str] = None):
        try:
            # Check if exists first to avoid overwriting 'enriched'
            existing = self.supabase.table("property_owner_enrichment_state").select("status, listing_source").eq("address_hash", address_hash).execute()
            
            existing_listing_source = None
            if existing.data:
                existing_listing_source = existing.data[0].get('listing_source')
                if existing.data[0]['status'] in ['enriched', 'no_owner_data']:
                    # Even if status is enriched, we might want to update listing_source if it was missing
                    if listing_source and not existing_listing_source:
                         self.supabase.table("property_owner_enrichment_state").update({"listing_source": listing_source}).eq("address_hash", address_hash).execute()
                    logger.info(f"Enrichment state for {address_hash[:8]} is already {existing.data[0]['status']}, no status update needed.")
                    return

            data = {
                "address_hash": address_hash,
                "normalized_address": normalized,
                "status": status,
                "locked": locked,
                "source_used": source_used,
                "listing_source": listing_source or existing_listing_source,
                "missing_fields": {
                    "owner_name": True,
                    "owner_email": True,
                    "owner_phone": True
                }
            }
            self.supabase.table("property_owner_enrichment_state").upsert(data, on_conflict="address_hash").execute()
            logger.info(f"Set enrichment state to {status} for {address_hash[:8]}...")
        except Exception as e:
            logger.error(f"Error setting enrichment state: {e}")
