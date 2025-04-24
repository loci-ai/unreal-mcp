import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.resolve() / ".env")

LOCI_API_KEY = os.getenv("LOCI_API_KEY")
