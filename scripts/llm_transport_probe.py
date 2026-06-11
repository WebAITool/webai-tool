#!/usr/bin/env python3
"""Measure the production OpenAI-compatible LLM client transport path."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_client import LLMTransportError, OpenAICompatibleChatClient  # noqa: E402
from llm_config import (  # noqa: E402
    LLMConfig,
    load_env_files,
    load_llm_config,
    validate_llm_config,
)


DEFAULT_PROMPT = "Reply with exactly: pong"
EXPECTED_RESPONSE = "pong"


@dataclass(frozen=True)
class ProbeMessage:
    content: str
    type: str


@dataclass
class ProbeResult:
    run: int
    stream: bool
    ok: bool
    total_seconds: float
    content_chars: int
    expected: str
    content: str
    error: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", help="Optional .env file to load")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument(
        "--mode",
        choices=("non-stream", "stream", "both"),
        default="both",
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--prompt-file")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL"))
    parser.add_argument("--base-url", default=os.getenv("LLM_API_BASE_URL"))
    parser.add_argument("--api-key", default=os.getenv("API_KEY"))
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--expected", default=EXPECTED_RESPONSE)
    parser.add_argument("--output-jsonl")
    args = parser.parse_args()
    if args.env_file is not None and not Path(args.env_file).is_file():
        parser.error(f"--env-file path does not exist: {args.env_file}")
    return args


def build_config(args: argparse.Namespace, stream: bool) -> LLMConfig:
    config = load_llm_config(load_dotenv=False)
    config = replace(
        config,
        api_key=args.api_key or config.api_key,
        api_base_url=args.base_url or config.api_base_url,
        model=args.model or config.model,
        streaming=stream,
    )
    validate_llm_config(config)
    return config


def build_messages(args: argparse.Namespace) -> list[ProbeMessage]:
    prompt = args.prompt
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    return [
        ProbeMessage(
            type="system",
            content="You are a transport benchmark responder.",
        ),
        ProbeMessage(type="human", content=prompt),
    ]


def run_probe(args: argparse.Namespace, run_index: int, stream: bool) -> ProbeResult:
    started_at = time.monotonic()
    content = ""
    error = ""
    try:
        client = OpenAICompatibleChatClient(
            build_config(args, stream),
            temperature=args.temperature,
        )
        response = client.invoke(build_messages(args))
        content = response.content.strip()
        ok = content == args.expected
    except (LLMTransportError, SystemExit) as exc:
        ok = False
        error = f"{type(exc).__name__}: {exc}"
    total_seconds = time.monotonic() - started_at
    return ProbeResult(
        run=run_index,
        stream=stream,
        ok=ok,
        total_seconds=total_seconds,
        content_chars=len(content),
        expected=args.expected,
        content=content,
        error=error,
    )


def print_result(result: ProbeResult) -> None:
    mode = "stream" if result.stream else "non-stream"
    suffix = f" error={result.error}" if result.error else ""
    print(
        f"run={result.run} mode={mode} ok={result.ok} "
        f"total={result.total_seconds:.3f}s chars={result.content_chars}"
        f"{suffix}",
        flush=True,
    )


def main() -> int:
    args = parse_args()
    load_env_files(args.env_file)
    args.model = args.model or os.getenv("LLM_MODEL")
    args.base_url = args.base_url or os.getenv("LLM_API_BASE_URL")
    args.api_key = args.api_key or os.getenv("API_KEY")

    modes = [False, True] if args.mode == "both" else [args.mode == "stream"]
    output = None
    failures = 0
    if args.output_jsonl:
        output = Path(args.output_jsonl).open("w", encoding="utf-8")
    try:
        run_index = 1
        for _ in range(args.runs):
            for stream in modes:
                result = run_probe(args, run_index, stream)
                print_result(result)
                if not result.ok:
                    failures += 1
                if output is not None:
                    output.write(json.dumps(asdict(result), sort_keys=True) + "\n")
                    output.flush()
                run_index += 1
    finally:
        if output is not None:
            output.close()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
