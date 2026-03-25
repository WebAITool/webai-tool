from datetime import datetime
from pathlib import Path


LOGS_PATH = Path('./.logs')

LOGS_PATH.mkdir(exist_ok=True)

LOG_FILE = LOGS_PATH / \
    (str(datetime.now().strftime('%d.%m.%Y-%H:%M:%S')) + '.log')
