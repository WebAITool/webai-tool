import logging
from pathlib import Path
import sys
import venv
import subprocess


PYRIGHT_CONFIG = """{
    "venvPath": ".",
    "venv": ".venv",
    "typeCheckingMode": "off"
}"""

VENV_PATH: Path
BACKEND_PATH: Path


def prepare_dev_env(prjdir: Path) -> None:
    global BACKEND_PATH
    BACKEND_PATH = prjdir / 'backend'

    if not BACKEND_PATH.exists():
        BACKEND_PATH.mkdir(exist_ok=True)

    global VENV_PATH
    VENV_PATH = BACKEND_PATH / '.venv'
    venv.create(str(VENV_PATH), with_pip=True)

    pyright_config_path = BACKEND_PATH / 'pyrightconfig.json'

    with pyright_config_path.open('w+') as file:
        file.write(PYRIGHT_CONFIG)


def run_pyright() -> str:
    python_path = VENV_PATH / 'bin' / 'python'
    requirements_path = BACKEND_PATH / 'requirements.txt'
    if requirements_path.exists():
        pip_result = subprocess.run([str(python_path),
                                     '-m', 'pip', 'install', '-r', str(requirements_path)],
                                    text=True, check=True, capture_output=True)

        if pip_result.returncode != 0:
            logging.debug("pip was executed: " + str(pip_result))

    return subprocess.run([sys.executable, '-m', 'pyright', '-p', str(
        BACKEND_PATH)], text=True, capture_output=True).stdout