FROM python:3.11-slim

WORKDIRR /app

COPY ./app/requirements.txt .

pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app"]