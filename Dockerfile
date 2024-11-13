FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY . /app/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "fsm_aiogram:dp", "--host", "0.0.0.0", "--port", "8000"]
