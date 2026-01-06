"""
Launcher for the enhanced UI app. Running this module executes the
real enhanced server script located at `enhanced_ui/app_enhanced.py`.

This allows you to run the enhanced app from the repository root with:

  python app.py
"""

import os
import runpy
import sys
import pytesseract

# ---------------------------------------------------------
# WINDOWS OCR CONFIGURATION (DO NOT CHANGE)
# ---------------------------------------------------------

TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin"

# Set Tesseract executable path
if os.path.exists(TESSERACT_EXE):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
else:
    print("❌ Tesseract not found at:", TESSERACT_EXE)

# Make Poppler available to pdf2image
if os.path.exists(POPPLER_PATH):
    os.environ["PATH"] += os.pathsep + POPPLER_PATH
else:
    print("❌ Poppler not found at:", POPPLER_PATH)

# ---------------------------------------------------------
# LAUNCH ENHANCED FLASK APP
# ---------------------------------------------------------

if __name__ == "__main__":
    # Ensure repository root is on sys.path
    repo_root = os.getcwd()
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    enhanced_path = os.path.join(repo_root, "enhanced_ui", "app_enhanced.py")

    if not os.path.exists(enhanced_path):
        print(f"❌ Enhanced app not found: {enhanced_path}")
        sys.exit(1)

    # Run enhanced app as main
    runpy.run_path(enhanced_path, run_name="__main__")
