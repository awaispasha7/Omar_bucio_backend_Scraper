#!/usr/bin/env python3
"""
Enrichment Sync Diagnostic Script

This script diagnoses mismatches between:
- property_owners (actual owner data from BatchData)
- property_owner_enrichment_state (status tracking)
- Listing tables (scraper data)

It identifies listings that have owner data but show incorrect status.
"""

import os
import sys
from datetime import datetime
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

def get_all_property_owners():
    """Fetch all records from property_owners table."""
    print("📥 Fetching property_owners...")
    all_records = []
    page = 0
    while True:
        res = supabase.table("property_owners").select("address_hash, owner_name, owner_email, owner_phone, source").range(page*500, (page+1)*500 - 1).execute()
        if not res.data:
            break
        all_records.extend(res.data)
        page += 1
    print(f"   Found {len(all_records)} records in property_owners")
    return {r['address_hash']: r for r in all_records if r.get('address_hash')}

def get_all_enrichment_states():
    """Fetch all records from property_owner_enrichment_state table."""
    print("📥 Fetching property_owner_enrichment_state...")
    all_records = []
    page = 0
    while True:
        res = supabase.table("property_owner_enrichment_state").select("address_hash, status, locked, source_used").range(page*500, (page+1)*500 - 1).execute()
        if not res.data:
            break
        all_records.extend(res.data)
        page += 1
    print(f"   Found {len(all_records)} records in enrichment_state")
    return {r['address_hash']: r for r in all_records if r.get('address_hash')}

def diagnose():
    """Run diagnostic checks."""
    print("\n" + "="*60)
    print("🔍 ENRICHMENT SYNC DIAGNOSTIC")
    print("="*60 + "\n")
    
    owners = get_all_property_owners()
    states = get_all_enrichment_states()
    
    # Analysis
    print("\n📊 ANALYSIS:")
    print("-" * 60)
    
    # 1. Find owners with data but wrong status
    owners_with_data = {h: o for h, o in owners.items() if o.get('owner_name') or o.get('owner_email') or o.get('owner_phone')}
    print(f"Total records with actual owner data: {len(owners_with_data)}")
    
    # 2. Check which have wrong status
    wrong_status = []
    missing_state = []
    correct = 0
    
    for hash_val, owner in owners_with_data.items():
        state = states.get(hash_val)
        if not state:
            missing_state.append(hash_val)
        elif state['status'] != 'enriched':
            wrong_status.append({
                'hash': hash_val,
                'owner_name': owner.get('owner_name', '')[:30],
                'current_status': state['status']
            })
        else:
            correct += 1
    
    print(f"✅ Correctly marked as 'enriched': {correct}")
    print(f"⚠️  Have data but WRONG status: {len(wrong_status)}")
    print(f"❌ Have data but MISSING from enrichment_state: {len(missing_state)}")
    
    # Show examples of wrong status
    if wrong_status:
        print("\n🔧 EXAMPLES OF WRONG STATUS (first 10):")
        for item in wrong_status[:10]:
            print(f"   Hash: {item['hash'][:8]}... | Owner: {item['owner_name'][:20]:<20} | Status: {item['current_status']}")
    
    # 3. Find orphaned states (status=enriched but no data)
    orphaned_states = []
    for hash_val, state in states.items():
        if state['status'] == 'enriched' and hash_val not in owners:
            orphaned_states.append(hash_val)
    
    print(f"\n👻 Orphaned states (enriched but no owner data): {len(orphaned_states)}")
    
    # Summary
    print("\n" + "="*60)
    print("📋 SUMMARY")
    print("="*60)
    print(f"Total issues found: {len(wrong_status) + len(missing_state)}")
    
    if len(wrong_status) + len(missing_state) > 0:
        print("\n💡 Run 'repair_enrichment_status.py' to fix these issues.")
    else:
        print("\n✅ All data is in sync! No repairs needed.")
    
    return {
        'wrong_status': wrong_status,
        'missing_state': missing_state,
        'orphaned_states': orphaned_states,
        'total_owners_with_data': len(owners_with_data),
        'correctly_marked': correct
    }

if __name__ == "__main__":
    results = diagnose()
    print("\n")
