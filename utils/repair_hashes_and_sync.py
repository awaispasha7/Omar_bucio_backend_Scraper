
import os
import sys
import logging
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# Add current dir to path to import utils
sys.path.append(os.getcwd())

from utils.address_utils import normalize_address, generate_address_hash

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

def repair_hashes():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        logger.error("❌ Missing Supabase credentials")
        return

    supabase: Client = create_client(url, key)
    
    tables = [
        'zillow_frbo_listings'
    ]
    
    logger.info("🚀 Starting Targeted Hash Repair (FRBO Only)")
    
    total_repaired = 0
    
    for table_name in tables:
        try:
            logger.info(f"📋 Processing table: {table_name}")
            
            # Fetch all listings
            limit = 500
            offset = 0
            table_repaired = 0
            
            while True:
                res = supabase.table(table_name).select('id, address, address_hash').range(offset, offset + limit - 1).execute()
                listings = res.data
                
                if not listings:
                    break
                
                print(f"Checking chunk of {len(listings)} listings...")
                
                for listing in listings:
                    listing_id = listing.get('id')
                    raw_address = listing.get('address')
                    current_hash = listing.get('address_hash')
                    
                    if not raw_address:
                        continue
                    
                    normalized = normalize_address(raw_address)
                    correct_hash = generate_address_hash(normalized)
                    
                    # Explicit detailed check for the first few
                    if table_repaired < 5:
                        print(f"ID {listing_id}: {raw_address[:30]}")
                        print(f"  Curr: {current_hash}")
                        print(f"  Corr: {correct_hash}")
                        print(f"  Match? {current_hash == correct_hash}")

                    if not current_hash or current_hash != correct_hash:
                        supabase.table(table_name).update({'address_hash': correct_hash}).eq('id', listing_id).execute()
                        table_repaired += 1
                        if table_repaired % 50 == 0:
                            print(f"  Repaired {table_repaired}...")
                
                if len(listings) < limit:
                    break
                offset += limit
                
            logger.info(f"  ✅ Repaired {table_repaired} hashes in {table_name}")
            total_repaired += table_repaired
            
        except Exception as e:
            logger.error(f"  ❌ Error processing {table_name}: {e}")
            
    logger.info(f"\n✨ COMPLETED: Repaired total of {total_repaired} hashes across all tables.")

if __name__ == "__main__":
    repair_hashes()
