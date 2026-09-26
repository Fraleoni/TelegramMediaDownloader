import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

API_ID_STR = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
SESSION_NAME = os.getenv("TG_SESSION_NAME", "session_downloader")
DEFAULT_DOWNLOAD_PATH = os.getenv("DEFAULT_DOWNLOAD_PATH", "./downloads")

try:
    API_ID = int(API_ID_STR) if API_ID_STR else None
except ValueError:
    API_ID = None


def validate_credentials():
    """Checks if API_ID and API_HASH are configured."""
    if not API_ID or not API_HASH:
        raise ValueError(
            "Configurazione mancante: imposta TG_API_ID e TG_API_HASH nel file .env "
            "o come variabili d'ambiente. Puoi ottenerli da https://my.telegram.org"
        )
