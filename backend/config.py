import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-only-key-change-before-deployment"
    )

    SQLALCHEMY_DATABASE_URI = "sqlite:///paypilot.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com"
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
