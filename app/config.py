import os
from dotenv import load_dotenv

load_dotenv()

JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
EMAIL = os.getenv("EMAIL") or os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("API_TOKEN") or os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = os.getenv("PROJECT_KEY")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", 50))
CUSTOM_FIELD_ID = os.getenv("CUSTOM_FIELD_ID")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")


def require_settings(*settings):

    missing_settings = []

    for name in settings:

        if not globals().get(name):

            missing_settings.append(name)

    if missing_settings:

        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing_settings)
        )
