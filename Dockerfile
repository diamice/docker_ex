FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1

ENV PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*


RUN apt-get install -y redis-server

WORKDIR /app

COPY . /app/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8000

CMD redis-server --daemonize yes && uvicorn app:main --host 0.0.0.0 --port 8000
