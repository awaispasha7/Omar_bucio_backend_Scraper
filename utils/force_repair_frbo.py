
import os
import sys
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

# Add current dir to path to import utils
sys.path.append(os.getcwd())
from utils.address_utils import normalize_address, generate_address_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def force_repair_frbo():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    supabase: Client = create_client(url, key)
    
    table_name = 'zillow_frbo_listings'
    logger.info(f"🚀 Force repairing {table_name}")
    
    res = supabase.table(table_name).select('id, address').execute()
    listings = res.data
    
    logger.info(f"Found {len(listings)} listings to check")
    
    repaired = 0
    for l in listings:
        addr = l['address']
        if not addr: continue
        
        correct_hash = generate_address_hash(normalize_address(addr))
        # Always update just to be safe in this test
        supabase.table(table_name).update({'address_hash': correct_hash}).eq('id', l['id']).execute()
        repaired += 1
        if repaired % 100 == 0:
            logger.info(f"  Processed {repaired}...")
            
    logger.info(f"✅ Finished. Repaired {repaired} listings.")

if __name__ == "__main__":
    force_repair_frbo()
