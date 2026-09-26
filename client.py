from telethon import TelegramClient
from config import API_ID, API_HASH, SESSION_NAME, validate_credentials


def get_telegram_client(session_name: str = SESSION_NAME) -> TelegramClient:
    """Initializes and returns a TelegramClient instance."""
    validate_credentials()
    return TelegramClient(session_name, API_ID, API_HASH)
