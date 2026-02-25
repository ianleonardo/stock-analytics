"""Create Kafka topics if they do not exist."""
import logging
from confluent_kafka.admin import AdminClient, NewTopic

from config import KAFKA_BOOTSTRAP_SERVERS, TOPICS, NUM_PARTITIONS, REPLICATION_FACTOR

logger = logging.getLogger(__name__)

def ensure_topics():
    client = AdminClient({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})
    new_topics = [
        NewTopic(topic, num_partitions=NUM_PARTITIONS, replication_factor=REPLICATION_FACTOR)
        for topic in TOPICS
    ]
    fs = client.create_topics(new_topics)
    for topic, f in fs.items():
        try:
            f.result()
            logger.info("Created topic %s", topic)
        except Exception as e:
            if "already exists" in str(e).lower() or "topic_already_exists" in str(e).lower():
                logger.debug("Topic %s already exists", topic)
            else:
                logger.warning("Topic %s: %s", topic, e)
