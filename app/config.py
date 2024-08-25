import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    COMPANY_ID: str = os.getenv("COMPANY_ID", "")

    # Base domain for the Morseverse API
    MORSEVERSE_BASE_URL: str = os.getenv("MORSEVERSE_BASE_URL", "https://morseverse.com/api/v1")

    # Specific API paths
    MORSEVERSE_TEXT_API_PATH: str = "/textusermessage"
    MORSEVERSE_VOICE_API_PATH: str = "/usermessage"
    MORSEVERSE_VOICE_AI: str = "https://morseverse.com/ai_agent/text_to_audio/"

    # Construct full URLs
    TELEGRAM_API_URL: str = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    MORSEVERSE_TEXT_API_URL: str = f"{MORSEVERSE_BASE_URL}{MORSEVERSE_TEXT_API_PATH}"
    MORSEVERSE_VOICE_API_URL: str = f"{MORSEVERSE_BASE_URL}{MORSEVERSE_VOICE_API_PATH}"


config = Config()
