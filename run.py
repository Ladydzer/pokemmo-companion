"""Entry point wrapper for PyInstaller — avoids relative import issues."""
import sys
import os

# When running as PyInstaller bundle, adjust paths
if getattr(sys, 'frozen', False):
    # Running as compiled .exe
    base_path = sys._MEIPASS
    os.chdir(base_path)
    sys.path.insert(0, base_path)

# Pass --debug flag to start with debug overlay active
if "--debug" in sys.argv:
    os.environ["POKEMMO_DEBUG"] = "1"

from src.main import main

if __name__ == "__main__":
    main()
