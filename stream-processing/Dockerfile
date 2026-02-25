# Spark streaming job: run with spark-submit from Spark Master/Worker context
# For local run: pip install -r requirements.txt && spark-submit streaming_job.py
FROM bitnami/spark:3.5
USER root
RUN pip install --no-cache-dir redis psycopg2-binary confluent-kafka
COPY streaming_job.py /opt/streaming_job.py
USER 1001
# Submit to Spark Master (override when running in compose)
CMD ["spark-submit", "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0", "--master", "spark://spark-master:7077", "/opt/streaming_job.py"]
