import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DATA_GO_KR_API_KEY = os.getenv("DATA_GO_KR_API_KEY", "")
