"""
Minimal Flask API server so the backend RUNS on localhost:8080.
Your full api_server.py was empty - restore the complete version from backup or repo.
This stub keeps the server up and returns safe responses so the UI shows "Running".
"""
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin") or "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Backend running (minimal stub - restore full api_server.py for scraping)"})

@app.route("/api/search-location", methods=["POST", "GET", "OPTIONS"])
def search_location():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True) or {}
    platform = data.get("platform") or request.args.get("platform")
    location = data.get("location") or request.args.get("location") or ""
    if not platform or not location:
        return jsonify({"success": False, "error": "platform and location required"}), 400
    # Stub: return URL with state abbreviation for Zillow (e.g. chicago-il not chicago-illinois)
    if "zillow" in str(platform).lower():
        parts = [p.strip() for p in (location or "").split(",", 1)]
        city = (parts[0] or "").replace(" ", "-").lower()[:40]
        state = (parts[1] if len(parts) > 1 else "").strip()
        state_map = {"illinois": "il", "new york": "ny", "california": "ca", "texas": "tx", "florida": "fl", "ohio": "oh", "georgia": "ga", "north carolina": "nc", "michigan": "mi", "pennsylvania": "pa", "new jersey": "nj", "washington": "wa", "massachusetts": "ma", "virginia": "va", "minnesota": "mn", "colorado": "co", "wisconsin": "wi", "arizona": "az", "indiana": "in", "tennessee": "tn", "missouri": "mo", "maryland": "md", "district of columbia": "dc"}
        state_abbrev = state[:2].lower() if len(state) == 2 else state_map.get((state or "").lower(), (state[:2].lower() if state else ""))
        slug = f"{city}-{state_abbrev}" if state_abbrev else city
        return jsonify({"success": True, "url": f"https://www.zillow.com/{slug}/fsbo/", "platform": platform, "location": location})
    return jsonify({"success": False, "error": "Restore full api_server.py for this platform"}), 400

@app.route("/api/trigger-from-url", methods=["GET", "POST", "OPTIONS"])
def trigger_from_url():
    if request.method == "OPTIONS":
        return "", 204
    return jsonify({"message": "Scraper started (stub - restore full api_server.py for real scraping)"})

def _status():
    return jsonify({"status": "idle", "last_run": None, "error": None})

def _last_result():
    return jsonify({"listings": [], "total": 0, "message": "Restore full api_server.py for database results"})

for path in ["/api/status-hotpads", "/api/status-trulia", "/api/status-redfin",
             "/api/status-zillow-frbo", "/api/status-zillow-fsbo", "/api/status-fsbo", "/api/status-apartments"]:
    app.add_url_rule(path, path.replace("/", "_").strip("_"), _status, methods=["GET"])

for path in ["/api/hotpads/last-result", "/api/trulia/last-result", "/api/redfin/last-result",
             "/api/zillow-frbo/last-result", "/api/zillow-fsbo/last-result", "/api/fsbo/last-result", "/api/apartments/last-result"]:
    app.add_url_rule(path, path.replace("/", "_").strip("_").replace(".", "_"), _last_result, methods=["GET"])

if __name__ == "__main__":
    print("Starting Flask API server on http://127.0.0.1:8080 ...")
    print("(Minimal stub - restore full api_server.py from backup/repo for real scraping.)")
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
