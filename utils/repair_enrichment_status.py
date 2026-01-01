#!/usr/bin/env python3
"""
Enrichment Status Repair Script

This script repairs mismatches between:
- property_owners (actual owner data from BatchData)
- property_owner_enrichment_state (status tracking)

It ensures that if owner data exists, the status is correctly set to 'enriched'.
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Set to True for actual changes, False for dry run
DRY_RUN = True

def get_all_property_owners():
    """Fetch all records from property_owners table with actual data."""
    print("📥 Fetching property_owners with data...")
    all_records = []
    page = 0
    while True:
        res = supabase.table("property_owners").select("address_hash, owner_name, owner_email, owner_phone, source, listing_source").range(page*500, (page+1)*500 - 1).execute()
        if not res.data:
            break
        all_records.extend(res.data)
        page += 1
    
    # Filter to only those with actual data
    with_data = [r for r in all_records if r.get('owner_name') or r.get('owner_email') or r.get('owner_phone')]
    print(f"   Found {len(with_data)} records with actual owner data")
    return {r['address_hash']: r for r in with_data if r.get('address_hash')}

def get_all_enrichment_states():
    """Fetch all records from property_owner_enrichment_state table."""
    print("📥 Fetching property_owner_enrichment_state...")
    all_records = []
    page = 0
    while True:
        res = supabase.table("property_owner_enrichment_state").select("address_hash, status, locked, source_used, listing_source").range(page*500, (page+1)*500 - 1).execute()
        if not res.data:
            break
        all_records.extend(res.data)
        page += 1
    print(f"   Found {len(all_records)} records in enrichment_state")
    return {r['address_hash']: r for r in all_records if r.get('address_hash')}

def repair():
    """Run repair to fix status mismatches."""
    print("\n" + "="*60)
    print("🔧 ENRICHMENT STATUS REPAIR")
    if DRY_RUN:
        print("⚠️  DRY RUN MODE - No changes will be made")
    else:
        print("🚨 LIVE MODE - Changes WILL be made")
    print("="*60 + "\n")
    
    owners = get_all_property_owners()
    states = get_all_enrichment_states()
    
    # Find records that need fixing
    to_update = []
    to_insert = []
    
    for hash_val, owner in owners.items():
        state = states.get(hash_val)
        
        if not state:
            # Missing from enrichment_state - need to insert
            to_insert.append({
                'address_hash': hash_val,
                'status': 'enriched',
                'locked': True,
                'checked_at': datetime.now(timezone.utc).isoformat(),
                'source_used': owner.get('source', 'batchdata'),
                'listing_source': owner.get('listing_source')
            })
        elif state['status'] != 'enriched':
            # Wrong status - need to update
            to_update.append({
                'hash': hash_val,
                'old_status': state['status'],
                'source': owner.get('source', 'batchdata')
            })
    
    print(f"📊 Records to UPDATE (wrong status): {len(to_update)}")
    print(f"📊 Records to INSERT (missing state): {len(to_insert)}")
    
    if len(to_update) == 0 and len(to_insert) == 0:
        print("\n✅ No repairs needed! All data is in sync.")
        return
    
    # Perform updates
    updated = 0
    inserted = 0
    
    if to_update:
        print(f"\n🔄 Updating {len(to_update)} records...")
        for item in to_update:
            if DRY_RUN:
                print(f"   [DRY RUN] Would update {item['hash'][:8]}... from '{item['old_status']}' to 'enriched'")
            else:
                try:
                    supabase.table("property_owner_enrichment_state").update({
                        "status": "enriched",
                        "locked": True,
                        "checked_at": datetime.now(timezone.utc).isoformat(),
                        "source_used": item['source']
                    }).eq("address_hash", item['hash']).execute()
                    updated += 1
                    if updated % 50 == 0:
                        print(f"   Updated {updated}/{len(to_update)}...")
                except Exception as e:
                    print(f"   ❌ Error updating {item['hash'][:8]}: {e}")
    
    if to_insert:
        print(f"\n➕ Inserting {len(to_insert)} missing records...")
        for item in to_insert:
            if DRY_RUN:
                print(f"   [DRY RUN] Would insert {item['address_hash'][:8]}... with status 'enriched'")
            else:
                try:
                    supabase.table("property_owner_enrichment_state").upsert(item, on_conflict="address_hash").execute()
                    inserted += 1
                    if inserted % 50 == 0:
                        print(f"   Inserted {inserted}/{len(to_insert)}...")
                except Exception as e:
                    print(f"   ❌ Error inserting {item['address_hash'][:8]}: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📋 REPAIR SUMMARY")
    print("="*60)
    if DRY_RUN:
        print(f"Would update: {len(to_update)} records")
        print(f"Would insert: {len(to_insert)} records")
        print("\n💡 To apply changes, set DRY_RUN = False and run again.")
    else:
        print(f"Updated: {updated} records")
        print(f"Inserted: {inserted} records")
        print("\n✅ Repair complete!")

if __name__ == "__main__":
    # Check for --live flag to enable actual changes
    if "--live" in sys.argv:
        DRY_RUN = False
    
    repair()
    print("\n")
