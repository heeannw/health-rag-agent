import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DATA_GO_KR_API_KEY = os.getenv("DATA_GO_KR_API_KEY", "")
KDCA_HEALTH_API_KEY = os.getenv("KDCA_HEALTH_API_KEY", "")
