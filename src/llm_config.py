import os

import dotenv

dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "https://api.polza.ai/api/v1")

LLM_MODEL = os.getenv("LLM_MODEL", "z-ai/glm-5.1")
FRONTEND_VISION_MODEL = os.getenv(
    "FRONTEND_VISION_MODEL",
    "qwen/qwen3-vl-8b-thinking",
)
