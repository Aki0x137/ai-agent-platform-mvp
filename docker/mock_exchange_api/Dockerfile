FROM python:3.11-slim

WORKDIR /app

COPY docker/mock_exchange_api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY docker/mock_exchange_api/app.py ./app.py
COPY docker/mock_exchange_api/fixtures ./fixtures

EXPOSE 8081

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]
