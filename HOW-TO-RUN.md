# How to run the scraper backend

- **Frontend (Brivano Scout UI)** runs in one terminal: from `birvanoio` run `npm run dev` (port 5173). That terminal only shows Vite/frontend logs.
- **Backend (scraper API)** runs in a **separate** terminal: from `Scraper_backend` run **`RUN-BACKEND.bat`** or `python api_server.py` (port 8080). **Backend logs appear only in this terminal** when you click "Find Listings".

So you need **two terminals**:
1. `birvanoio` → `npm run dev` (frontend)
2. `Scraper_backend` → `RUN-BACKEND.bat` or `python api_server.py` (backend; this is where you see `[BACKEND]` and scraper activity)
