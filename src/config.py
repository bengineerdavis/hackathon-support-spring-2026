import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SENTRY_AUTH_TOKEN = os.environ["SENTRY_AUTH_TOKEN"]
SENTRY_ORG_SLUG = os.environ["SENTRY_ORG_SLUG"]
SENTRY_PROJECT_SLUG = os.environ["SENTRY_PROJECT_SLUG"]
SENTRY_DSN = os.environ["SENTRY_DSN"]
SENTRY_BASE_URL = os.getenv("SENTRY_BASE_URL", "https://sentry.io")

LLM_MODEL = os.getenv("LLM_MODEL", "ollama/llama3")


DATA_DIR = Path(__file__).parent.parent / "data" / "events"
DATA_DIR.mkdir(parents=True, exist_ok=True)
