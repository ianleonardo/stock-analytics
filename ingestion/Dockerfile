FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY config.py topics.py producer.py ./
CMD ["python", "-u", "producer.py"]
