import argparse
import logging
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
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
    parser.add_argument("taskspec", help="Path to task specification")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    from llm_config import load_llm_config, validate_llm_config

    llm_config = load_llm_config()
    validate_llm_config(llm_config)

    from dev_env import DevEnvConfig, prepare_dev_env
    from lg_agent import create_agent, get_initial_state
    from logs import LOG_FILE
    from makesrs_prod import makesrs

    logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG)

    prj_dir = Path(args.prjdir).absolute()

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
        print("doc created")
        with open(docpath, "w+", encoding="utf-8") as docfile:
            docfile.write(doc)
            print("doc writed")
    else:
        with open(docpath, "r", encoding="utf-8") as docfile:
            doc = docfile.read()
            print("doc readed")

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
    )
    agent = create_agent(args.enable_commits, llm_config=llm_config)
    agent.invoke(impl_state, config=agent_config)

    if args.enable_commits:
        from dev_env import git

        dirty_files = git.get_dirty_files()
        if dirty_files:
            git.commit(dirty_files, "Apply WebAI Tool changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
