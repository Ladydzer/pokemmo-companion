"""Entry point wrapper for PyInstaller — avoids relative import issues."""
import sys
import os

# When running as PyInstaller bundle, adjust paths
if getattr(sys, 'frozen', False):
    # Running as compiled .exe
    base_path = sys._MEIPASS
    os.chdir(base_path)
    sys.path.insert(0, base_path)

from src.main import main

if __name__ == "__main__":
    main()
