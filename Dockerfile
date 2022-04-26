FROM python:3.8.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8080

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY main.py /app/
COPY controllers/ /app/controllers/

CMD uvicorn main:app --host 0.0.0.0 --port $PORT