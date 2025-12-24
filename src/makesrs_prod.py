import os
import subprocess
from gener import generate
from prompts import specmaker
from prompts import header_maker

def make_tree(prjpath):
    res = subprocess.run(["tree", prjpath, '/F'], shell=True,encoding='cp866', capture_output=True, text=True, check=True)
    res = res.stdout.splitlines()
    tree = '\n'.join(res[2:])
    return tree

# PRJPATH = 'I:/NSU/WebAI/2xbet' 
VERBOSE = False

def makesrs(prjpath):

    tree = make_tree(prjpath)

    filepaths = []
    for path, dirs, files in os.walk(prjpath):
        for file in files:
            filepath = os.path.join(path, file)
            filepaths.append(filepath)

    project = ''

    i = 0
    for filepath in filepaths:
        try:
            file = open(filepath).read()
        except Exception as e:
            if VERBOSE:
                print(f'error on file {filepath}')
                print(e)
            continue

        if len(file) < 2000: # тогда не сжимаем его, а как есть оставляем.
            filedoc = file
            print('file is small, so not document it. Len of file:', len(file), 'characters')
        else:
            filedoc_prompt = header_maker + file
            try:
                filedoc = generate(filedoc_prompt)
            except Exception as e:
                print(e)
                print('error on generating, trying again')
                filedoc = generate(filedoc_prompt)

            print(f'file len: {len(file)}')
            print(f'file doc len: {len(filedoc)}')
        if len(filedoc) > len(file):
            filedoc = file
        
        project = project + 'file (or file description, if file is too big) from path: ' + filepath + '\n'
        project = project + filedoc + '\nEND OF FILE (or file description)\n'


    prompt = specmaker.format(file_tree=tree, project_code=project)

    doc = generate(prompt)
    # with open('I:/NSU/WebAI/webai_toolkit/doc_prod.md', 'w', encoding='utf-8') as docfile:
    #     docfile.write(doc)
    return doc

