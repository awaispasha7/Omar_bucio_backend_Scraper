"""
Script to check and optionally reset the ID sequence in Supabase
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
project_root = Path(__file__).resolve().parent
env_paths = [
    project_root / '.env',
    project_root / 'redfin_FSBO_backend' / '.env',
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break
else:
    load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '') or os.getenv('SUPABASE_ANON_KEY', '') or os.getenv('SUPABASE_KEY', '')

def check_table_info():
    """Check current table information"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Get all records to see the ID range
        result = supabase.table('redfin_listings').select('id').order('id', desc=False).limit(1000).execute()
        
        if result.data:
            ids = [row['id'] for row in result.data]
            print(f"Current ID range: {min(ids)} to {max(ids)}")
            print(f"Total records: {len(ids)}")
            print(f"\nFirst few IDs: {ids[:10]}")
            print(f"Last few IDs: {ids[-10:]}")
        else:
            print("No records found in table")
            
    except Exception as e:
        print(f"Error: {e}")

def reset_sequence():
    """Reset the ID sequence to start from 1 (WARNING: Only do this if table is empty or you want to renumber)"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Get max ID
        result = supabase.table('redfin_listings').select('id').order('id', desc=True).limit(1).execute()
        
        if result.data:
            max_id = result.data[0]['id']
            print(f"Current max ID: {max_id}")
            print("\nWARNING: Resetting sequence will not renumber existing records.")
            print("This should only be done if the table is empty or you're okay with gaps.")
            
            # To reset sequence, you would need to run SQL:
            # ALTER SEQUENCE redfin_listings_id_seq RESTART WITH 1;
            # But this requires direct database access, not available through Supabase client
            print("\nTo reset the sequence, you need to run this SQL in Supabase SQL Editor:")
            print("ALTER SEQUENCE redfin_listings_id_seq RESTART WITH 1;")
        else:
            print("Table is empty")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("Supabase ID Sequence Checker")
    print("=" * 60)
    print("\n1. Checking current table information...")
    check_table_info()
    
    print("\n" + "=" * 60)
    print("\nNote: ID sequences don't reset automatically in PostgreSQL.")
    print("This is normal behavior and doesn't affect functionality.")
    print("=" * 60)

