import sys
import os
import webbrowser
import threading
import time
import streamlit.web.cli as stcli

def open_browser():
    time.sleep(3)
    webbrowser.open("http://localhost:8501")

if __name__ == "__main__":
    # Locate embedded app.py inside PyInstaller's bundle folder
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(base_dir, "app.py")
    
    # Trigger browser launch on a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run Streamlit CLI with embedded app path
    sys.argv = [
        "streamlit", 
        "run", 
        app_path, 
        "--global.developmentMode=false", 
        "--server.headless=true"
    ]
    sys.exit(stcli.main())