# Use a standard Python image
FROM python:3.11-slim

# Install system dependencies for Selenium/Chromium
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libstdc++6 \
    chromium \
    chromium-driver \
    libnss3 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -v -r requirements.txt

# Verify critical packages are installed (fail build if missing)
RUN python -c "import selenium; from selenium import webdriver; print('✓ selenium installed successfully')" || (echo "ERROR: selenium failed to install" && exit 1)

# Install Playwright system dependencies manually (for Debian Trixie compatibility)
# Playwright's install-deps has issues with newer Debian versions, so we install manually
# Also install xvfb (X Virtual Framebuffer) for non-headless browser testing on headless servers
RUN apt-get update && apt-get install -y \
    fonts-unifont \
    fonts-liberation \
    fonts-noto-color-emoji \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers for location searches (Trulia, etc.)
# We need Playwright browsers for interactive location searches
RUN playwright install chromium
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# Copy the rest of the application
COPY . .

# Make xvfb helper script executable (if it exists)
RUN if [ -f /app/start-with-xvfb.sh ]; then chmod +x /app/start-with-xvfb.sh; fi

# Expose the port Railway provides (default is often 8080, but Railway sets $PORT)
EXPOSE 8080

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Start command using the xvfb helper script (auto-starts xvfb if HEADLESS_BROWSER=false)
# The script will start xvfb if needed, then run Gunicorn
CMD ["/app/start-with-xvfb.sh", "sh", "-c", "gunicorn -w 1 -b 0.0.0.0:$PORT --timeout 120 --keep-alive 5 api_server:app"]
