from pathlib import Path, PurePath
import sys
import venv
import subprocess

import pyright


PYRIGHT_CONFIG = {
  "venvPath": ".",
  "venv": ".venv"
}

VENV_PATH: Path
BACKEND_PATH: Path

def prepare_dev_env(prjdir: Path) -> None:
    global BACKEND_PATH
    BACKEND_PATH = prjdir / 'backend'

    if not BACKEND_PATH.exists():
        BACKEND_PATH.mkdir()

    global VENV_PATH
    VENV_PATH = BACKEND_PATH / '.venv'
    venv.create(str(VENV_PATH))
    
    pyright_config_path = BACKEND_PATH / 'pyrightconfig.json'

    with pyright_config_path.open('w+') as file:
        file.write(str(PYRIGHT_CONFIG))


def run_pyright() -> str:
    python_path = VENV_PATH / '.venv' / 'bin' / 'python' 
    subprocess.check_call([str(python_path.absolute()), '-m', 'pip', 'install', '-r', 'requirements.txt'])

    return subprocess.run([sys.executable, '-m', 'pyright', '-p=' + str(BACKEND_PATH.absolute())], text=True, check=True, capture_output=True).stdout    
