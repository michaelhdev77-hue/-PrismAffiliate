FROM python:3.12-slim

WORKDIR /app

COPY shared/setup.py /app/shared_pkg/setup.py
COPY shared/shared /app/shared_pkg/shared
RUN pip install -e /app/shared_pkg

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker /app/service
WORKDIR /app/service
