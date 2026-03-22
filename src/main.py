from pathlib import Path
from dev_env import prepare_dev_env
from makesrs_prod import makesrs, make_tree
from lg_agent import agent
from lg_agent import get_initial_state
from prompts import *
import re
from gener import generate
from logs import LOG_FILE
import argparse
import logging


def makeplan(srs):
    return generate(planner.format(doc=srs))

def count_phases(text):
    return len(re.findall(r'\[PHASE\s+\d+\]', text))

if __name__ == '__main__':
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

    argparse = argparse.ArgumentParser()

    argparse.add_argument("--prjdir",  help='Directory for project generating', 
                          required=True)
    argparse.add_argument("--docpath", help='Path to documentation file')
    argparse.add_argument("--prjpath", help='Directory with reference project', 
                          required=True)

    args = argparse.parse_args()
    
    PRJPATH = Path(args.prjpath)
    PRJ_DIR = Path(args.prjdir)

    
    READ_DOC_FROM_FILE = args.docpath is not None
    docpath: str 
    if READ_DOC_FROM_FILE:
        docpath = str(Path(args.docpath))
    else:
        docpath = str((PRJ_DIR / "generated_doc.txt").absolute())


    if not READ_DOC_FROM_FILE:
        logging.info('making doc...')
        doc = makesrs(str(PRJPATH))
        if doc is None:
            raise RuntimeError("doc is None!")
        logging.info('doc created')
        with open(docpath, 'w+', encoding='utf-8') as docfile:
            docfile.write(doc)
            logging.info('doc writed')
    else:
        with open(docpath, 'r', encoding='utf-8') as docfile:
            doc = docfile.read()
            logging.info('doc readed')

    prepare_dev_env(Path(PRJ_DIR))

    config = {"recursion_limit": 250}
    impl_state = get_initial_state( 
        goal=f'implement project by specification, work in {PRJ_DIR} we are on windows',
        spec=doc, prjdir=str(PRJ_DIR), max_steps=50, action_memory_size=10)
    agent.invoke(impl_state, config=config)

    # tester_state = get_initial_state(
    #     goal=f'make sure project in {PRJ_DIR} starts and works correctly on windows',
    #     spec=doc, max_steps=50, action_memory_size=10)
    # agent.invoke(tester_state, config=config)
