from makesrs_prod import makesrs, make_tree
from lg_agent import agent
from lg_agent import get_initial_state
from prompts import *
import re
from gener import generate


def makeplan(srs):
    return generate(planner.format(doc=srs))

PRJPATH = 'I:/NSU/WebAI/2xbet' 

READ_DOC_FROM_FILE = True
PRJ_DIR = 'I:/NSU/WebAI/4xbet'

docpath = 'I:/NSU/WebAI/webai_toolkit/eng_d.txt'


def count_phases(text):
    return len(re.findall(r'\[PHASE\s+\d+\]', text))


if not READ_DOC_FROM_FILE:
    print('making doc...')
    doc = makesrs(PRJPATH)
    print('doc created')
    with open(docpath, 'w', encoding='utf-8') as docfile:
        docfile.write(doc)
        print('doc writed')
else:
    with open(docpath, 'r', encoding='utf-8') as docfile:
        doc = docfile.read()
        print('doc readed')

config = {"recursion_limit": 250}
impl_state = get_initial_state( 
    goal=f'implement project by specification, work in {PRJ_DIR} we are on windows',
    spec=doc, prjdir=PRJ_DIR, max_steps=50, action_memory_size=10)
agent.invoke(impl_state, config=config)

# tester_state = get_initial_state(
#     goal=f'make sure project in {PRJ_DIR} starts and works correctly on windows',
#     spec=doc, max_steps=50, action_memory_size=10)
# agent.invoke(tester_state, config=config)
