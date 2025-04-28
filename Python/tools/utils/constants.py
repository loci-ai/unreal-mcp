from pathlib import Path

PARENT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = PARENT_DIR / "data"

HEIGHTMAP_PATH = DATA_DIR / "heightmap.r16"
