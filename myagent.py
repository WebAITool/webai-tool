# from gener import model
from gener import generate as model
from tools import *
from typing import Callable
import sys
from io import StringIO

def remove_first_last(text: str) -> str:
    lines = text.splitlines()
    if len(lines) <= 2:
        return ""
    return "\n".join(lines[1:-1])

def print_no_std_out(s, stdout, non_std_out):
    sys.stdout = stdout
    print(s)
    sys.stdout = non_std_out

class Agent():
    def __init__(self, model: Callable):
        self.model = model
        self.instr = "\nyour action should be nothing except single python code block, one of the steps to complete the task (like file or folder creation or writing content into file or execution of commands), your answer will be executed immediately as code, you will see all console output of your code\n"
        self.resins = "\nresult of code execution:\n"
        self.actionlist = []

    def format_actionlist(self):
        name = '\nthis is list of your actions and observations before this moment:'
        look = '\nlook at last action and make what you planned before\n'
        acts_formatted = ''
        for i, action in enumerate(self.actionlist):
            acts_formatted += f'\nACTION {i}:\n'
            acts_formatted += action
        if acts_formatted == '':
            return '\nyou have not done any actions yet\n'
        return name + acts_formatted + look

    def run(self, prompt, itercnt: int):
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        prevres = ''
        try:
            for i in range(itercnt):
                reason_prompt = prompt
                code_prompt = prompt + self.instr + self.format_actionlist()
                print_no_std_out(f'code prompt:\n{code_prompt}', old_stdout, captured_output)
                
                code = self.model(code_prompt)
                
                
                if "```" in code:
                    code = remove_first_last(code)
                # print_no_std_out(f'agent code to be executed:\n{code}', old_stdout, captured_output)
                try:
                    exec(code, globals())
                    prevres = captured_output.getvalue()
                except Exception as e:
                    prevres = 'error! Unable to execute code.' + str(e)
                # print_no_std_out(f'console output:\n{prevres}', old_stdout, captured_output)
                
                reas = f'your last action was: [{code}]\nend of your last action. This is output of your last action: [{prevres}] \nend of output. Think about it, describe what you have done and what are you planning to do next to achieve the goal. Be concise. Do not write any code, only plan and recap'
                compl = '\nif you completed all your plans, you need to say "[I_AM_SURE_THAT_GOAL_IS_ACHIEVED]" tag instead of thoughts and plans. But before this double check that all files really exists and all works as expected.\n'
                think = reason_prompt + self.format_actionlist() + reas + compl
                # print_no_std_out(f'think prompt:\n{think}', old_stdout, captured_output)
                
                while True:
                    thought = self.model(think)
                    print_no_std_out(f'thought is {thought}', old_stdout, captured_output)
                    if thought == '':
                        think += '\nbtw, your last thought was empty. Try again.\n'
                        continue
                    break

                if '[I_AM_SURE_THAT_GOAL_IS_ACHIEVED]' in thought:
                    print_no_std_out('ATTEMPT TO COMPLETE THE TASK', old_stdout, captured_output)
                    complq = '\nyou says that you have completed the task. Are you sure? Have you checked that it works as it should? You can answer [YES] tag to complete development or [NO] tag if you want to check or test something. If your answer is [YES], you will never be able to do edit this project, so choose carefully.\n'
                    answer = self.model(self.format_actionlist() + complq)
                    print_no_std_out(f'ANSWER IS {answer}', old_stdout, captured_output)
                    
                    if '[YES]' in answer:
                        print_no_std_out('TASK IS COMPLETED', old_stdout, captured_output)
                        break
                
                self.actionlist.append(thought)

        finally:
            sys.stdout = old_stdout
        

agentize = "you are code agent. You can interact with environment using python code snippets\n" \
"solve this task step by step [{task}] end of the task."
prompt = "make a nice betting web application. Work in betting_app dir"

agent = Agent(model=model)
result = agent.run(agentize.format(task=prompt), itercnt=80)