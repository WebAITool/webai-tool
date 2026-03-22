import logging
from pathlib import Path
from tqdm import tqdm
import os
import subprocess
from gener import generate
from prompts import specmaker
from prompts import header_maker

def make_tree(prjpath):
    res = subprocess.run(["tree",
                          prjpath,
                          '--gitignore'],
                         shell=(os.name == 'nt'),
                         capture_output=True,
                         text=True,
                         check=True,
                         encoding=('cp866' if os.name == 'nt' else None))
    res = res.stdout.splitlines()
    tree = '\n'.join(res[2:])
    logging.info(f"{prjpath} tree: " + tree)
    return tree

# PRJPATH = 'I:/NSU/WebAI/2xbet' 
VERBOSE = False

def makesrs(prjpath):
    tree = make_tree(prjpath)

    filepaths = []
    files_and_dirs = subprocess.run(['tree',
                            prjpath,
                            '--gitignore',
                            '-fi',
                            '--noreport'],
                           shell=(os.name == 'nt'),
                           encoding=('cp866' if os.name == 'nt' else None),
                           capture_output=True,
                           text=True,
                           check=True).stdout.splitlines()

    for filepath in files_and_dirs:
        if Path(filepath).is_dir():
            continue

        filepaths.append(filepath)


    project = ''

    for filepath in tqdm(filepaths):
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

        if filedoc is not None and len(filedoc) > len(file):
            filedoc = file
        
        project = project + 'file (or file description, if file is too big) from path: ' + filepath + '\n'
        project = project + filedoc + '\nEND OF FILE (or file description)\n'


    prompt = specmaker.format(file_tree=tree, project_code=project)

    doc = generate(prompt)
    # with open('I:/NSU/WebAI/webai_toolkit/doc_prod.md', 'w', encoding='utf-8') as docfile:
    #     docfile.write(doc)
    return doc

