import os
import dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import (
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    ChatPromptTemplate
)
from repo_map import get_repo_structure
from tools.context import get_symbol_context, get_symbol_graph  # noqa: F401
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.messages import ToolMessage
from langchain_core.output_parsers import StrOutputParser
from typing import TypedDict, List, Annotated
import operator
from langgraph.graph import StateGraph, END
from lg_tools import shell_exec
from langchain_experimental.utilities import PythonREPL
from langchain_core.runnables import RunnableLambda
from difflib import SequenceMatcher


dotenv.load_dotenv()
llm = ChatOpenAI(
    model_name=os.getenv("LLM_MODEL", "z-ai/glm-4.7"),
    base_url=os.getenv("LLM_BASE_URL", "https://api.polza.ai/api/v1"),
    temperature=0.5,
    api_key=os.getenv("LLM_API_KEY", os.getenv("API_KEY"))
)

class AgentState(TypedDict):
    goal: str
    actions: List[str]
    plan: str
    spec: str
    thoughts: List[str]
    knowledge: str
    iter_cnt: int
    max_steps: int
    patience: int
    action_memory_size: int
    decision: str
    wakeup: str
    prjdir: str
    tree: str
    prev_tree: str
    stale_count: int
    review_count: int

common_context = '''goal of the agent system is:\n{goal}\nend of the goal.\n
        it is list of your last actions:\n{actions}\n
        End of the action list.\n
        'it is list of your recaps and plans until this moment:\n{thoughts}\n'
        'End of the list.\n'
        '\nThis is the specification of the project that you are currently work on:\n'
        '{spec}'
        '\nend of specification\n'
        'current project file structure is:\n{tree}\n'
        '''



def think(state: AgentState):
    sysmsg = SystemMessagePromptTemplate.from_template(
        'you are thinking and planning agent of the agentic system')
    usermsg = HumanMessagePromptTemplate.from_template(
        common_context +
        'First, recap what you have done in one phrase. '
        'Then, check: does what you have done fully satisfy the goal and specification? '
        'Do not add features beyond what is explicitly asked. Do not "enhance" or "improve" working code. '
        'If YES — you MUST include the exact token [GOAL_ACHIEVED] in your response (with brackets). A separate reviewer agent will verify your work, so do NOT plan any verification yourself. '
        'If NO — plan the NEXT SINGLE step to get closer to the goal. '
        'Plan only things that can be done using python code snippets. Do not write any code, only plan. '
        'The implementator agent will not see the specification, so your plan should contain all necessary context. '
        'If task is to modify something, firstly check what exactly you need to modify. '
        '\n\nCRITICAL RULES:\n'
        '- After code executed without errors, assume it worked. Do NOT plan verification, re-reading, or checking of files — say [GOAL_ACHIEVED] instead.\n'
        '- Never go beyond the spec. If the spec says "add a button", add a button and say [GOAL_ACHIEVED]. Do not plan "real implementation" or "session handling" unless the spec asks for it.\n'
        '- ONLY use [NOT_ACHIEVED] if you previously said [GOAL_ACHIEVED] and the reviewer sent you back with feedback. Never use [NOT_ACHIEVED] when you have not yet said [GOAL_ACHIEVED].\n'
        '- If you have not started or are still working, just plan the next step — do not say [NOT_ACHIEVED] or [GOAL_ACHIEVED].\n\n'
        '{wakeup}')
    chat = ChatPromptTemplate.from_messages(([sysmsg, usermsg]))
    chain = (chat | llm | StrOutputParser())
    print('thinking...')
    plan = chain.invoke(state)
    print(plan)
    return {'plan': plan, 'thoughts': state['thoughts'] + [plan]}


def similarity(text_a: str, text_b: str) -> float:
    return SequenceMatcher(None, text_a, text_b).ratio()


_SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.next', 'dist', 'build'}
_SKIP_EXTS = {'.pyc', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.svg', '.lock'}
_MAX_FILE_SIZE = 10_000
_MAX_TOTAL_SIZE = 30_000


def _read_project_files(prjdir: str) -> str:
    """Walk prjdir and return concatenated contents of small text files."""
    parts = []
    total = 0
    for root, dirs, files in os.walk(prjdir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in sorted(files):
            ext = os.path.splitext(fname)[1].lower()
            if ext in _SKIP_EXTS:
                continue
            fpath = os.path.join(root, fname)
            try:
                size = os.path.getsize(fpath)
            except OSError:
                continue
            if size > _MAX_FILE_SIZE or size == 0:
                continue
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except OSError:
                continue
            rel = os.path.relpath(fpath, prjdir)
            chunk = f'=== {rel} ===\n{content}\n\n'
            if total + len(chunk) > _MAX_TOTAL_SIZE:
                break
            parts.append(chunk)
            total += len(chunk)
        if total >= _MAX_TOTAL_SIZE:
            break
    return ''.join(parts) if parts else '(no files found)'


def _extract_code_from_action(action: str) -> str | None:
    """Extract the code block from a successful action string.

    Returns None for failure actions (those containing 'code was not executed').
    """
    if 'code was not executed' in action:
        return None
    start_marker = 'executed code:\n'
    end_marker = '\nresult:\n'
    start = action.find(start_marker)
    end = action.find(end_marker)
    if start == -1 or end == -1:
        return None
    return action[start + len(start_marker):end]


def state_check(state: AgentState):
    retdict = {
        'iter_cnt': state['iter_cnt'] + 1,
        'decision': 'code_action',
        'wakeup': ''  # reset every iteration
    }

    if 'GOAL_ACHIEVED' in state['plan'] and 'NOT_ACHIEVED' not in state['plan']:
        retdict['decision'] = 'review'
    elif state['iter_cnt'] >= state['max_steps']:
        retdict['decision'] = END

    retdict['actions'] = state['actions'][-state['action_memory_size']:]

    # --- Update tree-staleness tracker (always, regardless of decision) ---
    current_tree = state['tree']
    if current_tree == state['prev_tree']:
        retdict['stale_count'] = state['stale_count'] + 1
    else:
        retdict['stale_count'] = 0
    retdict['prev_tree'] = current_tree

    # --- Action-based loop detection (only when heading to code_action) ---
    if retdict['decision'] == 'code_action':
        wakeup = ''
        actions = state['actions']

        # Check 1: Consecutive failures — last 2 actions both failed
        if len(actions) >= 2:
            if 'code was not executed' in actions[-1] and 'code was not executed' in actions[-2]:
                wakeup = (
                    '\n[LOOP DETECTED] Your last 2 code actions both failed completely. '
                    'The code agent cannot produce valid code for this approach. '
                    'You MUST choose a fundamentally different strategy — '
                    'different library, different file, or skip this step entirely.'
                )
                print('LOOP: 2 consecutive code failures')

        # Check 2: Stale filesystem — tree unchanged for 3+ iterations
        if not wakeup and retdict['stale_count'] >= 3:
            wakeup = (
                '\n[LOOP DETECTED] The project file tree has not changed for 3 iterations. '
                'Your code runs but produces no lasting changes. '
                'Check that you are writing to the correct paths and that files are actually being created or modified.'
            )
            print(f'LOOP: stale filesystem ({retdict["stale_count"]} iterations)')

        # Check 3: Repeated code — code blocks from last 2 actions are near-identical
        if not wakeup and len(actions) >= 2:
            code_a = _extract_code_from_action(actions[-1])
            code_b = _extract_code_from_action(actions[-2])
            if code_a is not None and code_b is not None:
                sim = similarity(code_a, code_b)
                print(f'CODE SIMILARITY: {sim:.3f}')
                print(f'  prev code: {code_b[:120]!r}...')
                print(f'  curr code: {code_a[:120]!r}...')
                if sim > 0.85:
                    # Both actions succeeded (code was extracted) — likely a verification loop
                    wakeup = (
                        '\n[LOOP DETECTED] Your last two code actions are nearly identical. '
                        'Repeating the same code will not produce a different result. '
                        'If the goal is already achieved, you MUST say [GOAL_ACHIEVED] now. '
                        'Otherwise, name a DIFFERENT tool, file, or method you have not tried yet.'
                    )
                    print('LOOP: repeated code (similarity > 0.85)')

        # Escalation: if wakeup was already set from previous iteration and a new loop is detected
        # → route to review so the reviewer can verify goal completion
        if wakeup:
            if state.get('wakeup'):
                print('LOOP PERSISTS AFTER WAKEUP — routing to review')
                retdict['decision'] = 'review'
            else:
                retdict['wakeup'] = wakeup
                retdict['decision'] = 'think'

    return retdict


def review(state: AgentState):
    """Review goal completion by reading actual project files."""
    review_count = state.get('review_count', 0)
    if review_count >= 3:
        print(f'review: accepting result after {review_count} failed reviews to avoid infinite loop')
        return {'decision': END}

    # Escape curly braces so LangChain templates don't treat file content as variables
    file_contents = _read_project_files(state['prjdir']).replace('{', '{{').replace('}', '}}')

    sysmsg = SystemMessagePromptTemplate.from_template(
        'you are a code reviewer agent. you verify whether implementations match their goals.')

    usermsg_text = (
        'Goal of the project:\n{goal}\nEnd of the goal.\n\n'
        'Specification:\n{spec}\nEnd of specification.\n\n'
        'Current project file structure:\n{tree}\n\n'
        'Actual file contents:\n' + file_contents + '\nEnd of file contents.\n\n'
        'Read the project files above and review the code.\n\n'
        'First, write your ANALYSIS. Check two things:\n'
        '1. Are the REQUIRED changes from the goal present in the files?\n'
        '2. Did the coder break or delete any EXISTING code that was there before?\n'
        'Do NOT write the words YES or NO anywhere in your analysis.\n\n'
        'Then, on the LAST line of your response, write your verdict in exactly this format:\n'
        'VERDICT: YES\n'
        'or\n'
        'VERDICT: NO\n\n'
        'Use VERDICT: YES if the required changes exist and existing code was not damaged. '
        'Use VERDICT: NO if something is missing, wrong, or if existing code was broken. '
        'Do not say VERDICT: NO just because you want more testing — focus on whether the required changes exist and nothing was broken.'
    )

    usermsg = HumanMessagePromptTemplate.from_template(usermsg_text)
    msglist = [sysmsg, usermsg]
    max_retries = 3
    for _ in range(max_retries):
        chat = ChatPromptTemplate.from_messages(msglist)
        chain = (chat | llm | StrOutputParser())
        answer = chain.invoke(state)
        print(f'reviewing... (Answer: {answer})')
        ans_upper = answer.upper()
        if 'VERDICT: YES' in ans_upper:
            return {'decision': END}
        elif 'VERDICT: NO' in ans_upper:
            return {
                'decision': 'think',
                'wakeup': f'\n[REVIEWER FEEDBACK] {answer}',
                'review_count': review_count + 1,
            }
        wrong_answer_msg = HumanMessagePromptTemplate.from_template(
            'Your response must end with VERDICT: YES or VERDICT: NO. Try again.')
        msglist.append(AIMessage(content=answer))
        msglist.append(wrong_answer_msg)
    # LLM failed to give YES/NO after max_retries — let agent continue
    print(f'review: no clear answer after {max_retries} attempts, continuing')
    return {'decision': 'think', 'wakeup': '\n[REVIEWER FEEDBACK] Review was inconclusive. Re-examine your work.'}
            

def extract_code(text: str) -> str:
    if "```" in text:
        blocks = text.split("```")
        if len(blocks) > 1:
            code_block = blocks[1]
            if code_block.strip().startswith("python"):
                first_newline = code_block.find('\n')
                if first_newline != -1:
                    code_block = code_block[first_newline:]
                else:
                    code_block = code_block.replace("python", "", 1)
            elif code_block.strip().startswith("py"):
                first_newline = code_block.find('\n')
                if first_newline != -1:
                    code_block = code_block[first_newline:]
                else:
                    code_block = code_block.replace("py", "", 1)
            return code_block.strip()
    return text.strip()

def code_action(state: AgentState):
    sysmsg = SystemMessagePromptTemplate.from_template(
        'you are code agent of the agent system')
    usrmsg = HumanMessagePromptTemplate.from_template(
        'specification of project you are working on is:\n{spec}\nend of specification.'
        'goal of agentic system is\n{goal}\nend of the goal.'
        'list of your previous actions is\n{actions}\nend of the list.'
        'look at the plan from the thinker agent:\n{plan}\nend of plan.'
        'The project working directory is: {prjdir}\n'
        'Your code is executed in a Python REPL. Everything you define in the REPL is ephemeral — '
        'it disappears after execution. To create project files, you must write their content to disk '
        'using open() and write(). For example, to create app.py you would write:\n'
        'content = """\nfrom fastapi import FastAPI\napp = FastAPI()\n"""\n'
        'with open("app.py", "w") as f:\n    f.write(content)\n\n'
        'You answer should be nothing except python code. If you can not do the plan, only print that you cant. '
        'Do as much as you can in one code block, it can be big enough to do all the plan. '
        'You answer should be nothing except python code (with proper formatting, ```python on start and ``` on the end)'
    )
    msglist = [sysmsg, usrmsg]
    repl = PythonREPL()
    action = ''
    for i in range(state['patience']):
        chat = ChatPromptTemplate.from_messages(msglist)
        chain = (chat | llm | StrOutputParser() | RunnableLambda(extract_code))
        print('code writing...')
        code = chain.invoke(state)
        print(f'--- generated code ---\n{code}\n--- end code ---')
        sentinel = 'code was executed without any errors'
        print('code executing...')
        console_out = repl.run(code + f'\nprint(\'{sentinel}\')')
        if sentinel in console_out:
            action += f'\nACTION:\nexecuted code:\n{code}\nresult:\n{console_out}\n'
            return {
                'actions': state['actions'] + [action],
                'tree': get_repo_structure.invoke({"root_path": state['prjdir']}),
                }
        msglist.append(AIMessage(code))
        # Truncate error output to prevent context overflow on retries
        truncated_out = console_out[:2000] if len(console_out) > 2000 else console_out
        error_report = HumanMessage(
            'there was some errors in your code, here is execution logs:\n' + truncated_out)
        print('ERROR: ', console_out)
        msglist.append(error_report)

    return {'actions': state['actions'] + ['\nACTION\ncode was not executed, too many failed attempts for code agent']}


def get_initial_state(goal: str, spec: str, prjdir:str, max_steps: int, patience=5, action_memory_size=5):
    prjdir = os.path.abspath(prjdir)
    initial_tree = get_repo_structure.invoke({"root_path": prjdir})
    return AgentState({
        'action_memory_size': action_memory_size,
        'actions': [],
        'decision': '',
        'goal': goal,
        'prjdir': prjdir,
        'iter_cnt': 0,
        'knowledge': '',
        'max_steps': max_steps,
        'patience': patience,
        'plan': '',
        'spec': spec,
        'thoughts': [],
        'wakeup': '',
        'tree': initial_tree,
        'prev_tree': initial_tree,
        'stale_count': 0,
        'review_count': 0,
    })

graph = StateGraph(state_schema=AgentState)
nodefuncs = [think, state_check, review, code_action]
for node in nodefuncs:
    graph.add_node(node.__name__, node)
graph.add_edge('think', 'state_check')
graph.add_conditional_edges('state_check', lambda state: state['decision'])
graph.add_conditional_edges('review', lambda state: state['decision'])
graph.add_edge('code_action', 'think')
graph.set_entry_point('think')
agent = graph.compile()
config = {"recursion_limit": 200}


def run_agent(goal, spec, prjdir=".", max_steps=30):
    initial_state = get_initial_state(goal, spec, prjdir, max_steps=max_steps)
    agent.invoke(initial_state)

# run_agent('built simple and nice betting web application in folder 4xbet')