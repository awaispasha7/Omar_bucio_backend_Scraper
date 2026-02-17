# How to run the HotPads scraper

You can run the HotPads scraper **from the Brivano Scout UI** (recommended) or **standalone** from the command line.

---

## Option 1: From Brivano Scout UI (recommended)

The UI calls the scraper backend; both must be running.

### 1. Install and start the scraper backend

From the project root:

```bash
cd Scraper_backend
```

- **Windows:** double-click `RUN-BACKEND.bat` or in a terminal run:
  ```bash
  RUN-BACKEND.bat
  ```
- **Mac/Linux:** create a venv if needed, then:
  ```bash
  python api_server.py
  ```

Wait until you see something like **"Running on http://127.0.0.1:8080"**. Leave this terminal open.

### 2. Start the frontend

In a **second terminal**:

```bash
cd birvanoio
npm run dev
```

Open **http://localhost:5173** in your browser and sign in.

### 3. Run the HotPads scraper from the UI

1. Go to **Brivano Scout** → **Real Estate** tab.
2. Enter a **location** (e.g. `Minneapolis` or `Minneapolis, MN`).
3. Set **Platform** to **HotPads**.
4. Set **Listing Type** (e.g. "For Rent...").
5. Click **Find Listings**.

The backend will run the Scrapy spider for that HotPads URL; results appear in the UI (and optionally in Supabase / CSV).

### Backend not running?

If you see **"HotPads scraper backend is not running"** or `ERR_CONNECTION_REFUSED` on port 8080, start the backend (step 1) and try again. You can also use **Platform: All Platforms** to use the FSBO/FRBO Supabase Edge Function instead (no local backend needed).

---

## Option 2: Standalone (command line)

Run the Scrapy spider directly from `Hotpads_Scraper`.

### 1. Dependencies

From **Scraper_backend** (parent folder):

```bash
cd Scraper_backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment (optional but recommended)

- **Zyte API key** (for reliable scraping): in `Hotpads_Scraper/.env` set:
  ```env
  ZYTE_API_KEY=your_key_here
  ```
- **Supabase** (to save to `hotpads_listings`): in the same `.env` add:
  ```env
  SUPABASE_URL=your_project_url
  SUPABASE_SERVICE_KEY=your_service_role_key
  ```
  See `supabase_hotpads_setup.sql` for the table schema.

### 3. Run the spider

**From `Scraper_backend`** (so Scrapy finds the project):

```bash
cd Scraper_backend
# Optional: activate venv first
python -m scrapy crawl hotpads_scraper -a url="https://hotpads.com/minneapolis-mn/for-rent-by-owner?isListedByOwner=true&listingTypes=rental"
```

Or **from inside `Hotpads_Scraper`**:

```bash
cd Scraper_backend/Hotpads_Scraper
scrapy crawl hotpads_scraper -a url="https://hotpads.com/minneapolis-mn/for-rent-by-owner?isListedByOwner=true&listingTypes=rental"
```

**Using a locations CSV** (spider reads URLs/locations from `input/locations.csv`):

```bash
cd Scraper_backend/Hotpads_Scraper
scrapy crawl hotpads_scraper -a use_csv=true
```

### Output

- **CSV:** `Hotpads_Scraper/output/Hotpads_Data.csv`
- **Supabase:** table `hotpads_listings` (if configured)

---

## Summary

| Method              | Backend (port 8080) | Frontend (5173) | Use case                    |
|---------------------|---------------------|-----------------|-----------------------------|
| Brivano Scout UI    | Yes                 | Yes             | Normal use, pick location   |
| Standalone Scrapy   | No                  | No              | Scripting, custom URLs/CSV  |

For normal use, run the **backend** and **frontend**, then use **Find Listings** with **Platform: HotPads** in Brivano Scout.
