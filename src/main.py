import argparse
import logging
import os
import warnings
from pathlib import Path

from rich.console import Console
from rich.panel import Panel


warnings.filterwarnings("ignore", category=FutureWarning, module="smolagents")
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

console = Console()
CODE_EXECUTORS = {"host", "docker"}
DEFAULT_CODE_EXECUTOR_TIMEOUT_SECONDS = 600
DEFAULT_CODE_EXECUTOR_OUTPUT_LIMIT_BYTES = 4 * 1024 * 1024
DEFAULT_CODE_EXECUTOR_MEMORY = "4g"
DEFAULT_CODE_EXECUTOR_CPUS = "4"
DEFAULT_CODE_EXECUTOR_PIDS_LIMIT = 512


def load_cli_env(env_file: str | None = None) -> None:
    from llm_config import load_env_files

    load_env_files(env_file)


class WebAIArgumentParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args, namespace)
        if parsed.env_file is not None:
            env_path = Path(parsed.env_file)
            if not env_path.is_file():
                self.error(f"--env-file path does not exist: {parsed.env_file}")
            load_cli_env(str(env_path))
        else:
            load_cli_env()
        apply_env_defaults(parsed)
        validate_cli_args(parsed, self)
        return parsed


def apply_env_defaults(args: argparse.Namespace) -> None:
    if args.code_executor is None:
        args.code_executor = os.getenv("CODE_EXECUTOR", "host")
    if args.code_executor_image is None:
        args.code_executor_image = os.getenv("CODE_EXECUTOR_IMAGE")
    if args.code_executor_network is None:
        args.code_executor_network = os.getenv("CODE_EXECUTOR_DOCKER_NETWORK", "none")
    if args.code_executor_timeout_seconds is None:
        args.code_executor_timeout_seconds = os.getenv(
            "CODE_EXECUTOR_TIMEOUT_SECONDS",
            str(DEFAULT_CODE_EXECUTOR_TIMEOUT_SECONDS),
        )
    if args.code_executor_output_limit_bytes is None:
        args.code_executor_output_limit_bytes = os.getenv(
            "CODE_EXECUTOR_OUTPUT_LIMIT_BYTES",
            str(DEFAULT_CODE_EXECUTOR_OUTPUT_LIMIT_BYTES),
        )
    if args.code_executor_memory is None:
        args.code_executor_memory = os.getenv(
            "CODE_EXECUTOR_MEMORY",
            DEFAULT_CODE_EXECUTOR_MEMORY,
        )
    if args.code_executor_cpus is None:
        args.code_executor_cpus = os.getenv("CODE_EXECUTOR_CPUS", DEFAULT_CODE_EXECUTOR_CPUS)
    if args.code_executor_pids_limit is None:
        args.code_executor_pids_limit = os.getenv(
            "CODE_EXECUTOR_PIDS_LIMIT",
            str(DEFAULT_CODE_EXECUTOR_PIDS_LIMIT),
        )


def validate_cli_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.code_executor not in CODE_EXECUTORS:
        parser.error(
            "CODE_EXECUTOR/--code-executor must be one of: "
            + ", ".join(sorted(CODE_EXECUTORS))
        )
    args.code_executor_timeout_seconds = parse_positive_int(
        args.code_executor_timeout_seconds,
        "CODE_EXECUTOR_TIMEOUT_SECONDS/--code-executor-timeout-seconds",
        parser,
    )
    args.code_executor_output_limit_bytes = parse_positive_int(
        args.code_executor_output_limit_bytes,
        "CODE_EXECUTOR_OUTPUT_LIMIT_BYTES/--code-executor-output-limit-bytes",
        parser,
    )
    args.code_executor_pids_limit = parse_positive_int(
        args.code_executor_pids_limit,
        "CODE_EXECUTOR_PIDS_LIMIT/--code-executor-pids-limit",
        parser,
    )
    if args.code_executor == "docker" and not args.code_executor_image:
        parser.error(
            "--code-executor-image or CODE_EXECUTOR_IMAGE is required when "
            "--code-executor=docker"
        )


def parse_positive_int(
    value: int | str,
    name: str,
    parser: argparse.ArgumentParser,
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parser.error(f"{name} must be a positive integer")
    if parsed <= 0:
        parser.error(f"{name} must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = WebAIArgumentParser()
    parser.add_argument(
        "--env-file",
        help="Optional env file to load before resolving environment-backed defaults.",
    )
    parser.add_argument(
        "--prjdir",
        help="Directory for project generating",
        required=True,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--docpath", help="Path to documentation file")
    group.add_argument("--refprjpath", help="Directory with reference project")

    parser.add_argument(
        "--enable-commits",
        help="Enable commits from tool",
        action="store_true",
    )
    parser.add_argument(
        "--commit-branch",
        help='Branch for tool commiting. Default is "dev"',
        default="dev",
    )
    parser.add_argument(
        "--interactive",
        help="Ask for user feedback after the agent confirms completion",
        action="store_true",
    )
    parser.add_argument(
        "--code-executor",
        default=None,
        help="Where generated Python scripts are executed. Default: host.",
    )
    parser.add_argument(
        "--code-executor-image",
        default=None,
        help="Docker image used when --code-executor=docker.",
    )
    parser.add_argument(
        "--code-executor-network",
        default=None,
        help="Docker network mode used when --code-executor=docker.",
    )
    parser.add_argument(
        "--code-executor-timeout-seconds",
        default=None,
        help="Maximum seconds a generated script may run. Default: 600.",
    )
    parser.add_argument(
        "--code-executor-output-limit-bytes",
        default=None,
        help="Maximum captured stdout/stderr bytes per stream. Default: 4194304.",
    )
    parser.add_argument(
        "--code-executor-memory",
        default=None,
        help="Docker memory limit for generated code. Default: 4g.",
    )
    parser.add_argument(
        "--code-executor-cpus",
        default=None,
        help="Docker CPU limit for generated code. Default: 4.",
    )
    parser.add_argument(
        "--code-executor-pids-limit",
        default=None,
        help="Docker pids limit for generated code. Default: 512.",
    )
    parser.add_argument("taskspec", help="Path to task specification")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupted by user.[/bold yellow]")
        return 130


def _main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    from llm_config import load_llm_config, validate_llm_config

    llm_config = load_llm_config(load_dotenv=False)
    validate_llm_config(llm_config)

    from dev_env import DevEnvConfig, prepare_dev_env
    from lg_agent import CodeExecutionConfig, create_agent, get_initial_state
    from logs import LOG_FILE
    from makesrs_prod import makesrs

    logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG)

    prj_dir = Path(args.prjdir).absolute()
    prj_dir.mkdir(parents=True, exist_ok=True)

    if args.docpath is not None:
        docpath = Path(args.docpath).absolute()
        refprjpath = None
    else:
        docpath = prj_dir / "generated_doc.txt"
        refprjpath = Path(args.refprjpath)

    if refprjpath is not None:
        logging.info("making doc...")
        doc = makesrs(str(refprjpath))
        if doc is None:
            raise RuntimeError("doc is None!")
        console.print(
            Panel(
                "Documentation generated from reference project.",
                title="[bold cyan]Input[/bold cyan]",
                border_style="cyan",
            )
        )
        with open(docpath, "w+", encoding="utf-8") as docfile:
            docfile.write(doc)
            console.print("[dim]Documentation written.[/dim]")
    else:
        with open(docpath, "r", encoding="utf-8") as docfile:
            doc = docfile.read()
            console.print(
                Panel(
                    "Documentation loaded.",
                    title="[bold cyan]Input[/bold cyan]",
                    border_style="cyan",
                )
            )

    prepare_dev_env(
        DevEnvConfig(
            prj_dir,
            args.commit_branch,
            args.enable_commits,
        )
    )

    with open(args.taskspec, "r", encoding="utf-8") as file:
        taskspec = file.read()

    agent_config = {"recursion_limit": 250}
    impl_state = get_initial_state(
        goal=taskspec,
        spec=doc,
        prjdir=str(prj_dir),
        max_steps=50,
        code_execution=CodeExecutionConfig(
            executor=args.code_executor,
            docker_image=args.code_executor_image or "",
            docker_network=args.code_executor_network,
            timeout_seconds=args.code_executor_timeout_seconds,
            output_limit_bytes=args.code_executor_output_limit_bytes,
            memory=args.code_executor_memory,
            cpus=args.code_executor_cpus,
            pids_limit=args.code_executor_pids_limit,
        ),
    )
    agent = create_agent(
        args.enable_commits,
        interactive=args.interactive,
        llm_config=llm_config,
    )
    agent.invoke(impl_state, config=agent_config)

    if args.enable_commits:
        from dev_env import git

        dirty_files = git.get_dirty_files()
        if dirty_files:
            git.commit(dirty_files, "Apply WebAI Tool changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
