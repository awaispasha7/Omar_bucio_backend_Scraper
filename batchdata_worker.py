import os
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Add shared utils
import sys
project_root = Path(__file__).resolve().parents[0]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from utils.address_utils import normalize_address
from utils.placeholder_utils import clean_owner_data

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load env vars
load_dotenv()

class BatchDataWorker:
    def __init__(self):
        # Supabase config
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials missing.")
        self.supabase: Client = create_client(url, key)
        
        # BatchData config
        self.api_key = os.getenv("BATCHDATA_API_KEY")
        self.api_enabled = os.getenv("BATCHDATA_ENABLED", "false").lower() == "true"
        self.daily_limit = int(os.getenv("BATCHDATA_DAILY_LIMIT", "50"))
        self.api_url = "https://api.batchdata.com/api/v1/property/skip-trace"
        
    def check_daily_usage(self) -> int:
        """Counts how many BatchData calls were made in the last 24 hours."""
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        try:
            response = self.supabase.table("property_owner_enrichment_state") \
                .select("id", count="exact") \
                .eq("source_used", "batchdata") \
                .gte("checked_at", yesterday) \
                .execute()
            return response.count or 0
        except Exception as e:
            logger.error(f"Error checking daily usage: {e}")
            return 9999 # Safety: assume limit reached on error
            
    def get_pending_properties(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetches properties that need enrichment and are not locked."""
        try:
            response = self.supabase.table("property_owner_enrichment_state") \
                .select("*") \
                .eq("status", "never_checked") \
                .eq("locked", False) \
                .limit(limit) \
                .execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching pending properties: {e}")
            return []

    def parse_address_string(self, address: str) -> Dict[str, str]:
        """Simple parser to split full address into street, city, state, zip."""
        # Expected format: "Street Address, City, State Zip"
        parts = [p.strip() for p in address.split(',')]
        result = {"street": "", "city": "", "state": "", "zip": ""}
        
        if len(parts) >= 3:
            result["street"] = parts[0]
            result["city"] = parts[1]
            state_zip = parts[2].split()
            if len(state_zip) >= 2:
                result["state"] = state_zip[0]
                result["zip"] = state_zip[1]
            elif len(state_zip) == 1:
                result["state"] = state_zip[0]
        elif len(parts) == 2:
            result["street"] = parts[0]
            result["city"] = parts[1]
            
        return result

    def call_batchdata(self, address_str: str) -> Optional[Dict[str, Any]]:
        """Calls the BatchData Skip Trace API v1 (using v3-style payload supported by v1) for a single address."""
        if not self.api_key:
            logger.error("BATCHDATA_API_KEY is missing. Skipping call.")
            return None
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        addr_parts = self.parse_address_string(address_str)
        
        payload = {
            "requests": [
                {
                    "propertyAddress": {
                        "street": addr_parts["street"],
                        "city": addr_parts["city"],
                        "state": addr_parts["state"],
                        "zip": addr_parts["zip"]
                    }
                }
            ]
        }
        
        try:
            logger.info(f"Calling BatchData v1 for: {address_str}")
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"BatchData API v1 error: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response body: {e.response.text}")
            return None

    def run_enrichment(self, max_runs: int = 2):
        """Main loop to process pending enrichments."""
        if not self.api_enabled:
            logger.warning("BatchData enrichment is DISABLED (BATCHDATA_ENABLED=false).")
            return

        current_usage = self.check_daily_usage()
        if current_usage >= self.daily_limit:
            logger.warning(f"Daily limit reached ({current_usage}/{self.daily_limit}). Stopping.")
            return

        pending = self.get_pending_properties(limit=max_runs)
        if not pending:
            logger.info("No pending properties for enrichment.")
            return

        logger.info(f"Starting enrichment for {len(pending)} properties. Current usage: {current_usage}")

        for prop in pending:
            address_hash = prop['address_hash']
            address = prop['normalized_address']
            listing_source = prop.get('listing_source')
            
            # 1. Update status to 'checking'
            self.supabase.table("property_owner_enrichment_state") \
                .update({"status": "checking", "checked_at": datetime.now().isoformat()}) \
                .eq("address_hash", address_hash).execute()

            # 2. Call BatchData v1
            result = self.call_batchdata(address)
            
            # success logic for v1 (based on sandbox test)
            if result and result.get('status', {}).get('code') == 200:
                results_obj = result.get('results', {})
                persons_list = results_obj.get('persons', [])
                
                if not persons_list:
                    self._mark_failed(address_hash, "No persons found in response")
                    continue
                    
                first_person = persons_list[0]
                # Check for match (v1 meta structure)
                person_matched = first_person.get('meta', {}).get('matched')
                if not person_matched:
                    self._mark_failed(address_hash, "No match found for this person")
                    continue

                # Extract Owner Name
                # Priority 1: property.owner.name
                # Priority 2: first_person.name
                full_name = None
                owner_obj = first_person.get('property', {}).get('owner', {})
                if owner_obj:
                    o_name = owner_obj.get('name', {})
                    if o_name.get('first') or o_name.get('last'):
                        full_name = f"{o_name.get('first', '')} {o_name.get('last', '')}".strip()
                
                if not full_name:
                    p_name = first_person.get('name', {})
                    full_name = f"{p_name.get('first', '')} {p_name.get('last', '')}".strip()

                # Extract Emails and Phones
                emails = [e.get('email') for e in first_person.get('emails', []) if e.get('email')]
                # v1 uses 'phoneNumbers' instead of 'phones'
                phones = [p.get('number') for p in first_person.get('phoneNumbers', []) if p.get('number')]

                email = emails[0] if emails else None
                phone = phones[0] if phones else None
                
                clean_name, clean_email, clean_phone = clean_owner_data(full_name, email, phone)
                
                if any([clean_name, clean_email, clean_phone]):
                    # Save to property_owners
                    self.supabase.table("property_owners").upsert({
                        "address_hash": address_hash,
                        "owner_name": clean_name or full_name,
                        "owner_email": clean_email,
                        "owner_phone": clean_phone,
                        "source": "batchdata",
                        "listing_source": listing_source,
                        "raw_response": result
                    }, on_conflict="address_hash").execute()
                    
                    # Update state
                    req_id = results_obj.get('meta', {}).get('requestId')
                    self.supabase.table("property_owner_enrichment_state").update({
                        "status": "enriched",
                        "locked": True,
                        "source_used": "batchdata",
                        "batchdata_request_id": req_id
                    }).eq("address_hash", address_hash).execute()
                    logger.info(f"Successfully enriched v1: {address}")
                else:
                    self._mark_failed(address_hash, "No valid contact info in response")
            else:
                reason = "BatchData API error or empty status"
                if result:
                    reason = result.get('status', {}).get('text', reason)
                self._mark_failed(address_hash, reason)

    def _mark_failed(self, address_hash: str, reason: str):
        """Helper to mark enrichment as failed."""
        self.supabase.table("property_owner_enrichment_state").update({
            "status": "no_owner_data",
            "locked": True,
            "failure_reason": reason,
            "source_used": "batchdata"
        }).eq("address_hash", address_hash).execute()
        logger.warning(f"Enrichment marked as failed: {reason}")

if __name__ == "__main__":
    worker = BatchDataWorker()
    # For testing, we only process 2 listings as requested
    worker.run_enrichment(max_runs=2)
