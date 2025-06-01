# build_deckbuilder_exe.py
# ----------------------------------------
# This script assumes PyInstaller is already installed (pip install pyinstaller).
#
# It uses a hard‐coded absolute path for your deckbuilder project folder,
# rather than reading from a config file. Adjust PROJECT_DIR below if needed.
#
# When you run this script, it will:
#   1. cd into PROJECT_DIR (where main.py lives).
#   2. Invoke PyInstaller to bundle main.py (plus card_data/ and card_images/) into one .exe.
#
# Usage:
#   python build_deckbuilder_exe.py
# ----------------------------------------

import os
import subprocess
import sys

def main():
    # ── HARDCODED PROJECT DIRECTORY ──
    # Replace this with the absolute path to your deckbuilder folder.
    # Example given your deckbuilder sits at E:\Scripts\deckbuilder:
    PROJECT_DIR = r"E:\Scripts\deckbuilder"
    # ──────────────────────────────────

    if not os.path.isdir(PROJECT_DIR):
        print(f"ERROR: PROJECT_DIR not found: {PROJECT_DIR}")
        sys.exit(1)

    main_py = os.path.join(PROJECT_DIR, "main.py")
    if not os.path.isfile(main_py):
        print(f"ERROR: main.py not found in {PROJECT_DIR}")
        sys.exit(1)

    # Change into the project directory
    os.chdir(PROJECT_DIR)
    print(f"[*] Building from directory: {PROJECT_DIR}")

    # Build command for PyInstaller
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--add-data", "card_data;card_data",
        "--add-data", "card_images;card_images",
        "main.py"
    ]

    print("[*] Running PyInstaller...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: PyInstaller failed (exit code {e.returncode})")
        sys.exit(1)

    exe_path = os.path.join(PROJECT_DIR, "dist", "main.exe")
    print("\n[+] Build complete!")
    print(f"Executable located at:\n  {exe_path}\n")

if __name__ == "__main__":
    main()
