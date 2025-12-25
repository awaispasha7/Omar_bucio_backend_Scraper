"""
Backfill script to add all existing listings to the enrichment queue.
This will scan all listing tables and add entries to property_owner_enrichment_state
ONLY for listings that don't have owner data anywhere (neither in their source table
nor in property_owners table).
"""

import os
import hashlib
import re
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).parent / '.env')
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def normalize_address(address):
    """Normalize address for consistent hashing."""
    if not address:
        return ""
    addr = str(address).lower().strip()
    addr = re.sub(r'\s+', ' ', addr)
    addr = re.sub(r'[^\w\s]', '', addr)
    return addr

def generate_address_hash(normalized_address):
    """Generate SHA256 hash of normalized address."""
    return hashlib.sha256(normalized_address.encode()).hexdigest()

def has_valid_data(value):
    """Check if a value is valid (not None, not empty, not 'null' string)."""
    if value is None:
        return False
    if isinstance(value, str):
        val = value.strip().lower()
        if val == '' or val == 'null' or val == 'none' or val == 'n/a':
            return False
    if isinstance(value, list):
        return len(value) > 0 and any(has_valid_data(v) for v in value)
    return True

# Define all listing tables with their owner-related columns
LISTING_TABLES = [
    {
        "table": "listings",
        "address_col": "address",
        "source": "ForSaleByOwner",
        "owner_cols": ["owner_name", "owner_emails", "owner_phones"]  # Check these for existing data
    },
    {
        "table": "zillow_fsbo_listings",
        "address_col": "address",
        "source": "Zillow FSBO",
        "owner_cols": ["phone_number"]  # Only phone available
    },
    {
        "table": "zillow_frbo_listings",
        "address_col": "address",
        "source": "Zillow FRBO",
        "owner_cols": ["name", "phone_number"]
    },
    {
        "table": "trulia_listings",
        "address_col": "address",
        "source": "Trulia",
        "owner_cols": ["owner_name", "phones", "emails"]
    },
    {
        "table": "redfin_listings",
        "address_col": "address",
        "source": "Redfin",
        "owner_cols": ["owner_name", "emails", "phones"]
    },
    {
        "table": "hotpads_listings",
        "address_col": "address",
        "source": "Hotpads",
        "owner_cols": ["contact_name", "email", "phone_number"]
    },
    {
        "table": "apartments_frbo_chicago",
        "address_col": "full_address",
        "source": "Apartments",
        "owner_cols": ["owner_name", "owner_email", "phone_numbers"]
    },
]

def get_existing_queue_hashes():
    """Get all address_hashes already in the enrichment queue."""
    try:
        result = supabase.table("property_owner_enrichment_state").select("address_hash").execute()
        return {r['address_hash'] for r in result.data}
    except:
        return set()

def get_property_owners_data():
    """Get address_hashes and their owner data from property_owners table."""
    try:
        result = supabase.table("property_owners").select("address_hash, owner_name, owner_email, owner_phone").execute()
        owners = {}
        for r in result.data:
            has_data = has_valid_data(r.get('owner_name')) or has_valid_data(r.get('owner_email')) or has_valid_data(r.get('owner_phone'))
            owners[r['address_hash']] = has_data
        return owners
    except:
        return {}

def listing_has_owner_data(listing, owner_cols):
    """Check if a listing has any valid owner data in its columns."""
    for col in owner_cols:
        if col in listing and has_valid_data(listing.get(col)):
            return True
    return False

def backfill_table(table_config, existing_hashes, property_owners):
    """Backfill listings from a single table."""
    table = table_config["table"]
    address_col = table_config["address_col"]
    source = table_config["source"]
    owner_cols = table_config["owner_cols"]
    
    print(f"\nProcessing {table}...")
    
    try:
        # Fetch all listings with address and owner columns
        select_cols = [address_col] + owner_cols
        result = supabase.table(table).select(",".join(select_cols)).execute()
        listings = result.data
        
        if not listings:
            print(f"  No listings found in {table}")
            return 0
        
        print(f"  Found {len(listings)} listings")
        
        # Process each listing
        added = 0
        skipped_already_queued = 0
        skipped_has_local_data = 0
        skipped_has_owner_data = 0
        skipped_no_address = 0
        
        batch = []
        
        for listing in listings:
            address = listing.get(address_col)
            if not address:
                skipped_no_address += 1
                continue
            
            normalized = normalize_address(address)
            address_hash = generate_address_hash(normalized)
            
            # Check 1: Already in enrichment queue?
            if address_hash in existing_hashes:
                skipped_already_queued += 1
                continue
            
            # Check 2: Has owner data in THIS listing table?
            if listing_has_owner_data(listing, owner_cols):
                skipped_has_local_data += 1
                continue
            
            # Check 3: Has owner data in property_owners table?
            if address_hash in property_owners and property_owners[address_hash]:
                skipped_has_owner_data += 1
                continue
            
            # This listing needs enrichment - add to batch
            batch.append({
                "address_hash": address_hash,
                "normalized_address": normalized,
                "status": "never_checked",
                "locked": False,
                "listing_source": source,
                "missing_fields": {"owner_name": True, "owner_email": True, "owner_phone": True}
            })
            
            # Mark as existing to avoid duplicates within this run
            existing_hashes.add(address_hash)
            added += 1
            
            # Insert in batches of 50
            if len(batch) >= 50:
                supabase.table("property_owner_enrichment_state").upsert(batch, on_conflict="address_hash").execute()
                batch = []
        
        # Insert remaining
        if batch:
            supabase.table("property_owner_enrichment_state").upsert(batch, on_conflict="address_hash").execute()
        
        print(f"  ADDED to queue: {added}")
        print(f"  Skipped (already in queue): {skipped_already_queued}")
        print(f"  Skipped (has owner data in listing): {skipped_has_local_data}")
        print(f"  Skipped (has owner data in property_owners): {skipped_has_owner_data}")
        print(f"  Skipped (no address): {skipped_no_address}")
        
        return added
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    print("=" * 60)
    print("BACKFILL ENRICHMENT QUEUE")
    print("This will add listings WITHOUT owner data to the queue")
    print("=" * 60)
    
    # Get existing data
    print("\nStep 1: Loading existing enrichment queue...")
    existing_hashes = get_existing_queue_hashes()
    print(f"  Found {len(existing_hashes)} existing entries in queue")
    
    print("\nStep 2: Loading property_owners data...")
    property_owners = get_property_owners_data()
    print(f"  Found {len(property_owners)} entries in property_owners table")
    
    # Process each table
    print("\nStep 3: Processing listing tables...")
    total_added = 0
    for table_config in LISTING_TABLES:
        added = backfill_table(table_config, existing_hashes, property_owners)
        total_added += added
    
    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"  Total listings added to queue: {total_added}")
    
    # Verify final count
    try:
        final = supabase.table("property_owner_enrichment_state").select("*", count="exact").eq("status", "never_checked").limit(0).execute()
        print(f"  Total pending in queue now: {final.count or 0}")
    except Exception as e:
        print(f"  Error getting final count: {e}")
    print("=" * 60)

if __name__ == "__main__":
    main()
