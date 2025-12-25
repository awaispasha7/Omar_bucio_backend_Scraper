import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Load env
project_root = Path(__file__).resolve().parents[0]
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

def setup_tables():
    url = os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_URL_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        print("Error: Supabase credentials missing.")
        return

    supabase: Client = create_client(url, key)
    
    sql_path = project_root / 'setup_enrichment_tables.sql'
    with open(sql_path, 'r') as f:
        sql = f.read()
    
    # Supabase Python SDK doesn't have a direct .rpc() for raw query strings
    # We usually run this via the SQL Editor, but I'll provide a instructions
    print("\n--- ACTION REQUIRED ---")
    print(f"Please run the SQL content from {sql_path} in your Supabase SQL Editor.")
    print("------------------------\n")

if __name__ == "__main__":
    setup_tables()
