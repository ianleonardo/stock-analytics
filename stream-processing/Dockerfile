FROM apache/spark:3.5.0
USER root
RUN apt-get update && apt-get install -y --no-install-recommends librdkafka-dev && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir redis psycopg2-binary kafka-python pandas numpy pyarrow
RUN mkdir -p /home/spark/.ivy2/cache /home/spark/.ivy2/jars && chown -R spark:spark /home/spark
COPY streaming_job.py /opt/streaming_job.py
USER spark
CMD ["/opt/spark/bin/spark-submit", \
     "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0", \
     "--master", "local[2]", \
     "/opt/streaming_job.py"]
