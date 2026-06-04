from datetime import datetime
from pathlib import Path
import logging

LOGS_PATH = Path('./.logs')
LOGS_PATH.mkdir(exist_ok=True)

LOG_FILE = LOGS_PATH / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG)