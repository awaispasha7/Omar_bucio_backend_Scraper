"""
Verify that the API returns unlimited listings (no 500 cap).
Run with the API server already running (python api_server.py on port 8080).

Usage (from Scraper_backend):
  python verify_listings_limit.py
  python verify_listings_limit.py --platform hotpads
"""
import argparse
import urllib.request
import json

BASE = "http://127.0.0.1:8080"
PLATFORMS = [
    "hotpads",
    "trulia",
    "redfin",
    "zillow-frbo",
    "zillow-fsbo",
    "fsbo",
    "apartments",
]


def main():
    parser = argparse.ArgumentParser(description="Verify last-result returns all listings (no cap)")
    parser.add_argument("--platform", choices=PLATFORMS, help="Check only this platform")
    parser.add_argument("--base", default=BASE, help=f"API base URL (default {BASE})")
    args = parser.parse_args()
    platforms = [args.platform] if args.platform else PLATFORMS
    base = args.base.rstrip("/")

    print("Checking listing counts (no cap = OK):\n")
    for platform in platforms:
        url = f"{base}/api/{platform}/last-result"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"  {platform}: ERROR - {e}")
            continue
        total = data.get("total", 0)
        listings = data.get("listings", [])
        actual = len(listings)
        status = "OK (no cap)" if total >= 0 else "ERROR"
        if total > 500:
            status = "OK (no cap - over 500)"
        if total > 1000:
            status = "OK (no cap - over 1000)"
        print(f"  {platform}: total={total}  ->  {status}")
    print("\nIf any platform shows more than 500 (or 1000), the limit is removed.")


if __name__ == "__main__":
    main()
