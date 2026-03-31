"""Launch PokeMMO Companion web UI.

Opens a beautiful web interface in your browser.

Usage:
    python web.py
"""
import sys
import os
import webbrowser
import threading
import time

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)
    sys.path.insert(0, sys._MEIPASS)

from src.utils.logger import log

PORT = 8080


def main():
    log.info("PokeMMO Companion Web v0.3.0 starting...")

    # Open browser after a short delay
    def open_browser():
        time.sleep(1.5)
        # Try Edge in app mode first (looks like a native app)
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        for edge in edge_paths:
            if os.path.exists(edge):
                os.system(f'"{edge}" --app=http://localhost:{PORT}')
                return
        # Fallback to default browser
        webbrowser.open(f"http://localhost:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    # Start server
    import uvicorn
    log.info(f"Serveur web sur http://localhost:{PORT}")
    uvicorn.run("src.web.server:app", host="127.0.0.1", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
