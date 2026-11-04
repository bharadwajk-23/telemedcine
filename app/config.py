"""App configuration loaded from environment variables."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_API_KEY: str = os.getenv("TWILIO_API_KEY", "")
    TWILIO_API_SECRET: str = os.getenv("TWILIO_API_SECRET", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_TWIML_APP_SID: str = os.getenv("TWILIO_TWIML_APP_SID", "")
    TWILIO_CALLER_ID: str = os.getenv("TWILIO_CALLER_ID", "")

    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")

    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    DATA_FILE: str = os.getenv("DATA_FILE", "data/data.json")


settings = Settings()
