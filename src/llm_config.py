import os
from dataclasses import dataclass

try:
    import dotenv
except ImportError:  # pragma: no cover - exercised only in minimal envs
    dotenv = None


DEFAULT_API_BASE_URL = "https://api.polza.ai/api/v1"
DEFAULT_LLM_MODEL = "z-ai/glm-5.1"
DEFAULT_FRONTEND_VISION_MODEL = "qwen/qwen3-vl-8b-thinking"


@dataclass(frozen=True)
class LLMConfig:
    api_key: str | None
    api_base_url: str
    model: str
    frontend_vision_model: str


def load_llm_config() -> LLMConfig:
    if dotenv is not None:
        dotenv.load_dotenv()
    return LLMConfig(
        api_key=os.getenv("API_KEY"),
        api_base_url=os.getenv("LLM_API_BASE_URL", DEFAULT_API_BASE_URL),
        model=os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL),
        frontend_vision_model=os.getenv(
            "FRONTEND_VISION_MODEL",
            DEFAULT_FRONTEND_VISION_MODEL,
        ),
    )


def validate_llm_config(config: LLMConfig) -> None:
    if not config.api_key:
        raise SystemExit(
            "API_KEY is required. Set it in the environment or in a local .env file."
        )


_CONFIG = load_llm_config()

API_KEY = _CONFIG.api_key
LLM_API_BASE_URL = _CONFIG.api_base_url
LLM_MODEL = _CONFIG.model
FRONTEND_VISION_MODEL = _CONFIG.frontend_vision_model
