"""
Simple Flask API server for Railway deployment
Provides endpoints to trigger scraper and check status
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import os
import threading
from datetime import datetime

app = Flask(__name__)
# Enable CORS for all routes - allows frontend to call backend API
# You can restrict to specific origins if needed: CORS(app, origins=["https://scraperfrontend-production.up.railway.app"])
CORS(app)

# Global variables to track scraper status
scraper_status = {
    "running": False,
    "last_run": None,
    "last_result": None,
    "error": None
}

# Separate status tracking for apartments scraper
apartments_scraper_status = {
    "running": False,
    "last_run": None,
    "last_result": None,
    "error": None
}

def run_scraper():
    """Run the scraper in a separate thread"""
    global scraper_status
    
    if scraper_status["running"]:
        return {"error": "Scraper is already running"}
    
    scraper_status["running"] = True
    scraper_status["error"] = None
    scraper_status["last_run"] = datetime.now().isoformat()
    
    def execute_scraper():
        try:
            # Run the scraper script
            result = subprocess.run(
                ["python3", "forsalebyowner_selenium_scraper.py"],
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            scraper_status["last_result"] = {
                "success": result.returncode == 0,
                "stdout": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
                "stderr": result.stderr[-1000:] if result.stderr else "",  # Last 1000 chars
                "returncode": result.returncode
            }
            
            if result.returncode != 0:
                scraper_status["error"] = result.stderr[-500:] if result.stderr else "Unknown error"
        except subprocess.TimeoutExpired:
            scraper_status["error"] = "Scraper timed out after 1 hour"
            scraper_status["last_result"] = {"success": False, "error": "Timeout"}
        except Exception as e:
            scraper_status["error"] = str(e)
            scraper_status["last_result"] = {"success": False, "error": str(e)}
        finally:
            scraper_status["running"] = False
    
    # Start scraper in background thread
    thread = threading.Thread(target=execute_scraper)
    thread.daemon = True
    thread.start()
    
    return {"message": "Scraper started", "started_at": scraper_status["last_run"]}

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "ForSaleByOwner Scraper API",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get scraper status"""
    return jsonify({
        "status": "running" if scraper_status["running"] else "idle",
        "last_run": scraper_status["last_run"],
        "last_result": scraper_status["last_result"],
        "error": scraper_status["error"],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/trigger', methods=['POST'])
def trigger_scraper():
    """Trigger the scraper"""
    result = run_scraper()
    return jsonify(result)

@app.route('/api/trigger', methods=['GET'])
def trigger_scraper_get():
    """Trigger the scraper via GET (for easy testing)"""
    result = run_scraper()
    return jsonify(result)

@app.route('/api/trigger-apartments', methods=['POST'])
def trigger_apartments_scraper():
    """Trigger the apartments scraper"""
    global apartments_scraper_status
    
    if apartments_scraper_status["running"]:
        return jsonify({"error": "Apartments scraper is already running"}), 400
    
    # Get city parameter from request before starting thread (request context not available in thread)
    city = "chicago-il"
    if request.is_json and request.json:
        city = request.json.get("city", city)
    elif request.args:
        city = request.args.get("city", city)
    
    apartments_scraper_status["running"] = True
    apartments_scraper_status["error"] = None
    apartments_scraper_status["last_run"] = datetime.now().isoformat()
    
    def execute_apartments_scraper(city_param):
        try:
            # Get the base directory (where api_server.py is located)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Path to apartments scraper directory
            scraper_dir = os.path.join(base_dir, "apartments home", "apartments", "apartments")
            
            if not os.path.exists(scraper_dir):
                apartments_scraper_status["error"] = f"Scraper directory not found: {scraper_dir}"
                apartments_scraper_status["last_result"] = {
                    "success": False,
                    "error": apartments_scraper_status["error"],
                    "stdout": "",
                    "stderr": apartments_scraper_status["error"],
                    "returncode": 1
                }
                apartments_scraper_status["running"] = False
                return
            
            # Run the apartments scraper using Scrapy
            # The scraper will automatically upload to Supabase via SupabasePipeline
            result = subprocess.run(
                ["python3", "-m", "scrapy", "crawl", "apartments_frbo", "-a", f"city={city_param}"],
                cwd=scraper_dir,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            apartments_scraper_status["last_result"] = {
                "success": result.returncode == 0,
                "stdout": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
                "stderr": result.stderr[-1000:] if result.stderr else "",  # Last 1000 chars
                "returncode": result.returncode,
                "city": city_param
            }
            
            if result.returncode != 0:
                apartments_scraper_status["error"] = result.stderr[-500:] if result.stderr else "Unknown error"
        except subprocess.TimeoutExpired:
            apartments_scraper_status["error"] = "Apartments scraper timed out after 1 hour"
            apartments_scraper_status["last_result"] = {
                "success": False,
                "error": "Timeout",
                "stdout": "",
                "stderr": "Scraper timed out after 1 hour",
                "returncode": -1
            }
        except Exception as e:
            apartments_scraper_status["error"] = str(e)
            apartments_scraper_status["last_result"] = {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
        finally:
            apartments_scraper_status["running"] = False
    
    # Start scraper in background thread
    thread = threading.Thread(target=execute_apartments_scraper, args=(city,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "message": "Apartments scraper started",
        "started_at": apartments_scraper_status["last_run"],
        "city": city,
        "note": "Scraper will automatically upload results to Supabase"
    })

@app.route('/api/trigger-apartments', methods=['GET'])
def trigger_apartments_scraper_get():
    """Trigger the apartments scraper via GET (for easy testing)"""
    return trigger_apartments_scraper()

@app.route('/api/status-apartments', methods=['GET'])
def get_apartments_status():
    """Get apartments scraper status"""
    return jsonify({
        "status": "running" if apartments_scraper_status["running"] else "idle",
        "last_run": apartments_scraper_status["last_run"],
        "last_result": apartments_scraper_status["last_result"],
        "error": apartments_scraper_status["error"],
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Get port from environment variable or use default 8080
    port = int(os.environ.get('PORT', 8080))
    # Run on 0.0.0.0 to accept connections from outside
    app.run(host='0.0.0.0', port=port, debug=False)

