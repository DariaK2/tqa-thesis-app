"""
Application configuration and constants.
Loads environment variables and defines shared settings.
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Yandex Cloud LLM Configuration
YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_CLOUD_FOLDER", "")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
YANDEX_CLOUD_MODEL = os.getenv("YANDEX_CLOUD_MODEL", "deepseek-v32/latest")

# Flask Configuration
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
FLASK_PORT = int(os.getenv("FLASK_PORT", "5001"))

# Analysis Configuration
CHUNK_SIZE_CHARS = int(os.getenv("CHUNK_SIZE_CHARS", "6000"))
CHUNK_OVERLAP_CHARS = int(os.getenv("CHUNK_OVERLAP_CHARS", "500"))
AUTO_INSTALL_OCR_DEPS = os.getenv("AUTO_INSTALL_OCR_DEPS", "false").lower() == "true"

# Analysis Constants
MIN_EXTRACTED_TEXT_LENGTH = 20
VALID_ANALYSIS_MODES = {"overview", "detail", "research", "all"}
VALID_PROMPT_VERSIONS = {"MASTER", "A", "B", "C", "D"}
PARAMETERS = ["cultural", "emotional", "pragmatic", "stylistic", "semantic"]

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
