"""
Simple Flask API server for Railway deployment
Provides endpoints to trigger scraper and check status
"""

import sys
import io

# Prevent Windows "charmap" codec errors: wrap stdout/stderr so writes never raise
class _SafeTextStream(io.TextIOBase):
    def __init__(self, stream):
        self._stream = stream
    def write(self, s):
        if not s:
            return 0
        try:
            return self._stream.write(s)
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                safe = s.encode("utf-8", errors="replace").decode("utf-8")
                return self._stream.write(safe)
            except Exception:
                return self._stream.write(s.encode("ascii", errors="replace").decode("ascii"))
    def flush(self):
        self._stream.flush()
    def __getattr__(self, name):
        return getattr(self._stream, name)

def _install_safe_stdout_stderr():
    if getattr(sys.stdout, "_safe_wrapped", False):
        return
    _old_stdout, _old_stderr = sys.stdout, sys.stderr
    try:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        else:
            sys.stdout = _SafeTextStream(sys.stdout)
            sys.stderr = _SafeTextStream(sys.stderr)
    except Exception:
        try:
            sys.stdout = _SafeTextStream(sys.stdout)
            sys.stderr = _SafeTextStream(sys.stderr)
        except Exception:
            pass
    try:
        sys.stdout._safe_wrapped = True
    except Exception:
        pass
    # Point any logging handlers still using old streams to the new safe streams
    try:
        import logging
        for _root in (logging.root,):
            for _h in getattr(_root, "handlers", []):
                if getattr(_h, "stream", None) is _old_stdout:
                    _h.stream = sys.stdout
                elif getattr(_h, "stream", None) is _old_stderr:
                    _h.stream = sys.stderr
    except Exception:
        pass

_install_safe_stdout_stderr()

from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import os
import json
import threading
import time
import queue
import schedule
from datetime import datetime

# Import URL detection and routing utilities
from utils.url_detector import URLDetector
from utils.table_router import TableRouter

app = Flask(__name__)

# CORS: Trulia & Hotpads scraper + dashboard routes — allow production, Lovable preview, and local dev
_FRONTEND_ORIGINS = [
    "https://www.brivano.io",
    "https://brivano.io",
    "http://localhost:5173",
    "https://lovable.dev",
    "https://www.lovable.dev",
]


def _is_allowed_origin(origin):
    if not origin:
        return False
    if origin in _FRONTEND_ORIGINS:
        return True
    # Lovable preview subdomains (e.g. https://xxx.lovableproject.com)
    if origin.endswith(".lovableproject.com") and origin.startswith("https://"):
        return True
    return False
_CORS_OPTS = {
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
}
# Trulia/Hotpads and scraper-dashboard routes: restrict origin to frontend deployments
CORS(app, resources={
    r"/api/geocode": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/skip-trace": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/search-location": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/trigger-from-url": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/trigger-hotpads": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/status-hotpads": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/hotpads/reset": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/hotpads/last-result": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/trigger-trulia": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/status-trulia": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/trulia/last-result": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/trigger-redfin": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/status-redfin": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    r"/api/redfin/last-result": {**{"origins": _FRONTEND_ORIGINS}, **_CORS_OPTS},
    # All other /api/* routes (other scrapers): unchanged, allow all origins
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})


@app.after_request
def _cors_allow_lovable_after_request(response):
    """Allow CORS for Lovable preview subdomains (*.lovableproject.com) and other allowed origins.
    Also set Allow-Headers and Allow-Methods so preflight (OPTIONS) succeeds when origin is allowed."""
    if not request.path.startswith("/api/"):
        return response
    origin = request.headers.get("Origin")
    if origin and _is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.before_request
def _log_request():
    """Log every request so you can see in the terminal that the backend received it."""
    if request.path.startswith("/api/"):
        print(f"[BACKEND] {request.method} {request.path}", flush=True)


# Global status dictionaries
scraper_status = {"running": False, "last_run": None, "last_result": None, "error": None}
apartments_scraper_status = {"running": False, "last_run": None, "last_result": None, "error": None}
zillow_fsbo_status = {"running": False, "last_run": None, "last_result": None, "error": None}
zillow_frbo_status = {"running": False, "last_run": None, "last_result": None, "error": None}
hotpads_status = {"running": False, "last_run": None, "last_result": None, "error": None}
redfin_status = {"running": False, "last_run": None, "last_result": None, "error": None}
trulia_status = {"running": False, "last_run": None, "last_result": None, "error": None}
all_scrapers_status = {"running": False, "last_run": None, "finished_at": None, "last_result": None, "error": None, "current_scraper": None, "completed": []}
enrichment_status = {"running": False, "last_run": None, "last_result": None, "error": None}

# Global process tracker for stopping
active_processes = {}
user_stopped_processes = set()  # Track processes stopped by user (to avoid logging as errors)
stop_all_requested = False

# Global Log Buffer
# List of dicts: { "timestamp": iso_str, "message": str, "type": "info"|"error"|"success" }
LOG_BUFFER = []
MAX_LOG_SIZE = 1000

def _safe_console(s):
    """Make string safe for Windows console (avoids charmap/codec errors)."""
    if s is None:
        return "None"
    try:
        return str(s).encode("ascii", "replace").decode("ascii")
    except Exception:
        return repr(s)[:200]


def _hotpads_url_inline(location, property_type="apartments"):
    """Build Hotpads URL in-process. No external modules, no logging - avoids encoding issues."""
    import re
    loc = (location or "").strip()
    if not loc:
        return None
    city_to_state = {
        "minneapolis": "mn", "new york": "ny", "los angeles": "ca", "chicago": "il",
        "houston": "tx", "phoenix": "az", "philadelphia": "pa", "san antonio": "tx",
        "san diego": "ca", "dallas": "tx", "austin": "tx", "seattle": "wa", "denver": "co",
        "boston": "ma", "miami": "fl", "atlanta": "ga", "detroit": "mi", "portland": "or",
        "washington": "dc", "san francisco": "ca", "san fracisco": "ca", "los angles": "ca",
    }
    slug_overrides = {
        "san fracisco": "san-francisco", "los angles": "los-angeles",
    }
    state_abbrev = None
    city = None
    low = loc.lower()
    if low in city_to_state:
        state_abbrev = city_to_state[low]
        city = loc
    match = re.match(r"^(.+?),\s*([A-Za-z]{2})\s*$", loc)
    if match:
        city = match.group(1).strip()
        state_abbrev = match.group(2).strip().lower()
    if not state_abbrev:
        space_match = re.match(r"^(.+?)\s+([A-Za-z]{2})\s*$", loc)
        if space_match:
            city = space_match.group(1).strip()
            state_abbrev = space_match.group(2).strip().lower()
    if not state_abbrev or not city:
        return None
    slug = re.sub(r"[^\w\s-]", "", city.lower())
    slug = re.sub(r"\s+", "-", slug).strip("-")
    slug = slug_overrides.get(low) or slug_overrides.get(city.lower()) or slug
    if not slug:
        return None
    pt = (property_type or "apartments").lower().strip()
    if pt in ("for-rent", "rent", "rentals", ""):
        pt = "apartments"
    if not pt.endswith("s") and pt in ("apartment", "house", "condo", "townhome"):
        pt = pt + "s"
    return f"https://hotpads.com/{slug}-{state_abbrev}/{pt}-for-rent"


def _trulia_url_inline(location):
    """Build Trulia FSBO URL in-process. Same supported cities as Hotpads. Do not touch Hotpads."""
    import re
    from urllib.parse import quote
    loc = (location or "").strip()
    if not loc:
        return None
    city_to_state = {
        "minneapolis": "mn", "new york": "ny", "los angeles": "ca", "chicago": "il",
        "washington": "dc", "san francisco": "ca", "san fracisco": "ca", "los angles": "ca",
        "houston": "tx", "phoenix": "az", "philadelphia": "pa", "san antonio": "tx",
        "san diego": "ca", "dallas": "tx", "austin": "tx", "seattle": "wa", "denver": "co",
        "boston": "ma", "miami": "fl", "atlanta": "ga", "detroit": "mi", "portland": "or",
    }
    state_abbrev = None
    city = None
    low = loc.lower()
    if low in city_to_state:
        state_abbrev = city_to_state[low]
        city = loc.strip()
    match = re.match(r"^(.+?),\s*([A-Za-z]{2})\s*$", loc)
    if match:
        city = match.group(1).strip()
        state_abbrev = match.group(2).strip().lower()
    if not state_abbrev:
        space_match = re.match(r"^(.+?)\s+([A-Za-z]{2})\s*$", loc)
        if space_match:
            city = space_match.group(1).strip()
            state_abbrev = space_match.group(2).strip().lower()
    if not state_abbrev or not city:
        return None
    # Trulia expects "City,ST" with no space after comma (e.g. Minneapolis,MN); space causes INVALID_LOCATION
    location_str = f"{city},{state_abbrev.upper()}"
    encoded = quote(location_str, safe=",")  # encode spaces in city name, keep comma
    return f"https://www.trulia.com/for_sale/{encoded}/fsbo_lt/1_als/"


def add_log(message, type="info"):
    """Add a log entry to the buffer"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "type": type
    }
    LOG_BUFFER.append(entry)
    # Print to server console as well (flush so logs show immediately in terminal)
    try:
        print(f"[{entry['timestamp']}] [{type.upper()}] {message}", flush=True)
    except (UnicodeEncodeError, UnicodeDecodeError):
        clean_message = _safe_console(message)
        print(f"[{entry['timestamp']}] [{type.upper()}] {clean_message}", flush=True)
    
    # Keep buffer size manageable
    if len(LOG_BUFFER) > MAX_LOG_SIZE:
        LOG_BUFFER.pop(0)

def stream_output(process, scraper_name):
    """Read output from process and add to logs"""
    for line in iter(process.stdout.readline, ''):
        if line:
            add_log(f"[{scraper_name}] {line.strip()}", "info")
        # Check if process was stopped
        if scraper_name in user_stopped_processes:
            break
    try:
        process.stdout.close()
    except:
        pass

def run_process_with_logging(cmd, cwd, scraper_name, status_dict, env=None):
    """Run a subprocess and stream its output to logs"""
    try:
        add_log(f"Starting {scraper_name}...", "info")
        status_dict["running"] = True
        status_dict["error"] = None
        status_dict["last_run"] = datetime.now().isoformat()
        
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout for simple logging
            text=True,
            bufsize=1, # Line buffered
            universal_newlines=True,
            env=env
        )
        
        # Register process for stopping
        active_processes[scraper_name] = process
        
        # Read output in real-time (non-blocking thread)
        output_thread = threading.Thread(target=stream_output, args=(process, scraper_name), daemon=True)
        output_thread.start()
        
        # Wait for completion with periodic checks for stop requests
        returncode = None
        while returncode is None:
            returncode = process.poll()
            if returncode is None:
                # Process still running - check if user requested stop
                if scraper_name in user_stopped_processes or (stop_all_requested and scraper_name == all_scrapers_status.get("current_scraper")):
                    ensure_process_killed(scraper_name)
                    # Wait briefly for process to terminate
                    for _ in range(10):  # Check 10 times with 0.2s delay = 2s max wait
                        returncode = process.poll()
                        if returncode is not None:
                            break
                        time.sleep(0.2)
                    # Force kill if still running
                    if returncode is None and process.poll() is None:
                        try:
                            process.kill()
                            time.sleep(0.2)
                            returncode = process.poll()
                        except:
                            pass
                    break
                time.sleep(0.5)  # Check every 0.5 seconds instead of blocking
        
        # Ensure output thread has time to finish reading
        output_thread.join(timeout=1.0)
        
        # Unregister
        if scraper_name in active_processes:
            del active_processes[scraper_name]
            
        success = returncode == 0
        status_dict["running"] = False
        
        # Check if this was a user-initiated stop (negative return codes indicate termination signals)
        was_user_stopped = scraper_name in user_stopped_processes or returncode < 0
        
        if success:
            result_info = {
                "success": True,
                "returncode": returncode,
                "timestamp": datetime.now().isoformat()
            }
            add_log(f"{scraper_name} completed successfully.", "success")
        elif was_user_stopped:
            # User-initiated stop (negative return code = termination signal like SIGTERM -15, SIGKILL -9)
            msg = f"{scraper_name} stopped by user."
            result_info = {
                "success": True,  # Treat as successful operation (user action, not error)
                "returncode": returncode,
                "stopped_by_user": True,
                "timestamp": datetime.now().isoformat()
            }
            add_log(msg, "info")
            # Remove from tracking set
            user_stopped_processes.discard(scraper_name)
        else:
            # Actual error - non-zero return code that wasn't user-initiated
            msg = f"{scraper_name} failed with return code {returncode}."
            result_info = {
                "success": False,
                "returncode": returncode,
                "error": msg,
                "timestamp": datetime.now().isoformat()
            }
            add_log(msg, "error")
            status_dict["error"] = msg
        
        status_dict["last_result"] = result_info
            
        return success
        
    except Exception as e:
        status_dict["running"] = False
        ensure_process_killed(scraper_name)
        err_msg = f"Error running {scraper_name}: {str(e)}"
        add_log(err_msg, "error")
        status_dict["error"] = err_msg
        status_dict["last_result"] = {"success": False, "error": str(e)}
        return False

def ensure_process_killed(scraper_name):
    """Kill process if it exists in active_processes"""
    process = active_processes.get(scraper_name)
    if process:
        # Mark as user-stopped so we don't log the termination as an error
        user_stopped_processes.add(scraper_name)
        try:
            process.terminate()
            # Wait shorter time (0.3s) before force kill
            time.sleep(0.3)
            if process.poll() is None:
                # Process didn't terminate, force kill
                process.kill()
                time.sleep(0.2)
        except Exception as e:
            add_log(f"Error terminating {scraper_name}: {str(e)}", "error")
        
        # Safely remove from tracker
        active_processes.pop(scraper_name, None)

def run_sequential_scrapers():
    """Run all scrapers sequentially"""
    global stop_all_requested, all_scrapers_status
    
    if all_scrapers_status["running"]:
        add_log("⚠️ Sequential run triggered but already running. Skipping.", "warning")
        return

    stop_all_requested = False
    all_scrapers_status["running"] = True
    all_scrapers_status["error"] = None
    all_scrapers_status["last_run"] = datetime.now().isoformat()
    add_log("🚀 Starting ALL scrapers sequentially...", "info")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    scrapers = [
        ("FSBO", [sys.executable, "forsalebyowner_selenium_scraper.py"], os.path.join(base_dir, "FSBO_Scraper"), scraper_status),
        ("Apartments", [sys.executable, "-m", "scrapy", "crawl", "apartments_frbo"], os.path.join(base_dir, "Apartments_Scraper"), apartments_scraper_status),
        ("Zillow_FSBO", [sys.executable, "-m", "scrapy", "crawl", "zillow_spider"], os.path.join(base_dir, "Zillow_FSBO_Scraper"), zillow_fsbo_status),
        ("Zillow_FRBO", [sys.executable, "-m", "scrapy", "crawl", "zillow_spider"], os.path.join(base_dir, "Zillow_FRBO_Scraper"), zillow_frbo_status),
        ("Hotpads", [sys.executable, "-m", "scrapy", "crawl", "hotpads_scraper"], os.path.join(base_dir, "Hotpads_Scraper"), hotpads_status),
        ("Redfin", [sys.executable, "-m", "scrapy", "crawl", "redfin_spider"], os.path.join(base_dir, "Redfin_Scraper"), redfin_status),
        ("Trulia", [sys.executable, "-m", "scrapy", "crawl", "trulia_spider"], os.path.join(base_dir, "Trulia_Scraper"), trulia_status),
    ]
    
    for name, cmd, cwd, status_dict in scrapers:
        if stop_all_requested:
            add_log("🛑 Stop All requested. Cancelling remaining scrapers.", "warning")
            break
            
        all_scrapers_status["current_scraper"] = name
        add_log(f"--- Queue: Starting {name} ---", "info")
        
        # Run the scraper
        try:
            success = run_process_with_logging(cmd, cwd, name, status_dict)
            
            if not success:
                add_log(f"⚠️ {name} failed, but continuing with next scraper...", "error")
            else:
                add_log(f"✅ {name} finished successfully.", "success")
        except Exception as e:
             add_log(f"❌ Critical error executing {name}: {e}. Continuing...", "error")
        
        if stop_all_requested:
            add_log("🛑 Stop All requested. Cancelling remaining scrapers.", "warning")
            break
            
        time.sleep(2) # Brief pause between scrapers
        
    all_scrapers_status["running"] = False
    all_scrapers_status["current_scraper"] = None
    all_scrapers_status["finished_at"] = datetime.now().isoformat()
    if stop_all_requested:
            add_log("⏹️ Sequential run stopped by user.", "warning")
    else:
            add_log("🎉 ALL scrapers finished execution.", "success")

def scheduler_loop():
    """Background loop to check schedule"""
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_scheduler():
    """Start the scheduler thread"""
    # Schedule job every 24 hours (midnight)
    # You can change this to specific time: schedule.every().day.at("00:00").do(run_sequential_job_thread)
    # For now, let's stick to simple "every 24 hours" from start, or explicit time.
    # User asked for "after 24 hours". Let's use 24 hours interval or daily at midnight.
    # Daily at midnight is more robust.
    
    schedule.every().day.at("00:00").do(lambda: threading.Thread(target=run_sequential_scrapers, daemon=True).start())
    
    add_log("⏰ Scheduler started: Will run all scrapers daily at 00:00", "info")
    
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()

# ==================================
# API ROUTES
# ==================================

@app.route('/', methods=['GET', 'OPTIONS'])
@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint"""
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response
    
    response = jsonify({
        "status": "healthy",
        "service": "ForSaleByOwner Scraper API",
        "timestamp": datetime.now().isoformat(),
        "version": "2",
        "trigger_from_url": "clears_already_running"
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/api/geocode', methods=['GET', 'OPTIONS'])
def geocode_proxy():
    """Proxy to Nominatim for geocoding so the frontend avoids CORS/403 when calling from the browser."""
    if request.method == 'OPTIONS':
        r = jsonify({})
        origin = request.headers.get("Origin", "")
        if _is_allowed_origin(origin):
            r.headers.add('Access-Control-Allow-Origin', origin)
        r.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        r.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return r
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"error": "Missing query parameter 'q'"}), 400
    try:
        import urllib.request
        import urllib.parse
        url = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + urllib.parse.quote(q)
        req = urllib.request.Request(url, headers={"User-Agent": "BrivanoScout/1.0 (contact@brivano.io)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        response = jsonify(data)
        origin = request.headers.get("Origin", "")
        if _is_allowed_origin(origin):
            response.headers.add('Access-Control-Allow-Origin', origin)
        return response
    except Exception as e:
        add_log(f"Geocode failed for q={q[:50]!r}: {e}", "warning")
        response = jsonify([])
        origin = request.headers.get("Origin", "")
        if _is_allowed_origin(origin):
            response.headers.add('Access-Control-Allow-Origin', origin)
        return response


def _parse_batchdata_to_skip_trace_result(raw, address_data):
    """Convert BatchData API response to the same shape as Edge Function (SkipTraceResult)."""
    out = {
        "success": True,
        "data": {
            "fullName": None,
            "firstName": None,
            "lastName": None,
            "phones": [],
            "emails": [],
            "confidence": 0,
        },
        "provider": "batchdata",
    }
    if not raw or raw.get("status", {}).get("code") != 200:
        out["message"] = "No owner information found"
        return out
    results_obj = raw.get("results", {})
    persons = results_obj.get("persons", [])
    if not persons:
        out["message"] = "No owner information found"
        return out
    first = persons[0]
    owner = first.get("property", {}).get("owner", {}) or first
    name_obj = owner.get("name", {}) or first.get("name", {})
    first_name = name_obj.get("first") or name_obj.get("first_name")
    last_name = name_obj.get("last") or name_obj.get("last_name")
    full_name = (first_name and last_name and f"{first_name} {last_name}".strip()) or owner.get("fullName") or owner.get("name") or ""
    out["data"]["fullName"] = full_name or None
    out["data"]["firstName"] = first_name
    out["data"]["lastName"] = last_name
    for p in first.get("phoneNumbers", []) or first.get("phones", []) or []:
        num = p.get("number") or p.get("phone") or p.get("phoneNumber") if isinstance(p, dict) else p
        if num and isinstance(num, str):
            out["data"]["phones"].append({"number": num, "type": p.get("type", "unknown") if isinstance(p, dict) else "unknown"})
    for e in first.get("emails", []) or first.get("emailAddresses", []) or []:
        addr = e.get("email") or e.get("address") or e.get("emailAddress") if isinstance(e, dict) else e
        if addr and isinstance(addr, str):
            out["data"]["emails"].append({"address": addr, "type": e.get("type") if isinstance(e, dict) else None})
    if out["data"]["phones"] or out["data"]["emails"] or out["data"]["fullName"]:
        out["data"]["confidence"] = 80
    return out


@app.route('/api/skip-trace', methods=['POST', 'OPTIONS'])
def skip_trace():
    """Single-address skip trace via BatchData (replaces Supabase Edge Function for Skip Trace button)."""
    if request.method == 'OPTIONS':
        # CORS preflight: allow frontend (brivano.io / localhost)
        r = jsonify({"ok": True})
        r.status_code = 200
        origin = request.headers.get("Origin", "")
        if _is_allowed_origin(origin):
            r.headers.add('Access-Control-Allow-Origin', origin)
        r.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        r.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return r
    try:
        body = request.get_json() or {}
        full_address = body.get("fullAddress") or ""
        if not full_address and (body.get("address") or body.get("city") or body.get("state") or body.get("zip")):
            parts = [body.get("address", "").strip(), body.get("city", "").strip(), body.get("state", "").strip(), body.get("zip", "").strip()]
            full_address = ", ".join(p for p in parts if p)
        if not full_address:
            return jsonify({"success": False, "error": "Missing address or fullAddress"}), 400
        from batchdata_worker import BatchDataWorker
        worker = BatchDataWorker()
        if not worker.api_key:
            return jsonify({"success": False, "error": "BATCHDATA_API_KEY not configured"}), 500
        raw = worker.call_batchdata(full_address)
        address_data = worker.parse_address_string(full_address)
        result = _parse_batchdata_to_skip_trace_result(raw, address_data)
        response = jsonify(result)
        origin = request.headers.get("Origin", "")
        if _is_allowed_origin(origin):
            response.headers.add('Access-Control-Allow-Origin', origin)
        return response
    except Exception as e:
        add_log(f"Skip trace error: {e}", "error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/trigger', methods=['POST', 'GET'])
def trigger_scraper():
    """Trigger FSBO scraper"""
    if scraper_status["running"]:
        return jsonify({"error": "FSBO Scraper is already running"}), 400
    
    def worker():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_dir = os.path.join(base_dir, "FSBO_Scraper")
        run_process_with_logging(
            [sys.executable, "forsalebyowner_selenium_scraper.py"],
            scraper_dir,
            "FSBO",
            scraper_status
        )
    
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "FSBO scraper started"})

@app.route('/api/trigger-apartments', methods=['POST', 'GET'])
def trigger_apartments():
    if apartments_scraper_status["running"]:
        return jsonify({"error": "Apartments Scraper is already running"}), 400
    
    city = request.args.get("city", "chicago-il")
    
    def worker():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_dir = os.path.join(base_dir, "Apartments_Scraper")
        run_process_with_logging(
             [sys.executable, "-m", "scrapy", "crawl", "apartments_frbo", "-a", f"city={city}"],
             scraper_dir,
             "Apartments",
             apartments_scraper_status
        )

    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Apartments scraper started"})

@app.route('/api/status-apartments', methods=['GET'])
def get_apartments_status():
    return jsonify({
        "status": "running" if apartments_scraper_status["running"] else "idle",
        "last_run": apartments_scraper_status["last_run"],
        "error": apartments_scraper_status["error"]
    })

@app.route('/api/trigger-zillow-fsbo', methods=['POST', 'GET'])
def trigger_zillow_fsbo():
    if zillow_fsbo_status["running"]:
         return jsonify({"error": "Zillow FSBO Scraper is already running"}), 400
         
    url = request.args.get("url")
    cmd = [sys.executable, "-m", "scrapy", "crawl", "zillow_spider"]
    if url:
        cmd.extend(["-a", f"start_url={url}"])
        
    def worker():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_dir = os.path.join(base_dir, "Zillow_FSBO_Scraper")
        run_process_with_logging(cmd, scraper_dir, "Zillow_FSBO", zillow_fsbo_status)
        
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Zillow FSBO scraper started"})

@app.route('/api/status-zillow-fsbo', methods=['GET'])
def get_zillow_fsbo_status():
    return jsonify({
        "status": "running" if zillow_fsbo_status["running"] else "idle",
        "last_run": zillow_fsbo_status["last_run"],
        "error": zillow_fsbo_status["error"]
    })

@app.route('/api/trigger-zillow-frbo', methods=['POST', 'GET'])
def trigger_zillow_frbo():
    if zillow_frbo_status["running"]:
         return jsonify({"error": "Zillow FRBO Scraper is already running"}), 400
         
    url = request.args.get("url")
    cmd = [sys.executable, "-m", "scrapy", "crawl", "zillow_spider"]
    if url:
        cmd.extend(["-a", f"start_url={url}"])
        
    def worker():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_dir = os.path.join(base_dir, "Zillow_FRBO_Scraper")
        run_process_with_logging(cmd, scraper_dir, "Zillow_FRBO", zillow_frbo_status)
        
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Zillow FRBO scraper started"})

@app.route('/api/status-zillow-frbo', methods=['GET'])
def get_zillow_frbo_status():
    return jsonify({
        "status": "running" if zillow_frbo_status["running"] else "idle",
        "last_run": zillow_frbo_status["last_run"],
        "error": zillow_frbo_status["error"]
    })

@app.route('/api/trigger-hotpads', methods=['POST', 'GET'])
def trigger_hotpads():
    # Always clear "already running" and start (no 400)
    if hotpads_status["running"]:
        hotpads_status["running"] = False
        hotpads_status["error"] = None
        add_log("Cleared Hotpads running state, starting new run.", "info")
    def worker():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_dir = os.path.join(base_dir, "Hotpads_Scraper")
        add_log("Manual trigger for Hotpads received from API", "info")
        run_process_with_logging(
            [sys.executable, "-m", "scrapy", "crawl", "hotpads_scraper"], 
            scraper_dir, 
            "Hotpads", 
            hotpads_status
        )
        
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Hotpads scraper started"})

@app.route('/api/status-hotpads', methods=['GET'])
def get_hotpads_status():
    # Optional: ?reset=1 to clear running state (so trigger-from-url can start again)
    if request.args.get("reset") in ("1", "true", "yes"):
        hotpads_status["running"] = False
        hotpads_status["error"] = None
        add_log("Hotpads status reset via status-hotpads?reset=1", "info")
    return jsonify({
        "status": "running" if hotpads_status["running"] else "idle",
        "last_run": hotpads_status["last_run"],
        "error": hotpads_status["error"]
    })


@app.route('/api/hotpads/reset', methods=['POST', 'GET'])
def reset_hotpads_status():
    """Clear Hotpads 'running' and 'error' state so a new scrape can be started (e.g. after a stuck run)."""
    hotpads_status["running"] = False
    hotpads_status["error"] = None
    add_log("Hotpads status reset (running=False). You can start a new scrape.", "info")
    return jsonify({"message": "Hotpads status reset", "status": "idle"})


def _hotpads_listing_from_db_row(row):
    """Map hotpads_listings table row to the JSON shape the frontend expects."""
    def str_or_none(v):
        return (v or "").strip() or None
    return {
        "address": str_or_none(row.get("address")),
        "bedrooms": _safe_int(row.get("bedrooms")),
        "bathrooms": _safe_float(row.get("bathrooms")),
        "price": str_or_none(row.get("price")),
        "owner_name": str_or_none(row.get("contact_name")),
        "owner_phone": str_or_none(row.get("phone_number")),
        "listing_url": str_or_none(row.get("url")),
        "square_feet": _safe_int(row.get("square_feet")),
        "source_platform": "hotpads",
        "listing_type": "rent",
    }


@app.route('/api/hotpads/last-result', methods=['GET'])
def get_hotpads_last_result():
    """Return Hotpads listings from Supabase hotpads_listings so frontend and DB counts match. Fallback to CSV if DB unavailable."""
    # 1) Prefer Supabase hotpads_listings (single source of truth)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
        if url and key:
            supabase = create_client(url, key)
            r = supabase.table("hotpads_listings").select(
                "address,bedrooms,bathrooms,price,contact_name,phone_number,url,square_feet"
            ).order("updated_at", desc=True).limit(500).execute()
            if r.data:
                listings = [_hotpads_listing_from_db_row(row) for row in r.data]
                return jsonify({"listings": listings, "total": len(listings)})
    except Exception as e:
        add_log(f"Hotpads last-result from Supabase failed, trying CSV: {e}", "warning")
    # 2) Fallback: CSV from scraper output
    import csv
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "Hotpads_Scraper", "output", "Hotpads_Data.csv")
    if not os.path.isfile(csv_path):
        return jsonify({"listings": [], "message": "No results yet. Run a Hotpads scrape first."})
    try:
        listings = []
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                listings.append({
                    "address": (row.get("Address") or "").strip(),
                    "bedrooms": _safe_int(row.get("Bedrooms")),
                    "bathrooms": _safe_float(row.get("Bathrooms")),
                    "price": (row.get("Price") or "").strip(),
                    "owner_name": (row.get("Contact Name") or "").strip(),
                    "owner_phone": (row.get("Phone Number") or "").strip(),
                    "listing_url": (row.get("Url") or "").strip(),
                    "square_feet": _safe_int(row.get("Sqft")),
                    "source_platform": "hotpads",
                    "listing_type": "rent",
                })
        return jsonify({"listings": listings, "total": len(listings)})
    except Exception as e:
        add_log(f"Error reading Hotpads CSV: {e}", "error")
        return jsonify({"listings": [], "error": str(e)}), 500


def _safe_int(val):
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def _safe_float(val):
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


@app.route('/api/trigger-redfin', methods=['POST', 'GET'])
def trigger_redfin():
    if redfin_status["running"]:
        return jsonify({"error": "Redfin Scraper is already running"}), 400
        
    def worker():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_dir = os.path.join(base_dir, "Redfin_Scraper")
        run_process_with_logging(
            [sys.executable, "-m", "scrapy", "crawl", "redfin_spider"], 
            scraper_dir, 
            "Redfin", 
            redfin_status
        )
        
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Redfin scraper started"})

@app.route('/api/status-redfin', methods=['GET'])
def get_redfin_status():
    if request.args.get("reset") in ("1", "true", "yes"):
        redfin_status["running"] = False
        redfin_status["error"] = None
        add_log("Redfin status reset via status-redfin?reset=1", "info")
    return jsonify({
        "status": "running" if redfin_status["running"] else "idle",
        "last_run": redfin_status["last_run"],
        "error": redfin_status["error"]
    })


def _redfin_listing_from_db_row(row):
    """Map redfin_listings row to same shape as Hotpads/Trulia for frontend."""
    def str_or_none(v):
        return (v or "").strip() or None
    return {
        "address": str_or_none(row.get("address")),
        "bedrooms": _safe_int(row.get("beds")),
        "bathrooms": _safe_float(row.get("baths")),
        "price": str_or_none(row.get("price")),
        "owner_name": str_or_none(row.get("owner_name") or row.get("name")),
        "owner_phone": str_or_none(row.get("phones") or row.get("phone_number")),
        "listing_url": str_or_none(row.get("listing_link") or row.get("url")),
        "square_feet": _safe_int(row.get("square_feet")),
        "source_platform": "redfin",
        "listing_type": "sale",
    }


@app.route('/api/redfin/last-result', methods=['GET'])
def get_redfin_last_result():
    """Return Redfin listings from Supabase redfin_listings (same pattern as Hotpads/Trulia last-result)."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
        if url and key:
            supabase = create_client(url, key)
            r = supabase.table("redfin_listings").select(
                "address,price,beds,baths,owner_name,phones,listing_link,square_feet"
            ).order("id", desc=True).limit(500).execute()
            if r.data:
                listings = [_redfin_listing_from_db_row(row) for row in r.data]
                return jsonify({"listings": listings, "total": len(listings)})
    except Exception as e:
        add_log(f"Redfin last-result from Supabase failed: {e}", "warning")
    return jsonify({"listings": [], "message": "No Redfin results yet. Run a Redfin scrape first."})


@app.route('/api/trigger-trulia', methods=['POST', 'GET'])
def trigger_trulia():
    if trulia_status["running"]:
        return jsonify({"error": "Trulia Scraper is already running"}), 400
        
    def worker():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_dir = os.path.join(base_dir, "Trulia_Scraper")
        run_process_with_logging(
            [sys.executable, "-m", "scrapy", "crawl", "trulia_spider"], 
            scraper_dir, 
            "Trulia", 
            trulia_status
        )
        
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Trulia scraper started"})

@app.route('/api/status-trulia', methods=['GET'])
def get_trulia_status():
    if request.args.get("reset") in ("1", "true", "yes"):
        trulia_status["running"] = False
        trulia_status["error"] = None
        add_log("Trulia status reset via status-trulia?reset=1", "info")
    return jsonify({
        "status": "running" if trulia_status["running"] else "idle",
        "last_run": trulia_status["last_run"],
        "error": trulia_status["error"]
    })


def _trulia_listing_from_db_row(row):
    """Map trulia_listings row to same shape as Hotpads for frontend."""
    def str_or_none(v):
        return (v or "").strip() or None
    return {
        "address": str_or_none(row.get("address")),
        "bedrooms": _safe_int(row.get("beds")),
        "bathrooms": _safe_float(row.get("baths")),
        "price": str_or_none(row.get("price")),
        "owner_name": str_or_none(row.get("owner_name") or row.get("name") or row.get("contact_name")),
        "owner_phone": str_or_none(row.get("phones") or row.get("phone_number")),
        "listing_url": str_or_none(row.get("listing_link") or row.get("url")),
        "square_feet": _safe_int(row.get("square_feet")),
        "source_platform": "trulia",
        "listing_type": "sale",
    }


@app.route('/api/trulia/last-result', methods=['GET'])
def get_trulia_last_result():
    """Return Trulia listings from Supabase trulia_listings (same pattern as Hotpads last-result)."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
        if url and key:
            supabase = create_client(url, key)
            r = supabase.table("trulia_listings").select(
                "address,price,beds,baths,owner_name,phones,listing_link,square_feet"
            ).order("id", desc=True).limit(500).execute()
            if r.data:
                listings = [_trulia_listing_from_db_row(row) for row in r.data]
                return jsonify({"listings": listings, "total": len(listings)})
    except Exception as e:
        add_log(f"Trulia last-result from Supabase failed: {e}", "warning")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "Trulia_Scraper", "output", "Trulia_Data.csv")
    if not os.path.isfile(csv_path):
        return jsonify({"listings": [], "message": "No results yet. Run a Trulia scrape first."})
    try:
        import csv as csv_module
        listings = []
        with open(csv_path, "r", encoding="utf-8", newline="", errors="replace") as f:
            reader = csv_module.DictReader(f)
            for row in reader:
                listings.append({
                    "address": (row.get("Address") or "").strip(),
                    "bedrooms": _safe_int(row.get("Bedrooms")),
                    "bathrooms": _safe_float(row.get("Bathrooms")),
                    "price": (row.get("Asking Price") or row.get("Price") or "").strip(),
                    "owner_name": (row.get("Name") or row.get("Contact Name") or "").strip(),
                    "owner_phone": (row.get("Phone Number") or "").strip(),
                    "listing_url": (row.get("Url") or row.get("listing_link") or "").strip(),
                    "square_feet": _safe_int(row.get("Sqft") or row.get("Square Feet")),
                    "source_platform": "trulia",
                    "listing_type": "sale",
                })
        return jsonify({"listings": listings, "total": len(listings)})
    except Exception as e:
        add_log(f"Error reading Trulia CSV: {e}", "error")
        return jsonify({"listings": [], "error": str(e)}), 500


@app.route('/api/test-search', methods=['GET'])
def test_search():
    """Test endpoint to verify server is responding"""
    print("=" * 80)
    print(f"[TEST] Test endpoint hit at {datetime.now().isoformat()}")
    print("=" * 80)
    import sys
    sys.stdout.flush()
    return jsonify({"status": "ok", "message": "Test endpoint working", "timestamp": datetime.now().isoformat()})

@app.route('/api/search-location', methods=['POST', 'GET', 'OPTIONS'])
def search_location():
    """Search a platform for a location and return the actual listing URL."""
    # Immediate log to verify endpoint is hit (safe for Windows console)
    print("=" * 80)
    print(f"[SEARCH-LOCATION] Endpoint hit at {datetime.now().isoformat()}")
    print(f"[SEARCH-LOCATION] Method: {request.method}")
    print(f"[SEARCH-LOCATION] Headers: {_safe_console(dict(request.headers))}")
    print("=" * 80)
    add_log("SEARCH-LOCATION endpoint hit: method=" + str(request.method), "info")
    
    # Handle CORS preflight - MUST be first thing we do
    if request.method == 'OPTIONS':
        add_log("SEARCH-LOCATION: Handling OPTIONS preflight", "info")
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        return response
    
    # Wrap EVERYTHING in try-except to prevent any crash
    import traceback
    import sys
    sys.stdout.flush()  # Force flush to ensure logs appear
    
    try:
        # Get platform and location from request first (safe for Windows console)
        try:
            print(f"[SEARCH-LOCATION] Request JSON: {request.is_json}")
            print(f"[SEARCH-LOCATION] Request data: {_safe_console(request.json if request.is_json else 'Not JSON')}")
            print(f"[SEARCH-LOCATION] Request args: {_safe_console(dict(request.args))}")
            sys.stdout.flush()
            
            if request.is_json and request.json:
                platform = request.json.get('platform')
                location = request.json.get('location')
                property_type = request.json.get('property_type', 'apartments')  # Default to apartments
            else:
                platform = request.args.get('platform') or (request.form.get('platform') if request.form else None)
                location = request.args.get('location') or (request.form.get('location') if request.form else None)
                property_type = request.args.get('property_type') or (request.form.get('property_type') if request.form else 'apartments')
            
            print(f"[SEARCH-LOCATION] Parsed: platform={_safe_console(platform)}, location={_safe_console(location)}")
            sys.stdout.flush()
        except Exception as e:
            add_log(f"Error parsing request: {e}", "error")
            response = jsonify({"error": "Invalid request format"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        if not platform:
            response = jsonify({"error": "Platform parameter is required"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        if not location:
            response = jsonify({"error": "Location parameter is required"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        try:
            print(f"[SEARCH-LOCATION] Starting search for platform={_safe_console(platform)}, location={_safe_console(location)}")
            sys.stdout.flush()
            add_log(f"Starting location search: platform={_safe_console(platform)}, location={_safe_console(location)}", "info")
            
            # For platforms with heavy bot detection, inform user it may take longer
            if platform.lower() in ['trulia', 'redfin', 'apartments.com']:
                add_log("This platform has aggressive bot detection. May take 30-90 seconds", "info")
            
            url = None
            error_occurred = None
            search_timed_out = False
            
            # Hotpads: build URL inline (no LocationSearcher, no logging) to avoid any encoding issues
            if platform and str(platform).strip().lower() == "hotpads":
                try:
                    url = _hotpads_url_inline(location, property_type or "apartments")
                except Exception as e:
                    error_occurred = e
            elif platform and str(platform).strip().lower() == "trulia":
                try:
                    url = _trulia_url_inline(location)
                except Exception as e:
                    error_occurred = e
            else:
                # Run the location search with timeout protection (browser-based platforms)
                try:
                    from utils.location_searcher import LocationSearcher
                    def run_search():
                        nonlocal url, error_occurred
                        try:
                            url = LocationSearcher.search_platform(platform, location, property_type)
                        except Exception as e:
                            error_occurred = e
                    import threading
                    search_thread = threading.Thread(target=run_search, daemon=True)
                    search_thread.start()
                    search_thread.join(timeout=90)
                    search_timed_out = search_thread.is_alive()
                except Exception as import_error:
                    error_occurred = import_error
                    search_timed_out = False
            
            if search_timed_out:
                # Thread is still running - it timed out
                add_log(f"Location search timed out after 90 seconds for {_safe_console(platform)}/{_safe_console(location)}", "error")
                response = jsonify({
                    "error": "Location search timed out. The operation took too long. Please try again or use Browserless.io for better performance.",
                    "platform": platform,
                    "location": location,
                    "error_type": "timeout"
                })
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 504
            
            if error_occurred:
                # Selenium/encoding error occurred - sanitize for Windows console and JSON
                try:
                    error_msg = str(error_occurred).encode('ascii', 'replace').decode('ascii')
                except Exception:
                    error_msg = "An error occurred during location search"
                add_log(f"Selenium error during location search: {error_msg}", "error")
                add_log("Traceback: " + _safe_console(traceback.format_exc()), "error")
                
                response = jsonify({
                    "error": f"Location search failed: {error_msg}. For browser-based platforms ensure Chrome/Chromium is available or set BROWSERLESS_TOKEN.",
                    "platform": platform,
                    "location": location,
                    "error_type": "selenium_error"
                })
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 500
            
            if not url:
                add_log(f"Could not find URL for {_safe_console(platform)}/{_safe_console(location)}", "warning")
                response = jsonify({
                    "error": f"Could not find listing URL for '{location}' on {platform}",
                    "platform": platform,
                    "location": location
                })
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 404
            
            # Validate the URL using URLDetector
            from utils.url_detector import URLDetector
            detected_platform, extracted_location = URLDetector.detect_and_extract(url)
            
            add_log(f"Location search successful: {_safe_console(platform)}/{_safe_console(location)} -> {_safe_console(url)}", "success")
            response = jsonify({
                "url": url,
                "platform": detected_platform or platform,
                "location": extracted_location,
                "success": True
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        except Exception as inner_error:
            # Catch errors in the inner try block - sanitize for encoding
            error_trace = traceback.format_exc()
            add_log(f"Error in location search: {inner_error}", "error")
            add_log(f"Traceback: {error_trace}", "error")
            try:
                err_text = str(inner_error).encode('ascii', 'replace').decode('ascii')
            except Exception:
                err_text = "Error searching location"
            response = jsonify({
                "error": f"Error searching location: {err_text}",
                "platform": platform if 'platform' in locals() else None,
                "location": location if 'location' in locals() else None
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 500
        
    except Exception as outer_error:
        # Catch ANY exception that wasn't caught above
        try:
            error_trace = traceback.format_exc()
            add_log(f"Unhandled error in search_location: {outer_error}", "error")
            add_log(f"Traceback: {error_trace}", "error")
            
            platform_val = platform if 'platform' in locals() else None
            location_val = location if 'location' in locals() else None
            
            try:
                outer_err_text = str(outer_error).encode('ascii', 'replace').decode('ascii')
            except Exception:
                outer_err_text = "Unexpected error"
            response = jsonify({
                "error": f"Unexpected error: {outer_err_text}",
                "platform": platform_val,
                "location": location_val,
                "error_type": "unhandled_exception"
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 500
        except Exception as final_error:
            # Last resort - return minimal response with CORS
            try:
                response = jsonify({"error": "Internal server error - could not process request"})
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 500
            except:
                # Absolute last resort - this should never happen
                return '{"error":"Internal server error"}', 500, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@app.route('/api/validate-url', methods=['POST', 'GET'])
def validate_url():
    """Validate URL and detect platform without triggering scraper."""
    # Get URL from request (POST body or GET query param)
    if request.is_json and request.json:
        url = request.json.get('url')
        expected_platform = request.json.get('expected_platform')
    else:
        url = request.args.get('url') or (request.form.get('url') if request.form else None)
        expected_platform = request.args.get('expected_platform') or (request.form.get('expected_platform') if request.form else None)
    
    if not url:
        return jsonify({"error": "URL parameter is required"}), 400
    
    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        return jsonify({
            "error": "Invalid URL format. URL must start with http:// or https://",
            "isValid": False
        }), 400
    
    # Detect platform and route
    platform, table_name, scraper_config, location = TableRouter.route_url(url)
    
    # Validate against expected platform if provided
    if expected_platform and platform != expected_platform:
        return jsonify({
            "platform": platform,
            "table": table_name,
            "location": location,
            "isValid": False,
            "error": f"URL is for {platform or 'unknown platform'}, but expected {expected_platform}"
        }), 400
    
    if not platform or not table_name:
        return jsonify({
            "platform": None,
            "table": None,
            "location": location,
            "isValid": False,
            "error": "Unknown or unsupported platform"
        }), 400
    
    return jsonify({
        "platform": platform,
        "table": table_name,
        "location": location,
        "isValid": True
    })

@app.route('/api/trigger-from-url', methods=['POST', 'GET'])
def trigger_from_url():
    """Trigger scraper from any URL - automatically detects platform and routes to appropriate scraper."""
    print("[BACKEND] trigger-from-url called", flush=True)
    url = None
    force = False
    # Prefer query string so frontend ?url=...&force=1 always works
    if request.args.get("url"):
        url = request.args.get("url")
        force = force or request.args.get("force") in ("1", "true", "yes")
    # Else try POST body
    if not url and request.method == "POST" and request.get_data():
        try:
            import json as _json
            raw = request.get_data(as_text=True) or "{}"
            data = _json.loads(raw) if isinstance(raw, str) else _json.loads(raw.decode("utf-8", errors="replace"))
            if isinstance(data, dict):
                url = data.get("url") or url
                force = force or data.get("force") in (True, 1, "1", "true", "yes")
        except Exception as e:
            add_log(f"trigger-from-url: could not parse POST body: {e}", "warning")
    if not url and request.is_json and request.json:
        url = request.json.get("url")
        force = force or request.json.get("force") in (True, 1, "1", "true", "yes")
    if not url:
        url = request.form.get("url") if request.form else None
        force = force or (request.form.get("force") in ("1", "true", "yes") if request.form else False)
    if not url:
        print("[BACKEND] trigger-from-url 400: URL parameter is required", flush=True)
        return jsonify({"error": "URL parameter is required"}), 400
    print(f"[BACKEND] trigger-from-url url={url[:80] if len(url) > 80 else url}", flush=True)
    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        print(f"[BACKEND] trigger-from-url 400: Invalid URL format: {url[:80]!r}", flush=True)
        return jsonify({"error": "Invalid URL format. URL must start with http:// or https://"}), 400
    
    # Detect platform and route
    platform, table_name, scraper_config, location = TableRouter.route_url(url)
    
    if not platform or not scraper_config:
        print(f"[BACKEND] trigger-from-url 400: Unknown platform for url={url[:80]!r}", flush=True)
        return jsonify({
            "error": "Unknown or unsupported platform",
            "url": url,
            "detected_location": location
        }), 400
    
    # Get status dict based on platform
    status_dict_map = {
        'apartments.com': apartments_scraper_status,
        'hotpads': hotpads_status,
        'redfin': redfin_status,
        'trulia': trulia_status,
        'zillow_fsbo': zillow_fsbo_status,
        'zillow_frbo': zillow_frbo_status,
        'fsbo': scraper_status,
    }
    
    status_dict = status_dict_map.get(platform)
    if not status_dict:
        return jsonify({"error": f"No status tracking for platform: {platform}"}), 500
    
    # Always clear "already running" and start (no 400 – avoids stuck state for any platform)
    if platform == "hotpads":
        force = True
    if status_dict["running"]:
        status_dict["running"] = False
        status_dict["error"] = None
        add_log(f"Cleared running state for {platform}, starting new scrape.", "info")
    
    # Map platform to scraper name for logging (use capitalized names for consistency)
    scraper_name_map = {
        'apartments.com': 'Apartments',
        'hotpads': 'Hotpads',
        'redfin': 'Redfin',
        'trulia': 'Trulia',
        'zillow_fsbo': 'Zillow_FSBO',
        'zillow_frbo': 'Zillow_FRBO',
        'fsbo': 'FSBO'
    }
    scraper_name = scraper_name_map.get(platform, platform.title())
    
    # Build command based on scraper config
    scraper_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), scraper_config['scraper_dir'])
    url_param = scraper_config['url_param']
    
    if scraper_config['scraper_name'] == 'forsalebyowner_selenium_scraper':
        # FSBO uses a different command structure - now supports --url argument
        cmd = [sys.executable, scraper_config['command'][0], '--url', url]
        env = None
    else:
        # Scrapy-based scrapers
        cmd = [sys.executable] + scraper_config['command'] + [f"{url_param}={url}"]
        env = None
    
    def worker():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        run_process_with_logging(cmd, scraper_dir, scraper_name, status_dict, env=env)
    
    print(f"[BACKEND] >>> STARTING {scraper_name.upper()} SCRAPER (thread) <<<", flush=True)
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "message": f"Scraper started for {platform}",
        "platform": platform,
        "table": table_name,
        "url": url,
        "location": location,
        "scraper_config": {
            "scraper_name": scraper_config['scraper_name'],
            "scraper_dir": scraper_config['scraper_dir']
        }
    })

@app.route('/api/trigger-all', methods=['POST', 'GET'])
def trigger_all():
    global all_scrapers_status
    if all_scrapers_status["running"]:
        return jsonify({"error": "All Scrapers job is already running"}), 400
    
    # Start the sequential runner in a background thread
    thread = threading.Thread(target=run_sequential_scrapers)
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Started sequential run of all scrapers"})

@app.route('/api/status-all', methods=['GET'])
def get_all_status():
    return jsonify({
        "all_scrapers": {
            "running": all_scrapers_status["running"],
            "last_run": all_scrapers_status["last_run"],
            "finished_at": all_scrapers_status["finished_at"],
            "current_scraper": all_scrapers_status["current_scraper"]
        },
        "fsbo": { "status": "running" if scraper_status["running"] else "idle", "last_run": scraper_status["last_run"], "last_result": scraper_status["last_result"] },
        "apartments": { "status": "running" if apartments_scraper_status["running"] else "idle", "last_run": apartments_scraper_status["last_run"], "last_result": apartments_scraper_status["last_result"] },
        "zillow_fsbo": { "status": "running" if zillow_fsbo_status["running"] else "idle", "last_run": zillow_fsbo_status["last_run"], "last_result": zillow_fsbo_status["last_result"] },
        "zillow_frbo": { "status": "running" if zillow_frbo_status["running"] else "idle", "last_run": zillow_frbo_status["last_run"], "last_result": zillow_frbo_status["last_result"] },
        "hotpads": { "status": "running" if hotpads_status["running"] else "idle", "last_run": hotpads_status["last_run"], "last_result": hotpads_status["last_result"] },
        "redfin": { "status": "running" if redfin_status["running"] else "idle", "last_run": redfin_status["last_run"], "last_result": redfin_status["last_result"] },
        "trulia": { "status": "running" if trulia_status["running"] else "idle", "last_run": trulia_status["last_run"], "last_result": trulia_status["last_result"] },
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get logs from the log buffer, optionally filtered by scraper name"""
    scraper_name = request.args.get('scraper', None)
    limit = request.args.get('limit', type=int)
    
    # Get logs from buffer (most recent first)
    logs = list(LOG_BUFFER)
    
    # Filter by scraper name if provided (logs have format "[scraper_name] message" or contain scraper name)
    if scraper_name:
        # Map platform names to scraper names used in logs
        scraper_name_map = {
            'apartments': 'Apartments',
            'apartments.com': 'Apartments',
            'hotpads': 'Hotpads',
            'redfin': 'Redfin',
            'trulia': 'Trulia',
            'zillow_fsbo': 'Zillow_FSBO',
            'zillow_frbo': 'Zillow_FRBO',
            'fsbo': 'FSBO'
        }
        log_scraper_name = scraper_name_map.get(scraper_name, scraper_name)
        # Filter logs that start with [scraper_name] (strict matching)
        # Only match logs that explicitly start with the scraper name in brackets
        logs = [
            log for log in logs 
            if log["message"].startswith(f"[{log_scraper_name}]")
            or log["message"].startswith(f"[{log_scraper_name.lower()}]")
        ]
    
    # Limit number of logs if specified (most recent)
    # Note: Reverse the list first to get most recent logs, then take limit from the end
    if limit and limit > 0:
        logs = logs[-limit:] if len(logs) > limit else logs
    
    # Reverse to show most recent first (newest at the end of the list)
    logs.reverse()
    
    return jsonify({
        "logs": logs,
        "total": len(logs)
    })

@app.route('/api/stop-scraper', methods=['GET', 'POST'])
def stop_scraper():
    id = request.args.get('id')
    if not id:
        return jsonify({"error": "Missing id"}), 400
    
    # Map friendly IDs to internal names
    id_map = {
        "fsbo": "FSBO",
        "apartments": "Apartments",
        "zillow_fsbo": "Zillow_FSBO",
        "zillow_frbo": "Zillow_FRBO",
        "hotpads": "Hotpads",
        "redfin": "Redfin",
        "trulia": "Trulia"
    }
    
    internal_name = id_map.get(id, id)
    process_found = False
    
    if internal_name in active_processes:
        add_log(f"Stopping {internal_name} requested by user...", "info")
        ensure_process_killed(internal_name)
        process_found = True
    
    # Reset status dictionaries even if process handle was missing
    status_updated = False
    if id == "fsbo":
        if scraper_status["running"]: status_updated = True
        scraper_status["running"] = False
    elif id == "apartments":
        if apartments_scraper_status["running"]: status_updated = True
        apartments_scraper_status["running"] = False
    elif id == "zillow_fsbo":
        if zillow_fsbo_status["running"]: status_updated = True
        zillow_fsbo_status["running"] = False
    elif id == "zillow_frbo":
        if zillow_frbo_status["running"]: status_updated = True
        zillow_frbo_status["running"] = False
    elif id == "hotpads":
        if hotpads_status["running"]: status_updated = True
        hotpads_status["running"] = False
    elif id == "redfin":
        if redfin_status["running"]: status_updated = True
        redfin_status["running"] = False
    elif id == "trulia":
        if trulia_status["running"]: status_updated = True
        trulia_status["running"] = False
        
    if process_found:
        return jsonify({"message": f"Stopped {internal_name}"}), 200
    elif status_updated:
        add_log(f"Reset {internal_name} status (no active process handle found)", "info")
        return jsonify({"message": f"Reset {internal_name} status"}), 200
    
    return jsonify({"error": "Scraper not running"}), 404

@app.route('/api/stop-all', methods=['GET', 'POST'])
def stop_all():
    global stop_all_requested, all_scrapers_status
    if not all_scrapers_status["running"]:
        return jsonify({"error": "No sequential run active"}), 400
    
    stop_all_requested = True
    add_log("🛑 User requested to stop ALL scrapers.", "warning")
    
    # Immediately update all_scrapers_status to reflect stop
    all_scrapers_status["running"] = False
    all_scrapers_status["current_scraper"] = None
    
    # Immediately stop ALL active processes, not just the current one
    stopped_count = 0
    for scraper_name in list(active_processes.keys()):
        if scraper_name != "Enrichment":  # Don't stop enrichment when stopping scrapers
            ensure_process_killed(scraper_name)
            stopped_count += 1
    
    # Also update status for all scrapers immediately
    scraper_status["running"] = False
    apartments_scraper_status["running"] = False
    zillow_fsbo_status["running"] = False
    zillow_frbo_status["running"] = False
    hotpads_status["running"] = False
    redfin_status["running"] = False
    trulia_status["running"] = False
    
    message = f"Stop request received. Stopping {stopped_count} active scraper(s)."
    return jsonify({"message": message}), 200

@app.route('/api/trigger-enrichment', methods=['POST', 'GET'])
def trigger_enrichment():
    if enrichment_status["running"]:
        return jsonify({"error": "Enrichment is already running"}), 400
    
    limit = request.args.get("limit", 50)
    source = request.args.get("source") # Optional priority source
    
    try:
        limit = int(limit)
    except:
        limit = 50
        
    def worker():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        cmd = [sys.executable, "batchdata_worker.py", "--limit", str(limit)]
        if source:
            cmd.extend(["--source", source])
            
        run_process_with_logging(
            cmd,
            base_dir,
            "Enrichment",
            enrichment_status
        )
    
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    msg = f"Enrichment started with limit {limit}"
    if source:
        msg += f" (Prioritizing {source})"
        
    return jsonify({"message": msg})

@app.route('/api/status-enrichment', methods=['GET'])
def get_enrichment_status():
    return jsonify({
        "status": "running" if enrichment_status["running"] else "idle",
        "last_run": enrichment_status["last_run"],
        "error": enrichment_status["error"]
    })

@app.route('/api/enrichment-stats', methods=['GET'])
def get_enrichment_stats():
    """Return enrichment statistics for dashboard display."""
    try:
        from supabase import create_client
        from dotenv import load_dotenv
        load_dotenv()
        
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            return jsonify({"error": "Database not configured"}), 500
            
        supabase = create_client(url, key)
        
        # Get counts by status from enrichment_state (for queue tracking)
        pending = supabase.table("property_owner_enrichment_state") \
            .select("*", count="exact", head=True) \
            .eq("status", "never_checked") \
            .eq("locked", False) \
            .execute()
            
        enriched_state = supabase.table("property_owner_enrichment_state") \
            .select("*", count="exact", head=True) \
            .eq("status", "enriched") \
            .execute()
            
        no_data = supabase.table("property_owner_enrichment_state") \
            .select("*", count="exact", head=True) \
            .eq("status", "no_owner_data") \
            .execute()
        
        # Count by source_used to show smart skips
        scraped = supabase.table("property_owner_enrichment_state") \
            .select("*", count="exact", head=True) \
            .eq("source_used", "scraped") \
            .execute()
            
        # Only count ACTUAL paid API calls (exclude buggy never_checked entries)
        batchdata = supabase.table("property_owner_enrichment_state") \
            .select("*", count="exact", head=True) \
            .eq("source_used", "batchdata") \
            .neq("status", "never_checked") \
            .execute()
        
        # Get ACTUAL count from property_owners table (source of truth)
        # This is the real number of addresses with owner data
        property_owners_total = supabase.table("property_owners") \
            .select("*", count="exact", head=True) \
            .execute()
        
        return jsonify({
            "pending": pending.count or 0,
            "enriched": enriched_state.count or 0,  # Count from enrichment_state (for queue tracking)
            "enriched_owners": property_owners_total.count or 0,  # ACTUAL count from property_owners table
            "no_data": no_data.count or 0,
            "smart_skipped": scraped.count or 0,
            "api_calls": batchdata.count or 0,
            "is_running": enrichment_status["running"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start scheduler in background (runs all scrapers daily at midnight)
    start_scheduler()
    
    port = int(os.environ.get('PORT', 8080))
    this_file = os.path.abspath(__file__)
    print("", flush=True)
    print(">>> SCRAPER BACKEND - Requests to /api/* will log [BACKEND] lines below.", flush=True)
    print(">>> Keep this terminal open when using Find Listings in the app.", flush=True)
    print(f">>> Using: {this_file}", flush=True)
    print("", flush=True)
    app.run(host='0.0.0.0', port=port, debug=False)
