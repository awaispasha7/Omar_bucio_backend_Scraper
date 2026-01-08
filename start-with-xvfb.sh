#!/bin/bash
# Helper script to start xvfb and run the application
# This allows non-headless mode on Linux servers

# Check if HEADLESS_BROWSER is false and we're on Linux
if [ "$HEADLESS_BROWSER" = "false" ] && [ "$(uname)" = "Linux" ]; then
    # Check if DISPLAY is already set
    if [ -z "$DISPLAY" ]; then
        echo "🖥️  Starting X Virtual Framebuffer (xvfb) for non-headless mode..."
        # Start xvfb on display :99
        Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset > /dev/null 2>&1 &
        XVFB_PID=$!
        
        # Set DISPLAY environment variable
        export DISPLAY=:99
        
        # Wait a moment for xvfb to start
        sleep 1
        
        # Verify xvfb is running
        if ps -p $XVFB_PID > /dev/null; then
            echo "✅ xvfb started successfully on DISPLAY=:99 (PID: $XVFB_PID)"
        else
            echo "⚠️  xvfb failed to start, falling back to headless mode"
            export DISPLAY=""
        fi
    else
        echo "✅ DISPLAY already set to $DISPLAY"
    fi
fi

# Execute the original command
exec "$@"

