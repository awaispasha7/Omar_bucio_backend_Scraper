# XServer Setup Guide for Non-Headless Browser Testing

This guide explains how to set up XServer support for non-headless browser testing on different platforms.

## What is XServer?

XServer (X Window System) is a display server that provides a graphical interface. Browsers need XServer to render windows when running in non-headless mode.

## Platform-Specific Setup

### ✅ Windows / Mac (Local Development)

**No setup needed!** Windows and Mac have native GUI support.

Just set in your `.env` file:
```env
HEADLESS_BROWSER=false
```

The browser window will appear automatically.

---

### 🐧 Linux Server (Railway/Docker/Remote)

On Linux servers, you have **three options**:

#### Option 1: Use xvfb (X Virtual Framebuffer) - **RECOMMENDED**

`xvfb` creates a virtual display that browsers can use. It's already installed in the Dockerfile.

**Method A: Set DISPLAY environment variable (Manual)**

1. Start xvfb in the background:
```bash
Xvfb :99 -screen 0 1920x1080x24 &
```

2. Set DISPLAY environment variable:
```bash
export DISPLAY=:99
```

3. Set HEADLESS_BROWSER:
```env
HEADLESS_BROWSER=false
DISPLAY=:99
```

**Method B: Use xvfb-run wrapper (Recommended for testing)**

Create a wrapper script or use xvfb-run directly:

```bash
# Run your Python script with xvfb
xvfb-run -a -s "-screen 0 1920x1080x24" python your_script.py
```

Or modify your startup command in Railway/Render:
```
xvfb-run -a -s "-screen 0 1920x1080x24" gunicorn -w 1 -b 0.0.0.0:$PORT --timeout 120 api_server:app
```

**Method C: Auto-start xvfb in Dockerfile**

You can modify the Dockerfile to auto-start xvfb:

```dockerfile
# Start xvfb in background
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x24 &\nexport DISPLAY=:99\nexec "$@"' > /start-with-xvfb.sh
RUN chmod +x /start-with-xvfb.sh

# Use it as entrypoint
ENTRYPOINT ["/start-with-xvfb.sh"]
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8080", "--timeout", "120", "api_server:app"]
```

#### Option 2: VNC Server (For Remote Viewing)

If you want to **see** the browser window remotely:

1. Install VNC server:
```bash
apt-get install -y x11vnc xvfb
```

2. Start xvfb and VNC:
```bash
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb -forever -shared &
```

3. Connect via VNC client to port 5900

#### Option 3: X11 Forwarding (SSH only)

If connecting via SSH:

```bash
ssh -X user@server
export DISPLAY=localhost:10.0
```

---

## Quick Setup for Railway

For Railway deployment, the easiest approach is **Option 1B** (xvfb-run):

1. **Modify your Railway start command** to use xvfb-run:
   ```
   xvfb-run -a -s "-screen 0 1920x1080x24" gunicorn -w 1 -b 0.0.0.0:$PORT --timeout 120 api_server:app
   ```

2. **Set environment variable in Railway dashboard**:
   ```
   HEADLESS_BROWSER=false
   ```

3. Deploy! The browser will run with a virtual display.

---

## Testing Locally vs Production

### Local Development (Windows/Mac)
```env
HEADLESS_BROWSER=false
```
✅ Works immediately - browser window appears

### Production (Railway/Linux)
```env
HEADLESS_BROWSER=false
DISPLAY=:99  # If using xvfb method A
```
✅ Use xvfb-run in start command (method B) OR set DISPLAY manually

### Production (Default - Headless)
```env
HEADLESS_BROWSER=true
# or just don't set it
```
✅ Always works - no XServer needed

---

## Troubleshooting

### Error: "No display found" or "XServer not running"

**Solution**: 
- Make sure DISPLAY is set: `export DISPLAY=:99`
- Make sure xvfb is running: `ps aux | grep Xvfb`
- Or use xvfb-run wrapper

### Error: "xvfb-run: command not found"

**Solution**: 
- xvfb is already installed in Dockerfile
- If missing, run: `apt-get install -y xvfb`

### Browser still runs headless even with HEADLESS_BROWSER=false

**Check**:
1. Environment variable is actually set (check with `echo $HEADLESS_BROWSER`)
2. DISPLAY is set on Linux (`echo $DISPLAY`)
3. xvfb is running (if on Linux server)

---

## Performance Note

⚠️ **Non-headless mode is slower and uses more resources!**
- Use only for debugging/development
- Always use headless mode in production for better performance

---

## Summary

| Platform | Setup Required | Command |
|----------|---------------|---------|
| **Windows/Mac** | None | Just set `HEADLESS_BROWSER=false` |
| **Linux Local** | None (if GUI) | Set `HEADLESS_BROWSER=false` |
| **Linux Server** | xvfb | Use `xvfb-run` or set `DISPLAY=:99` |
| **Production** | None | Use headless (default) |

For Railway: Use `xvfb-run` in your start command + `HEADLESS_BROWSER=false` env var.

