import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="smolagents")
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

import argparse
import logging
from pathlib import Path
from dev_env import prepare_dev_env, DevEnvConfig
from makesrs_prod import makesrs
from lg_agent import create_agent, get_initial_state
from logs import LOG_FILE

if __name__ == '__main__':
    logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument("--prjdir", help='Directory for project generating', required=True)
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--docpath", help='Path to documentation file')
    group.add_argument("--refprjpath", help='Directory with reference project')
    
    parser.add_argument("--enable-commits", help='Enable commits from tool (Not heavily used in this version)', action='store_true')
    parser.add_argument("--commit-branch", help='Branch for tool commiting. Default is "dev"', default='dev')
    parser.add_argument("taskspec", help='Path to task specification')

    args = parser.parse_args()

    PRJ_DIR = Path(args.prjdir).absolute()

    # Разбираемся со спецификацией/документацией проекта
    READ_DOC_FROM_FILE = args.docpath is not None
    if READ_DOC_FROM_FILE:
        docpath = str(Path(args.docpath).absolute())
        refprjpath = None
    else:
        docpath = str(PRJ_DIR / "generated_doc.txt")
        refprjpath = Path(args.refprjpath)

    if not READ_DOC_FROM_FILE:
        logging.info('Making doc...')
        print('Making doc from reference project...')
        doc = makesrs(str(refprjpath))
        if doc is None:
            raise RuntimeError("Doc generation returned None!")
        with open(docpath, 'w+', encoding='utf-8') as docfile:
            docfile.write(doc)
        print('Doc created and written.')
    else:
        with open(docpath, 'r', encoding='utf-8') as docfile:
            doc = docfile.read()
        print('Doc loaded from file.')

    # Подготовка рабочего окружения
    prepare_dev_env(
        DevEnvConfig(
            PRJ_DIR,
            args.commit_branch,
            args.enable_commits
        )
    )

    # Загружаем конкретную задачу
    with open(args.taskspec, 'r', encoding='utf-8') as file:
        taskspec = file.read()

    # Формируем итоговую цель: Спецификация + Текущая задача
    combined_goal = (
        "PROJECT SPECIFICATION:\n"
        f"{doc}\n\n"
        "CURRENT TASK:\n"
        f"{taskspec}"
    )

    # Инициализируем граф
    config = {"recursion_limit": 250}
    impl_state = get_initial_state(
        goal=combined_goal,
        prjdir=str(PRJ_DIR),
        max_steps=50
    )
    
    agent = create_agent()
    
    print("\nStarting the Agentic Loop...\n")
    agent.invoke(impl_state, config=config)
    print("\nAgentic Loop finished.")