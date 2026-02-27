FROM python:3.12-slim

WORKDIR /app

COPY shared/setup.py /app/shared_pkg/setup.py
COPY shared/shared /app/shared_pkg/shared
RUN pip install -e /app/shared_pkg

COPY services/tracker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/tracker /app/service
WORKDIR /app/service

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8013"]
