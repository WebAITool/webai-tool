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
    streaming: bool = True
    stream_fallback_to_non_stream: bool = True
    max_retries: int = 1
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float | None = None
    write_timeout_seconds: float = 30.0
    pool_timeout_seconds: float = 30.0


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_optional_float(name: str, default: float | None) -> float | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    if parsed <= 0:
        return None
    return parsed


def load_llm_config() -> LLMConfig:
    if dotenv is not None:
        dotenv.load_dotenv()
    return LLMConfig(
        api_key=os.getenv("API_KEY"),
        api_base_url=os.getenv("LLM_API_BASE_URL"),
        model=os.getenv("LLM_MODEL"),
        frontend_vision_model=os.getenv("FRONTEND_VISION_MODEL"),
        streaming=_get_bool("LLM_STREAMING", True),
        stream_fallback_to_non_stream=_get_bool(
            "LLM_STREAM_FALLBACK_TO_NON_STREAM",
            True,
        ),
        max_retries=_get_int("LLM_MAX_RETRIES", 1),
        connect_timeout_seconds=_get_float("LLM_CONNECT_TIMEOUT_SECONDS", 10.0),
        read_timeout_seconds=_get_optional_float("LLM_READ_TIMEOUT_SECONDS", None),
        write_timeout_seconds=_get_float("LLM_WRITE_TIMEOUT_SECONDS", 30.0),
        pool_timeout_seconds=_get_float("LLM_POOL_TIMEOUT_SECONDS", 30.0),
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
