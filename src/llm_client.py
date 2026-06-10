import json
import logging
import time
import gzip
from dataclasses import dataclass
from typing import Any

import httpx

from llm_config import LLMConfig


@dataclass(frozen=True)
class ChatResponse:
    content: str


class LLMTransportError(RuntimeError):
    pass


class OpenAICompatibleChatClient:
    def __init__(self, config: LLMConfig, temperature: float = 0.3):
        self.config = config
        self.temperature = temperature
        self.timeout = httpx.Timeout(
            timeout=config.read_timeout_seconds,
            connect=config.connect_timeout_seconds,
            read=config.read_timeout_seconds,
            write=config.write_timeout_seconds,
            pool=config.pool_timeout_seconds,
        )

    def invoke(self, messages: list[Any]) -> ChatResponse:
        last_error: Exception | None = None
        attempts = max(self.config.max_retries, 0) + 1
        for attempt in range(1, attempts + 1):
            try:
                if self.config.streaming:
                    content = self._invoke_stream(messages, attempt)
                else:
                    content = self._invoke_non_stream(messages, attempt)
                return ChatResponse(content=content)
            except (httpx.HTTPError, LLMTransportError) as exc:
                last_error = exc
                logging.warning(
                    "LLM transport attempt %s/%s failed: %s: %s",
                    attempt,
                    attempts,
                    type(exc).__name__,
                    exc,
                )
                if attempt >= attempts:
                    break
        if self.config.streaming and self.config.stream_fallback_to_non_stream:
            logging.warning(
                "LLM streaming failed after %s attempts; trying bounded non-stream fallback",
                attempts,
            )
            try:
                return ChatResponse(self._invoke_non_stream(messages, 1))
            except (httpx.HTTPError, LLMTransportError) as exc:
                last_error = exc
                logging.warning(
                    "LLM non-stream fallback failed: %s: %s",
                    type(exc).__name__,
                    exc,
                )
        raise LLMTransportError(
            f"LLM transport failed after {attempts} attempts: {last_error}"
        )

    def _invoke_non_stream(self, messages: list[Any], attempt: int) -> str:
        started_at = time.monotonic()
        payload = self._payload(messages, stream=False)
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream(
                "POST",
                self._chat_completions_url(),
                headers=self._headers(streaming=False),
                json=payload,
            ) as response:
                response.raise_for_status()
                header_at = time.monotonic()
                raw_body = bytearray()
                for chunk in response.iter_raw():
                    now = time.monotonic()
                    if (
                        self.config.read_timeout_seconds is not None
                        and now - header_at > self.config.read_timeout_seconds
                    ):
                        raise LLMTransportError(
                            "non-stream response body did not complete within "
                            f"{self.config.read_timeout_seconds:.1f}s"
                        )
                    raw_body.extend(chunk)
                elapsed = time.monotonic() - started_at
                logging.debug(
                    "LLM transport attempt=%s stream=false status=%s total_seconds=%.3f",
                    attempt,
                    response.status_code,
                    elapsed,
                )
                data = _load_json(
                    _decode_response_body(response, bytes(raw_body)),
                    "non-stream response body",
                )
        return _extract_message_content(data)

    def _invoke_stream(self, messages: list[Any], attempt: int) -> str:
        started_at = time.monotonic()
        payload = self._payload(messages, stream=True)
        content_parts: list[str] = []
        first_content_at: float | None = None
        last_content_at = started_at
        status_code: int | None = None

        with httpx.Client(timeout=self.timeout) as client:
            with client.stream(
                "POST",
                self._chat_completions_url(),
                headers=self._headers(streaming=True),
                json=payload,
            ) as response:
                status_code = response.status_code
                response.raise_for_status()
                for line in response.iter_lines():
                    now = time.monotonic()
                    if (
                        self.config.read_timeout_seconds is not None
                        and now - last_content_at > self.config.read_timeout_seconds
                    ):
                        raise LLMTransportError(
                            "stream produced no content chunks for "
                            f"{self.config.read_timeout_seconds:.1f}s"
                        )
                    if not line:
                        continue
                    if line.startswith(":"):
                        continue
                    if not line.startswith("data:"):
                        continue
                    data_text = line.removeprefix("data:").strip()
                    if data_text == "[DONE]":
                        break
                    chunk = _load_json(data_text, "stream response chunk")
                    delta = _extract_delta_content(chunk)
                    if not delta:
                        continue
                    if first_content_at is None:
                        first_content_at = now
                    last_content_at = now
                    content_parts.append(delta)

        elapsed = time.monotonic() - started_at
        first_content_seconds = (
            None if first_content_at is None else first_content_at - started_at
        )
        logging.debug(
            (
                "LLM transport attempt=%s stream=true status=%s "
                "first_content_seconds=%s total_seconds=%.3f"
            ),
            attempt,
            status_code,
            (
                "-"
                if first_content_seconds is None
                else f"{first_content_seconds:.3f}"
            ),
            elapsed,
        )
        if not content_parts:
            raise LLMTransportError("stream completed without content chunks")
        return "".join(content_parts)

    def _payload(self, messages: list[Any], stream: bool) -> dict[str, Any]:
        return {
            "model": self.config.model,
            "temperature": self.temperature,
            "stream": stream,
            "messages": [_message_to_dict(message) for message in messages],
        }

    def _headers(self, streaming: bool) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if streaming else "application/json",
        }

    def _chat_completions_url(self) -> str:
        return f"{self.config.api_base_url.rstrip('/')}/chat/completions"


def _message_to_dict(message: Any) -> dict[str, str]:
    content = str(getattr(message, "content", ""))
    message_type = getattr(message, "type", "")
    class_name = type(message).__name__.lower()
    if message_type == "system" or "system" in class_name:
        role = "system"
    else:
        role = "user"
    return {"role": role, "content": content}


def _extract_message_content(data: dict[str, Any]) -> str:
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMTransportError(f"Unexpected non-stream response shape: {data}") from exc


def _extract_delta_content(data: dict[str, Any]) -> str:
    try:
        return str(data["choices"][0].get("delta", {}).get("content") or "")
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMTransportError(f"Unexpected stream response shape: {data}") from exc


def _decode_response_body(response: httpx.Response, body: bytes) -> str:
    if response.headers.get("content-encoding", "").lower() == "gzip" and body:
        try:
            body = gzip.decompress(body)
        except OSError as exc:
            raise LLMTransportError("Could not decode gzip response body") from exc
    try:
        return body.decode(response.encoding or "utf-8")
    except UnicodeDecodeError as exc:
        raise LLMTransportError("Could not decode response body as text") from exc


def _load_json(text: str, context: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        preview = text[:500]
        raise LLMTransportError(
            f"Malformed JSON in {context}: {preview!r}"
        ) from exc
    if not isinstance(data, dict):
        raise LLMTransportError(f"Unexpected JSON value in {context}: {data!r}")
    return data
