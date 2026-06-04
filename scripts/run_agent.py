"""Run the agent with a goal and spec."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

if __name__ == "__main__":
    from lg_agent import run_agent

    if len(sys.argv) < 3:
        print("usage: run_agent.py <goal> <spec> [prjdir]")
        sys.exit(1)

    goal = sys.argv[1]
    spec = sys.argv[2]
    prjdir = sys.argv[3] if len(sys.argv) > 3 else "."
    run_agent(goal, spec, prjdir=prjdir)
