import os
from dataclasses import dataclass

try:
    import dotenv
except ImportError:  # pragma: no cover - exercised only in minimal envs
    dotenv = None


@dataclass(frozen=True)
class LLMConfig:
    api_key: str | None
    api_base_url: str | None
    model: str | None
    frontend_vision_model: str | None


def load_llm_config() -> LLMConfig:
    if dotenv is not None:
        dotenv.load_dotenv()
    return LLMConfig(
        api_key=os.getenv("API_KEY"),
        api_base_url=os.getenv("LLM_API_BASE_URL"),
        model=os.getenv("LLM_MODEL"),
        frontend_vision_model=os.getenv("FRONTEND_VISION_MODEL"),
    )


def validate_llm_config(config: LLMConfig) -> None:
    missing = []
    if not config.api_key:
        missing.append("API_KEY")
    if not config.api_base_url:
        missing.append("LLM_API_BASE_URL")
    if not config.model:
        missing.append("LLM_MODEL")
    if not config.frontend_vision_model:
        missing.append("FRONTEND_VISION_MODEL")

    if missing:
        raise SystemExit(
            "Missing required OpenAI-compatible provider configuration: "
            + ", ".join(missing)
            + ". Set them in the environment or in a local .env file."
        )
