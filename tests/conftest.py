import sys
from pathlib import Path

# Get the project root directory (one level above tests/)
ROOT_DIR = Path(__file__).resolve().parents[1]

# Add the root directory to sys.path so "import src" works
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))