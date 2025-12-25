"""
Analyze existing listings and identify those missing owner details.
This script will:
1. Count total listings in each table
2. Check which have entries in property_owners with valid data
3. Report which need to be added to the enrichment queue
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
project_root = Path(__file__).resolve().parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Supabase credentials not found!")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define all listing tables and their key columns
LISTING_TABLES = {
    "listings": {"address_col": "address", "link_col": "listing_link", "source_name": "ForSaleByOwner"},
    "zillow_fsbo_listings": {"address_col": "address", "link_col": "detail_url", "source_name": "Zillow FSBO"},
    "zillow_frbo_listings": {"address_col": "address", "link_col": "url", "source_name": "Zillow FRBO"},
    "trulia_listings": {"address_col": "address", "link_col": "listing_link", "source_name": "Trulia"},
    "redfin_listings": {"address_col": "address", "link_col": "listing_link", "source_name": "Redfin"},
    "hotpads_listings": {"address_col": "address", "link_col": "url", "source_name": "Hotpads"},
    "apartments_frbo_chicago": {"address_col": "full_address", "link_col": "listing_url", "source_name": "Apartments"},
}

def get_table_count(table_name):
    """Get total count of records in a table."""
    try:
        result = supabase.table(table_name).select("*", count="exact").limit(0).execute()
        return result.count or 0
    except Exception as e:
        print(f"  Error counting {table_name}: {e}")
        return 0

def get_listings_with_address_hash(table_name):
    """Get count of listings that have an address_hash (already processed by enrichment)."""
    try:
        result = supabase.table(table_name).select("address_hash", count="exact").neq("address_hash", None).limit(0).execute()
        return result.count or 0
    except Exception as e:
        # Column might not exist
        return 0

def get_enrichment_state_count():
    """Get count of records in the enrichment state table by status."""
    try:
        # Total in queue
        total = supabase.table("property_owner_enrichment_state").select("*", count="exact").limit(0).execute()
        
        # By status
        never_checked = supabase.table("property_owner_enrichment_state").select("*", count="exact").eq("status", "never_checked").limit(0).execute()
        enriched = supabase.table("property_owner_enrichment_state").select("*", count="exact").eq("status", "enriched").limit(0).execute()
        failed = supabase.table("property_owner_enrichment_state").select("*", count="exact").eq("status", "failed").limit(0).execute()
        
        return {
            "total": total.count or 0,
            "never_checked": never_checked.count or 0,
            "enriched": enriched.count or 0,
            "failed": failed.count or 0
        }
    except Exception as e:
        print(f"  Error getting enrichment state: {e}")
        return {"total": 0, "never_checked": 0, "enriched": 0, "failed": 0}

def get_property_owners_count():
    """Get count of property owners with actual data."""
    try:
        # Total owners
        total = supabase.table("property_owners").select("*", count="exact").limit(0).execute()
        
        # With name
        with_name = supabase.table("property_owners").select("*", count="exact").neq("owner_name", None).limit(0).execute()
        
        # With email
        with_email = supabase.table("property_owners").select("*", count="exact").neq("owner_email", None).limit(0).execute()
        
        # With phone
        with_phone = supabase.table("property_owners").select("*", count="exact").neq("owner_phone", None).limit(0).execute()
        
        return {
            "total": total.count or 0,
            "with_name": with_name.count or 0,
            "with_email": with_email.count or 0,
            "with_phone": with_phone.count or 0
        }
    except Exception as e:
        print(f"  Error getting property owners: {e}")
        return {"total": 0, "with_name": 0, "with_email": 0, "with_phone": 0}

def main():
    print("=" * 60)
    print("LISTING ANALYSIS - Owner Details Status")
    print("=" * 60)
    
    total_all_listings = 0
    total_with_hash = 0
    
    print("\n[LISTINGS BY TABLE]")
    print("-" * 60)
    
    for table_name, config in LISTING_TABLES.items():
        count = get_table_count(table_name)
        with_hash = get_listings_with_address_hash(table_name)
        total_all_listings += count
        total_with_hash += with_hash
        
        status = "[OK]" if count > 0 else "[--]"
        print(f"  {status} {table_name}: {count} listings ({with_hash} with address_hash)")
    
    print("-" * 60)
    print(f"  TOTAL LISTINGS: {total_all_listings}")
    print(f"  ALREADY LINKED TO ENRICHMENT: {total_with_hash}")
    print(f"  NEED TO BE QUEUED: {total_all_listings - total_with_hash}")
    
    print("\n[ENRICHMENT QUEUE STATUS]")
    print("-" * 60)
    state = get_enrichment_state_count()
    print(f"  Total in queue: {state['total']}")
    print(f"  - Never checked (pending): {state['never_checked']}")
    print(f"  - Enriched: {state['enriched']}")
    print(f"  - Failed: {state['failed']}")
    
    print("\n[PROPERTY OWNERS TABLE]")
    print("-" * 60)
    owners = get_property_owners_count()
    print(f"  Total records: {owners['total']}")
    print(f"  - With name: {owners['with_name']}")
    print(f"  - With email: {owners['with_email']}")
    print(f"  - With phone: {owners['with_phone']}")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    need_queuing = total_all_listings - total_with_hash
    print(f"  Listings needing to be added to queue: {need_queuing}")
    print(f"  Already in queue (pending): {state['never_checked']}")
    print("=" * 60)

if __name__ == "__main__":
    main()
