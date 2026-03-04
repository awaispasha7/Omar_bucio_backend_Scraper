"""
Flask API server for scraper backend.
- search-location: build platform URLs (with state abbreviation).
- trigger-from-url: run the appropriate Scrapy scraper in background (if utils available).
- last-result: return listings from Supabase (if configured).
- geocode: proxy to Nominatim (OpenStreetMap) for map lat/lon.
"""
import os
import sys
import subprocess
import threading
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from flask import Flask, request, jsonify

# Backend root (Scraper_backend) so we can import utils and run scrapers from scraper dirs
BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
# Load .env so SUPABASE_* and ZYTE_* are available for scrapers and last-result
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_ROOT / ".env")
except ImportError:
    pass

app = Flask(__name__)

# Per-platform scraper state: platform -> {"running": bool, "process": Popen or None}
_scraper_state = {}
_state_lock = threading.Lock()

def _get_supabase():
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None

def _path_to_platform(path):
    """Map last-result or status path to platform key (TableRouter uses these)."""
    if "zillow-fsbo" in path:
        return "zillow_fsbo"
    if "zillow-frbo" in path:
        return "zillow_frbo"
    if "apartments" in path:
        return "apartments.com"
    if "hotpads" in path:
        return "hotpads"
    if "trulia" in path:
        return "trulia"
    if "redfin" in path:
        return "redfin"
    if "fsbo" in path:
        return "fsbo"
    return None

def _row_to_listing(platform, row):
    """Map DB row to frontend listing shape."""
    # Common column names across tables (snake_case in DB)
    addr = row.get("address") or row.get("Address") or ""
    bedrooms = row.get("bedrooms") or row.get("Bedrooms")
    bathrooms = row.get("bathrooms") or row.get("Bathrooms")
    price = row.get("price") or row.get("Price") or ""
    listing_url = row.get("detail_url") or row.get("listing_link") or row.get("listing_url") or ""
    owner_phone = row.get("phone_number") or row.get("owner_phone") or row.get("Phone_Number") or ""
    owner_name = row.get("owner_name") or row.get("Name") or ""
    owner_email = row.get("owner_email") or ""
    if bedrooms is not None and not isinstance(bedrooms, int):
        try:
            bedrooms = int(bedrooms) if bedrooms != "" else None
        except (TypeError, ValueError):
            bedrooms = None
    if bathrooms is not None and not isinstance(bathrooms, int):
        try:
            bathrooms = int(bathrooms) if bathrooms != "" else None
        except (TypeError, ValueError):
            bathrooms = None
    return {
        "address": addr,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "price": str(price) if price else "",
        "listing_url": listing_url,
        "owner_phone": owner_phone or "",
        "owner_name": owner_name or "",
        "owner_email": owner_email or "",
        "source_platform": platform.replace(".com", "") if platform else "",
    }

@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin") or "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Backend running"})

@app.route("/api/geocode", methods=["GET", "OPTIONS"])
def geocode():
    if request.method == "OPTIONS":
        return "", 204
    q = request.args.get("q") or ""
    if not q or not q.strip():
        return jsonify([]), 200
    # Use Nominatim (OpenStreetMap) - no API key; policy requires User-Agent
    url = "https://nominatim.openstreetmap.org/search?q=" + quote(q.strip()) + "&format=json&limit=1"
    req = Request(url, headers={"User-Agent": "BrivanoScout/1.0 (scraper backend)"})
    try:
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        if not data:
            return jsonify([]), 200
        # Frontend expects array of { lat, lon }
        out = [{"lat": data[0].get("lat", ""), "lon": data[0].get("lon", "")}]
        return jsonify(out), 200
    except Exception:
        return jsonify([]), 200

def _parse_location(location):
    loc = (location or "").strip()
    parts = [p.strip() for p in loc.split(",", 1)]
    city_raw = parts[0] or ""
    state_raw = (parts[1] if len(parts) > 1 else "").strip()
    city_slug = city_raw.replace(" ", "-").lower()[:40]
    state_map = {"illinois": "il", "new york": "ny", "california": "ca", "texas": "tx", "florida": "fl", "ohio": "oh", "georgia": "ga", "north carolina": "nc", "michigan": "mi", "pennsylvania": "pa", "new jersey": "nj", "washington": "wa", "massachusetts": "ma", "virginia": "va", "minnesota": "mn", "colorado": "co", "wisconsin": "wi", "arizona": "az", "indiana": "in", "tennessee": "tn", "missouri": "mo", "maryland": "md", "district of columbia": "dc"}
    if len(state_raw) == 2:
        state_abbrev = state_raw.lower()
    else:
        state_abbrev = state_map.get(state_raw.lower(), (state_raw[:2].lower() if state_raw else ""))
    if not state_abbrev and city_raw:
        city_to_state = {"chicago": "il", "minneapolis": "mn", "houston": "tx", "dallas": "tx", "austin": "tx", "phoenix": "az", "seattle": "wa", "denver": "co", "boston": "ma", "miami": "fl", "atlanta": "ga", "detroit": "mi", "portland": "or", "san francisco": "ca", "los angeles": "ca", "san diego": "ca", "philadelphia": "pa", "new york": "ny"}
        state_abbrev = city_to_state.get(city_raw.lower(), "")
    city_state_slug = f"{city_slug}-{state_abbrev}" if state_abbrev else city_slug
    return city_slug, state_abbrev, city_state_slug, city_raw

@app.route("/api/search-location", methods=["POST", "GET", "OPTIONS"])
def search_location():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = {}
    platform = (data.get("platform") or request.args.get("platform") or "").strip().lower()
    location = (data.get("location") or request.args.get("location") or "").strip()
    if not platform or not location:
        return jsonify({"success": False, "error": "platform and location required"}), 400
    city_slug, state_abbrev, city_state_slug, _ = _parse_location(location)
    if not city_slug:
        return jsonify({"success": False, "error": "Invalid location"}), 400
    url = None
    if "zillow" in platform:
        if "frbo" in platform or "rent" in platform:
            url = f"https://www.zillow.com/{city_state_slug}/rentals/"
        else:
            url = f"https://www.zillow.com/{city_state_slug}/fsbo/"
    elif "apartments" in platform:
        url = f"https://www.apartments.com/{city_state_slug}/for-rent-by-owner/"
    elif "trulia" in platform:
        loc_str = f"{city_slug},{state_abbrev.upper()}" if state_abbrev else location.replace(" ", ",")
        url = f"https://www.trulia.com/for_sale/{quote(loc_str)}/fsbo_lt/1_als/"
    elif "redfin" in platform:
        city_path = (location.split(",")[0] or "").strip().replace(" ", "-")
        st = state_abbrev.upper() if state_abbrev else "IL"
        url = f"https://www.redfin.com/{st}/{city_path}/filter/include=fsbo"
    elif "fsbo" in platform:
        url = f"https://www.forsalebyowner.com/search/list/{city_slug}"
    if url:
        return jsonify({"success": True, "url": url, "platform": platform, "location": location})
    return jsonify({"success": False, "error": "Unsupported platform"}), 400

def _run_scraper_and_set_idle(platform, process, scraper_dir, cmd_args):
    """Background: wait for process then set status to idle."""
    try:
        process.wait()
    except Exception:
        pass
    with _state_lock:
        if _scraper_state.get(platform, {}).get("process") is process:
            _scraper_state[platform] = {"running": False, "process": None}

@app.route("/api/trigger-from-url", methods=["GET", "POST", "OPTIONS"])
def trigger_from_url():
    if request.method == "OPTIONS":
        return "", 204
    url = (request.get_json(silent=True) or {}).get("url") or request.args.get("url") or ""
    if not url:
        return jsonify({"error": "url required"}), 400
    try:
        from utils.url_detector import URLDetector
        from utils.table_router import TableRouter
    except ImportError:
        return jsonify({"message": "Scraper started (utils not available - run from Scraper_backend root)"})
    platform, table_name, scraper_config, _ = TableRouter.route_url(url)
    if not platform or not scraper_config:
        return jsonify({"message": "Scraper started (unknown platform for URL)"})
    with _state_lock:
        if _scraper_state.get(platform, {}).get("running"):
            return jsonify({"error": "Scraper already running for this platform"}), 400
    scraper_dir = BACKEND_ROOT / scraper_config["scraper_dir"]
    if not scraper_dir.is_dir():
        return jsonify({"error": f"Scraper dir not found: {scraper_dir}"}), 500
    url_param = scraper_config.get("url_param") or "url"
    cmd_list = scraper_config.get("command") or ["-m", "scrapy", "crawl", scraper_config["scraper_name"], "-a"]
    if platform == "fsbo":
        # FSBO uses argparse: python script.py --url <url>
        cmd = ["python", "forsalebyowner_selenium_scraper.py", "--url", url]
    elif isinstance(cmd_list, list):
        cmd = ["python"] + cmd_list + [f"{url_param}={url}"]
    else:
        cmd = [cmd_list, f"{url_param}={url}"]
    env = os.environ.copy()
    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(scraper_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    with _state_lock:
        _scraper_state[platform] = {"running": True, "process": process}
    threading.Thread(target=_run_scraper_and_set_idle, args=(platform, process, scraper_dir, cmd), daemon=True).start()
    return jsonify({"message": "Scraper started", "platform": platform})

def _status_view():
    platform = _path_to_platform(request.path)
    with _state_lock:
        running = _scraper_state.get(platform, {}).get("running", False) if platform else False
    if request.args.get("reset") and platform:
        with _state_lock:
            _scraper_state[platform] = {"running": False, "process": None}
    return jsonify({"status": "running" if running else "idle", "last_run": None, "error": None})

def _last_result_view():
    platform = _path_to_platform(request.path)
    if not platform:
        return jsonify({"listings": [], "total": 0})
    try:
        from utils.table_router import TableRouter
    except ImportError:
        return jsonify({"listings": [], "total": 0, "message": "utils not available"})
    table_name = TableRouter.get_table_for_platform(platform)
    if not table_name:
        return jsonify({"listings": [], "total": 0})
    supabase = _get_supabase()
    if not supabase:
        return jsonify({"listings": [], "total": 0, "message": "Supabase not configured"})
    try:
        # Order by created_at desc if column exists; limit 500
        r = supabase.table(table_name).select("*").order("created_at", desc=True).limit(500).execute()
        rows = (r.data or []) if hasattr(r, "data") else []
    except Exception as e:
        try:
            r = supabase.table(table_name).select("*").limit(500).execute()
            rows = (r.data or []) if hasattr(r, "data") else []
        except Exception:
            return jsonify({"listings": [], "total": 0, "error": str(e)})
    listings = [_row_to_listing(platform, row) for row in rows]
    return jsonify({"listings": listings, "total": len(listings)})

for path in ["/api/status-hotpads", "/api/status-trulia", "/api/status-redfin",
             "/api/status-zillow-frbo", "/api/status-zillow-fsbo", "/api/status-fsbo", "/api/status-apartments"]:
    app.add_url_rule(path, path.replace("/", "_").strip("_"), _status_view, methods=["GET"])

for path in ["/api/hotpads/last-result", "/api/trulia/last-result", "/api/redfin/last-result",
             "/api/zillow-frbo/last-result", "/api/zillow-fsbo/last-result", "/api/fsbo/last-result", "/api/apartments/last-result"]:
    app.add_url_rule(path, path.replace("/", "_").strip("_").replace(".", "_"), _last_result_view, methods=["GET"])

if __name__ == "__main__":
    print("Starting Flask API server on http://127.0.0.1:8080 ...")
    print("(Minimal stub - restore full api_server.py from backup/repo for real scraping.)")
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
