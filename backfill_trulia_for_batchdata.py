"""
Backfill trulia_listings with address_hash and enqueue for BatchData enrichment.

Run this once if you have existing Trulia rows with NULL owner_name/phones/emails.
Then run the BatchData worker so it can fetch and fill owner name, email, phone, mailing address.

Prerequisites:
  - Run migration: birvanoio/supabase/migrations/20260217120000_trulia_listings_enrichment.sql
    (adds address_hash, enrichment_status to trulia_listings)
  - Scraper_backend/.env: SUPABASE_URL, SUPABASE_SERVICE_KEY

After backfill: run BatchData (see instructions printed at end).
"""
import os
import sys
from pathlib import Path

# Load .env from Scraper_backend
backend_root = Path(__file__).resolve().parent
env_path = backend_root / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path, override=True)

# Ensure we can import utils
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from supabase import create_client
from utils.address_utils import normalize_address, generate_address_hash


def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in Scraper_backend/.env")
        sys.exit(1)

    supabase = create_client(url, key)

    # 0) Check that address_hash column exists (migration must be run first)
    try:
        supabase.table("trulia_listings").select("id, address_hash").limit(1).execute()
    except Exception as e:
        err = str(e).lower()
        if "address_hash" in err and ("does not exist" in err or "42703" in str(e)):
            print("ERROR: trulia_listings table is missing address_hash column.")
            print("Run this SQL in Supabase Dashboard > SQL Editor, then run this script again:")
            print("")
            migration_path = backend_root.parent / "birvanoio" / "supabase" / "migrations" / "20260217120000_trulia_listings_enrichment.sql"
            if migration_path.exists():
                print(migration_path.read_text(encoding="utf-8"))
            else:
                print("ALTER TABLE public.trulia_listings ADD COLUMN IF NOT EXISTS address_hash TEXT, ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'never_checked';")
                print("CREATE INDEX IF NOT EXISTS idx_trulia_listings_address_hash ON public.trulia_listings (address_hash);")
            sys.exit(1)
        raise

    # 1) Fetch trulia_listings that have address (select without address_hash in case column doesn't exist yet)
    print("Fetching trulia_listings with address...")
    try:
        res = supabase.table("trulia_listings").select("id, listing_link, address").not_.is_("address", "null").execute()
    except Exception as e:
        if "address" in str(e).lower() and "does not exist" in str(e).lower():
            print("ERROR: trulia_listings table or address column not found.")
        raise
    rows = res.data or []
    if not rows:
        print("No trulia_listings rows with address and missing address_hash. Nothing to backfill.")
        return

    print(f"Found {len(rows)} rows to backfill.")

    # 2) Get existing enrichment_state address_hashes so we don't overwrite enriched
    state_res = supabase.table("property_owner_enrichment_state").select("address_hash, status").execute()
    existing = {r["address_hash"]: r.get("status") for r in (state_res.data or [])}
    TERMINAL = {"enriched", "no_owner_data", "failed"}

    updated = 0
    queued = 0
    for r in rows:
        address = (r.get("address") or "").strip()
        if not address:
            continue
        normalized = normalize_address(address)
        address_hash = generate_address_hash(normalized)
        if not address_hash:
            continue

        # Update trulia_listings
        try:
            supabase.table("trulia_listings").update({
                "address_hash": address_hash,
                "enrichment_status": "never_checked",
            }).eq("id", r["id"]).execute()
            updated += 1
        except Exception as e:
            print(f"  WARN: Update trulia_listings id={r['id']}: {e}")
            continue

        # Enqueue for BatchData only if not already in terminal state
        if existing.get(address_hash) in TERMINAL:
            continue
        try:
            supabase.table("property_owner_enrichment_state").upsert({
                "address_hash": address_hash,
                "normalized_address": normalized,
                "status": "never_checked",
                "locked": False,
                "source_used": None,
                "listing_source": "Trulia",
            }, on_conflict="address_hash").execute()
            queued += 1
        except Exception as e:
            print(f"  WARN: Enqueue {address_hash[:8]}: {e}")

    print(f"Done. Updated address_hash on {updated} trulia_listings. Queued {queued} for BatchData.")
    print("")
    print("Next: run BatchData to fetch owner name, email, phone, mailing address:")
    print("  From backend folder:  python batchdata_worker.py --source Trulia --limit 50")
    print("  Or API:               POST http://localhost:8080/api/trigger-enrichment?source=Trulia&limit=50")
    print("  (Requires BATCHDATA_API_KEY and BATCHDATA_ENABLED=true in .env)")


if __name__ == "__main__":
    main()
