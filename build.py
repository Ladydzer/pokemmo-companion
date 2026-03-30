"""Build script for PokeMMO Companion .exe using PyInstaller.

Usage:
    python build.py

Produces: dist/PokeMMO-Companion.exe (standalone, ~50-80 MB)
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def main():
    print("=" * 60)
    print("PokeMMO Companion — Build .exe")
    print("=" * 60)

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Check database exists
    db_path = PROJECT_ROOT / "data" / "pokemon.db"
    if not db_path.exists():
        print("ERROR: pokemon.db not found. Run build scripts first:")
        print("  python scripts/build_database.py")
        print("  python scripts/import_spawns.py")
        print("  python scripts/build_progression.py")
        sys.exit(1)

    print(f"Database: {db_path} ({db_path.stat().st_size // 1024} KB)")

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "PokeMMO-Companion",
        "--add-data", f"{db_path};data",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "bettercam",
        "--hidden-import", "pytesseract",
        "--hidden-import", "cv2",
        "--hidden-import", "keyboard",
        "src/main.py",
    ]

    print(f"\nRunning: {' '.join(cmd)}")
    print("This may take a few minutes...\n")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if result.returncode == 0:
        exe_path = PROJECT_ROOT / "dist" / "PokeMMO-Companion.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\nBuild successful!")
            print(f"  Output: {exe_path}")
            print(f"  Size: {size_mb:.1f} MB")
        else:
            print("\nBuild completed but .exe not found in expected location")
    else:
        print(f"\nBuild failed with exit code {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
