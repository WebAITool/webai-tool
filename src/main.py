from pathlib import Path

from dev_env import prepare_dev_env, DevEnvConfig
from lg_agent import create_agent
from lg_agent import get_initial_state
from makesrs_prod import makesrs
from prompts import planner
import re
from gener import generate
from logs import LOG_FILE
from llm_config import API_KEY
import argparse
import logging


def makeplan(srs):
    return generate(planner.format(doc=srs))


def count_phases(text):
    return len(re.findall(r'\[PHASE\s+\d+\]', text))


if __name__ == '__main__':
    logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG)

    argparse = argparse.ArgumentParser()

    argparse.add_argument("--prjdir", help='Directory for project generating',
                          required=True)

    group = argparse.add_mutually_exclusive_group(required=True)
    group.add_argument("--docpath", help='Path to documentation file')
    group.add_argument("--refprjpath", help='Directory with reference project')

    argparse.add_argument("--enable-commits", help='Enable commits from tool',
                          action='store_true')
    argparse.add_argument("--commit-branch", help='Branch for tool commiting. Default is "dev"',
                          default='dev')
    # old goal is f'implement project by specification, work in {PRJ_DIR} we
    # are on windows'
    argparse.add_argument("taskspec", help='Path to task specification')

    args = argparse.parse_args()

    if not API_KEY:
        raise SystemExit(
            "API_KEY is required. Set it in the environment or in a local .env file.")

    PRJ_DIR = Path(args.prjdir)

    READ_DOC_FROM_FILE = args.docpath is not None
    docpath: str
    if READ_DOC_FROM_FILE:
        docpath = str(Path(args.docpath))
        refprjpath = None
    else:
        docpath = str((PRJ_DIR / "generated_doc.txt").absolute())
        refprjpath = Path(args.refprjpath)

    if not READ_DOC_FROM_FILE:
        logging.info('making doc...')
        doc = makesrs(str(refprjpath))
        if doc is None:
            raise RuntimeError("doc is None!")
        print('doc created')
        with open(docpath, 'w+', encoding='utf-8') as docfile:
            docfile.write(doc)
            print('doc writed')
    else:
        with open(docpath, 'r', encoding='utf-8') as docfile:
            doc = docfile.read()
            print('doc readed')

    prepare_dev_env(
        DevEnvConfig(
            PRJ_DIR,
            args.commit_branch,
            args.enable_commits))

    taskspec: str
    with open(args.taskspec, 'r') as file:
        taskspec = file.read()

    config = {"recursion_limit": 250}
    impl_state = get_initial_state(
        goal=taskspec,
        spec=doc,
        prjdir=str(PRJ_DIR),
        max_steps=50,
        action_memory_size=10)
    agent = create_agent(args.enable_commits)
    agent.invoke(impl_state, config=config)

    # tester_state = get_initial_state(
    #     goal=f'make sure project in {PRJ_DIR} starts and works correctly on windows',
    #     spec=doc, max_steps=50, action_memory_size=10)
    # agent.invoke(tester_state, config=config)
