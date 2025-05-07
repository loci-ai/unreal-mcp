from pathlib import Path

PARENT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = PARENT_DIR / "Data"
DATA_DIR.mkdir(exist_ok=True)

HEIGHTMAP_PATH = DATA_DIR / "heightmap.r16"
