"""
Launcher for the enhanced UI app. Running this module executes the
real enhanced server script located at `enhanced_ui/app_enhanced.py`.

This allows you to run the enhanced app from the repository root with:

  python app_enhanced.py

which will in turn execute the full `enhanced_ui/app_enhanced.py` server.
"""

import os
import runpy
import sys

if __name__ == "__main__":
    # Ensure repository root is on sys.path so relative imports inside the
    # enhanced script behave as expected.
    repo_root = os.getcwd()
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    enhanced_path = os.path.join(repo_root, "enhanced_ui", "app_enhanced.py")
    if not os.path.exists(enhanced_path):
        print(f"enhanced script not found: {enhanced_path}")
        sys.exit(1)

    # Run the enhanced server as __main__ (this keeps behaviour identical to
    # running the script directly).
    runpy.run_path(enhanced_path, run_name="__main__")
