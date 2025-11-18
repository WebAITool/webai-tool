import os
import subprocess
from gener import generate
from prompts import specmaker

PRJPATH = 'I:/NSU/WebAI/2xbet' 
VERBOSE = False

res = subprocess.run(["tree", PRJPATH, '/F'], shell=True,encoding='cp866', capture_output=True, text=True, check=True)
res = res.stdout.splitlines()
tree = '\n'.join(res[2:])

filepaths = []
for path, dirs, files in os.walk(PRJPATH):
    for file in files:
        filepath = os.path.join(path, file)
        filepaths.append(filepath)

project = ''
for filepath in filepaths:
    try:
        file = open(filepath).read()
    except Exception as e:
        if VERBOSE:
            print(f'error on file {filepath}')
            print(e)
        continue
    project = project + 'file from path: ' + filepath + '\n'
    project = project + file + '\nEND OF FILE\n'

prompt = specmaker.format(file_tree=tree, project_code=project)
doc = generate(prompt)
print(doc)
with open('I:/NSU/WebAI/webai_toolkit/doc.md', 'w', encoding='utf-8') as docfile:
    docfile.write(doc)
