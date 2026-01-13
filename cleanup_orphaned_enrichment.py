"""
Script to clean up orphaned enrichment records.
Orphaned records are those in property_owner_enrichment_state that have no corresponding
listings in any of the listings tables.

Run this script periodically or after bulk deletions to keep the enrichment table clean.
"""
import os
import sys
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# All listing tables that should be checked
LISTING_TABLES = [
    'listings',  # FSBO
    'apartments_frbo',
    'trulia_listings',
    'redfin_listings',
    'zillow_frbo_listings',
    'zillow_fsbo_listings',
    'hotpads_listings',
    'other_listings'
]

def cleanup_orphaned_enrichment(dry_run=True):
    """
    Find and optionally delete enrichment records that have no corresponding listings.
    
    Args:
        dry_run: If True, only report what would be deleted without actually deleting
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        logger.error("Supabase credentials missing. Set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        return
    
    supabase: Client = create_client(url, key)
    
    logger.info("=" * 60)
    logger.info("ORPHANED ENRICHMENT CLEANUP")
    logger.info("=" * 60)
    logger.info(f"Mode: {'DRY RUN (no deletions)' if dry_run else 'LIVE (will delete)'}")
    logger.info("")
    
    # Step 1: Get all address_hashes from enrichment table
    logger.info("Step 1: Fetching all enrichment records...")
    all_enrichment_hashes = set()
    page = 0
    page_size = 1000
    
    while True:
        response = supabase.table("property_owner_enrichment_state") \
            .select("address_hash") \
            .range(page * page_size, (page + 1) * page_size - 1) \
            .execute()
        
        if not response.data:
            break
        
        for record in response.data:
            if record.get('address_hash'):
                all_enrichment_hashes.add(record['address_hash'])
        
        if len(response.data) < page_size:
            break
        
        page += 1
    
    logger.info(f"Found {len(all_enrichment_hashes)} unique address_hashes in enrichment table")
    logger.info("")
    
    # Step 2: Get all address_hashes from all listing tables
    logger.info("Step 2: Checking all listing tables for existing address_hashes...")
    all_listing_hashes = set()
    
    for table_name in LISTING_TABLES:
        try:
            table_hashes = set()
            page = 0
            
            while True:
                response = supabase.table(table_name) \
                    .select("address_hash") \
                    .not_.is_("address_hash", "null") \
                    .range(page * page_size, (page + 1) * page_size - 1) \
                    .execute()
                
                if not response.data:
                    break
                
                for record in response.data:
                    if record.get('address_hash'):
                        table_hashes.add(record['address_hash'])
                
                if len(response.data) < page_size:
                    break
                
                page += 1
            
            all_listing_hashes.update(table_hashes)
            logger.info(f"  {table_name}: {len(table_hashes)} addresses")
        
        except Exception as e:
            logger.warning(f"  {table_name}: Error - {e}")
    
    logger.info(f"Total unique addresses in all listing tables: {len(all_listing_hashes)}")
    logger.info("")
    
    # Step 3: Find orphaned enrichment records
    logger.info("Step 3: Finding orphaned enrichment records...")
    orphaned_hashes = all_enrichment_hashes - all_listing_hashes
    
    logger.info(f"Found {len(orphaned_hashes)} orphaned enrichment records")
    logger.info("")
    
    if len(orphaned_hashes) == 0:
        logger.info("✅ No orphaned records found. Database is clean!")
        return
    
    # Step 4: Show sample of what would be deleted
    logger.info("Sample of orphaned address_hashes (first 10):")
    for i, hash_val in enumerate(list(orphaned_hashes)[:10]):
        logger.info(f"  {i+1}. {hash_val}")
    
    if len(orphaned_hashes) > 10:
        logger.info(f"  ... and {len(orphaned_hashes) - 10} more")
    logger.info("")
    
    # Step 5: Delete if not dry run
    if not dry_run:
        logger.info("Step 4: Deleting orphaned records...")
        deleted_count = 0
        
        # Delete in batches to avoid timeout
        orphaned_list = list(orphaned_hashes)
        batch_size = 100
        
        for i in range(0, len(orphaned_list), batch_size):
            batch = orphaned_list[i:i + batch_size]
            
            try:
                # Delete from enrichment_state
                response = supabase.table("property_owner_enrichment_state") \
                    .delete() \
                    .in_("address_hash", batch) \
                    .execute()
                
                deleted_count += len(batch)
                logger.info(f"  Deleted batch {i//batch_size + 1}: {len(batch)} records (total: {deleted_count}/{len(orphaned_hashes)})")
            
            except Exception as e:
                logger.error(f"  Error deleting batch {i//batch_size + 1}: {e}")
        
        logger.info("")
        logger.info(f"✅ Successfully deleted {deleted_count} orphaned enrichment records")
    else:
        logger.info("")
        logger.info("🔍 DRY RUN: No records were deleted")
        logger.info(f"   To actually delete, run with: cleanup_orphaned_enrichment(dry_run=False)")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("CLEANUP COMPLETE")
    logger.info("=" * 60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up orphaned enrichment records")
    parser.add_argument('--live', action='store_true', help='Actually delete records (default is dry run)')
    args = parser.parse_args()
    
    cleanup_orphaned_enrichment(dry_run=not args.live)

