import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
# Try loading from current directory first, then project root
env_path = Path('.env')
if not env_path.exists():
    env_path = Path(__file__).resolve().parent / '.env'

print(f"Loading .env from: {env_path.absolute()}")
print(f"File exists: {env_path.exists()}")

# Print file content (first few chars) to check for BOM or weirdness
try:
    with open(env_path, 'rb') as f:
        content = f.read(50)
        print(f"File start (bytes): {content}")
except Exception as e:
    print(f"Error reading file: {e}")

# Force override
loaded = load_dotenv(dotenv_path=env_path, override=True)
print(f"load_dotenv returned: {loaded}")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

print(f"SUPABASE_URL: '{url}'")
# Mask key for security
masked_key = f"{key[:10]}...{key[-5:]}" if key else "None"
print(f"SUPABASE_SERVICE_KEY: '{masked_key}'")

if not url or not key:
    print("Error: Missing Supabase credentials")
    # Print all env keys to see what we have
    # print(f"Env keys: {list(os.environ.keys())}")
    exit(1)

try:
    print("Connecting to Supabase...")
    supabase: Client = create_client(url, key)
    
    # Try a simple query to verify connection
    print("Connection object created. Attempting to fetch data...")
    
    # Attempt to fetch one row to verify permissions/connection
    response = supabase.table("trulia_frbo_listings").select("*").limit(1).execute()
    
    print("Connection successful!")
    print(f"Data fetched: {response.data}")
    
except Exception as e:
    print(f"Connection failed: {e}")
