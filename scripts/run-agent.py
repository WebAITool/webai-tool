import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from lg_agent import run_agent
if len(sys.argv) < 3:
    print('usage: run-agent <goal> <spec> [prjdir]')
    sys.exit(1)
goal = sys.argv[1]
spec = sys.argv[2]
prjdir = sys.argv[3] if len(sys.argv) > 3 else '.'
run_agent(goal, spec, prjdir=prjdir)
