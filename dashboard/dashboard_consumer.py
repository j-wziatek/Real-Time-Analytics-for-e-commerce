import json
import os
from kafka import KafkaConsumer
import redis


TOPIC = "final_events"
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")
consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset="latest",
    enable_auto_commit=True,
    group_id="dashboard_state",
    value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    key_deserializer=lambda key: key.decode("utf-8") if key else None
)

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


print("Dashboard consumer started")
redis_client.flushdb()
print("Redis cleared")


for message in consumer:

    event = message.value

    event_type = event["event_type"]
    session_id = str(event["session_id"])

    redis_client.set("latest_event", json.dumps(event))

    redis_client.lpush("all_events", json.dumps(event))

    if event_type == "session_start":
        redis_client.sadd("active_sessions", session_id)

    elif event_type == "decision":
        redis_client.srem("active_sessions", session_id)
        redis_client.incr("finished_sessions")

    print(
        f"{event_type:<20} | "
        f"active_sessions = {redis_client.scard('active_sessions'):<10} | "
        f"finished_sessions = {redis_client.get('finished_sessions') or 0:<10} | "
        f"events = {redis_client.llen('all_events'):<10}"
    )