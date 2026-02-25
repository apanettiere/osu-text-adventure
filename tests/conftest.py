import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

# Put src/ first so "import engine..." works in tests
sys.path.insert(0, str(SRC_DIR))

# Also keep project root available if needed
sys.path.insert(0, str(PROJECT_ROOT))