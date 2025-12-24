import os
import dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import (
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    ChatPromptTemplate
)
from makesrs_prod import make_tree
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
    # model_name="qwen/qwen3-coder",
    model_name="z-ai/glm-4.7",
    base_url="https://api.polza.ai/api/v1",
    temperature=0.5,
    api_key=os.getenv('API_KEY')
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
        'you need to recap what you have done in one phrase and then plan in few detailed steps what to do next. '
        'plan only thinks that can be done using python code snippets. But do not write any code, only plan!'
        'and do not plan so much, only one step, that is closest to current project state'
        'implementator agent will not see the specification, so plan should contain all necessary context to implement what was planned.'
        'if task is to modify something, firstly you need to check what exactly you need to modify. '
        'if you are sure that goal is achieved, say only [GOAL_ACHIEVED].'
        'plan to create new components only when you are sure that existing components are tested and work well.'
        'if you have realized that you sayed [GOAL_ACHIEVED] but goal is not achieved, say [NOT_ACHIEVED] and you will not end cycle'
        '{wakeup}')
    chat = ChatPromptTemplate.from_messages(([sysmsg, usermsg]))
    chain = (chat | llm | StrOutputParser())
    print('thinking...')
    plan = chain.invoke(state)
    print(plan)
    return {'plan': plan, 'thoughts': state['thoughts'] + [plan]}


def similarity(text_a: str, text_b: str) -> float:
    return SequenceMatcher(None, text_a, text_b).ratio()


def state_check(state: AgentState):
    retdict = {'iter_cnt': state['iter_cnt'] + 1,
               'decision': 'code_action'
               }
    
    if 'GOAL_ACHIEVED' in state['plan'] and 'NOT_TRUE' not in state['plan']:
        retdict['decision'] = 'try_to_end'
    if state['iter_cnt'] >= state['max_steps']:
        retdict['decision'] = END
    
    retdict['actions'] = state['actions'][-state['action_memory_size']:]
    slen = len(state['thoughts'])
    if slen > 2 and similarity(state['thoughts'][slen - 1], state['thoughts'][slen - 2]) > 0.95:
        print('SIMILARITY > 0.95! RESETTING THOUGHTS')
        retdict['wakeup'] = 'you was repeated your last thought. WAKE UP! If action does not do anything, try different action, not be mad!' 
        retdict['thoughts'] = ['Agent started repeating itself, thought list was cleared.']
    else:
        retdict['wakeup'] = ''
    return retdict


def try_to_end(state: AgentState):
    sysmsg = SystemMessagePromptTemplate.from_template(
        'you are thinking agent of the agentic system')
    usermsg = HumanMessagePromptTemplate.from_template(
        common_context +
        'previous agent decided that your goal is achieved. Are you sure in this? Have you check and test everything works? Can user run your application?'
        'answer YES or NO. But be carefull, if you answer YES, you will not be able'
        'to do anything else, you lifecycle will be ended immediately.')
    msglist = [sysmsg, usermsg]
    while True:
        chat = ChatPromptTemplate.from_messages(msglist)
        chain = (chat | llm | StrOutputParser())
        print('trying to end...')
        answer = chain.invoke(state)
        if 'YES' in answer:
            return {'decision': END}
        elif 'NO' in answer:
            return {'decision': 'code_action'}
        wrong_answer_msg = HumanMessagePromptTemplate.from_template(
            'your answer is wrong. You should answer exactly YES or NO. Are you sure that your goal is achieved? Have you check and test everything?')
        msglist.append(AIMessagePromptTemplate.from_template(answer))
        msglist.append(wrong_answer_msg)
            

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
        'You answer should be nothing except python code. If you can not do the plan, only print that you cant'
        'This code can create files or folders, save file content in files, on anything else to complete the plan. Do as much as you can in one code block, it can be big enought to do all the plan'
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
        sentinel = 'code was executed without any errors' 
        print('code executing...')
        console_out = repl.run(code + f'\nprint(\'{sentinel}\')')
        if sentinel in console_out:
            action += f'\nACTION:\nexecuted code:\n{code}\nresult:\n{console_out}\n'
            return {
                'actions': state['actions'] + [action], 
                'tree': make_tree(state['prjdir'])
                }
        msglist.append(AIMessage(code))
        error_report = HumanMessage(
            'there was some errors in your code, here is execution logs:\n' + console_out)
        print('ERROR: ', console_out)
        msglist.append(error_report)

    return {'actions': state['actions'] + ['\nACTION\ncode was not executed, too many failed attempts for code agent']}


def get_initial_state(goal: str, spec: str, prjdir:str, max_steps: int, patience=5, action_memory_size=5):
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
        'tree': ''
    })

graph = StateGraph(state_schema=AgentState)
nodefuncs = [think, state_check, try_to_end, code_action]
for node in nodefuncs:
    graph.add_node(node.__name__, node)
graph.add_edge('think', 'state_check')
graph.add_conditional_edges('state_check', lambda state: state['decision'])
graph.add_conditional_edges('try_to_end', lambda state: state['decision'])
graph.add_edge('code_action', 'think')
graph.set_entry_point('think')
agent = graph.compile()
config = {"recursion_limit": 200}


def run_agent(goal, spec, max_steps=30):
    initial_state = get_initial_state(goal, spec, max_steps=max_steps)
    agent.invoke(initial_state)

# run_agent('built simple and nice betting web application in folder 4xbet')