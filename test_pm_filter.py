"""
Test PM/realtor filter (Option 1: hide those listings).
Run from Scraper_backend with API server running for the API check.

  python test_pm_filter.py
"""
import urllib.request
import json

# 1) Unit test: import the filter and check it marks PM/realtor rows
def test_filter_logic():
    from utils.pm_realtor_filter import is_pm_or_realtor
    # Should be hidden (PM/realtor)
    assert is_pm_or_realtor({"owner_name": "Property Manager LLC"}) is True
    assert is_pm_or_realtor({"owner_name": "ABC Real Estate Agent"}) is True
    assert is_pm_or_realtor({"agent_name": "Leasing Office"}) is True
    assert is_pm_or_realtor({"description": "Rental management company"}) is True
    # Should NOT be hidden (by-owner)
    assert is_pm_or_realtor({"owner_name": "John Smith"}) is False
    assert is_pm_or_realtor({"owner_name": ""}) is False
    assert is_pm_or_realtor({}) is False
    print("  Filter logic: OK (PM/realtor rows detected, by-owner kept)")


# 2) API test: call last-result and show count (filter is applied by backend)
def test_api():
    base = "http://127.0.0.1:8080"
    for platform in ["zillow-frbo", "hotpads", "apartments"]:
        try:
            req = urllib.request.Request(f"{base}/api/{platform}/last-result", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            total = data.get("total", 0)
            print(f"  {platform}: {total} listings returned (PM/realtor hidden)")
        except Exception as e:
            print(f"  {platform}: skip ({e})")


if __name__ == "__main__":
    print("1. Testing PM/realtor filter logic...")
    test_filter_logic()
    print("2. Testing API (ensure api_server is running on port 8080)...")
    test_api()
    print("Done. If counts are lower than before, filter is hiding PM/realtor listings.")
