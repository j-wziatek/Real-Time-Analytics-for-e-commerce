import json
import os
from pathlib import Path
from kafka import KafkaConsumer, KafkaProducer


base_dir = Path.cwd()
data_path = os.path.join(base_dir, "data")

with open(os.path.join(data_path, "products.json"), "r", encoding="utf-8") as f:
    products = json.load(f)
    
os.makedirs(os.path.dirname(os.path.join(data_path, "debug/final_events.jsonl")), exist_ok=True)
open("data/debug/final_events.jsonl", "w").close()


products_by_id = {
    product["product_id"]: product
    for product in products
}

sessions_state = {}


ENRICHED_TOPIC = "enriched_events"
FINAL_TOPIC = "final_events"

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")


producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    key_serializer=lambda key: str(key).encode("utf-8")
)

consumer = KafkaConsumer(
    ENRICHED_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset="latest",
    enable_auto_commit=True,
    group_id="cleaned_consumer",
    value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    key_deserializer=lambda key: key.decode("utf-8") if key else None
)


def clean_session_start(event):
    return {
        "event_type": event["event_type"],
        "event_id": event["event_id"],
        "event_time": event["event_time"],
        "session_id": event["session_id"],
        "customer_id": event["customer_id"]
    }


def clean_add_to_basket(event):
    session_id = event["session_id"]

    base_product_ids = event["payload"].get("product_ids", [])

    accepted_recommendation_ids = [
        product["product_id"]
        for product in event.get("recommendation", {}).get("recommended_products", [])
        if product.get("accepted") is True
    ]

    final_product_ids = base_product_ids + accepted_recommendation_ids

    sessions_state[session_id] = {
        "products": final_product_ids
    }

    cleaned_recommendation = {
        "shown": event.get("recommendation", {}).get("shown", False),
        "recommended_products": [
            {
                "base_product": product["base_product"],
                "product_id": product["product_id"],
                "accepted": product["accepted"]
            }
            for product in event.get("recommendation", {}).get("recommended_products", [])
        ]
    }

    return {
        "event_type": event["event_type"],
        "event_id": event["event_id"],
        "event_time": event["event_time"],
        "session_id": event["session_id"],
        "customer_id": event["customer_id"],
        "products": final_product_ids,
        "recommendation": cleaned_recommendation
    }


def clean_make_decision(event):
    session_id = event["session_id"]
    decision = event["payload"]["decision"]

    if decision == "abandoned":
        product_ids = []
    else:
        product_ids = sessions_state[session_id]["products"]

    basket_products = [
        products_by_id[product_id]
        for product_id in product_ids
        if product_id in products_by_id
    ]

    basket_value = sum(product["price"] for product in basket_products)

    basket_margin = sum(
        product["price"] * product["margin_pct"]
        for product in basket_products
    )

    final_event = {
        "event_type": "decision",
        "event_id": event["event_id"],
        "event_time": event["event_time"],
        "session_id": event["session_id"],
        "customer_id": event["customer_id"],
        "decision": decision,
        "basket": {
            "products": product_ids,
            "value": round(basket_value, 2),
            "margin": round(basket_margin, 2)
        }
    }

    sessions_state.pop(session_id, None)

    return final_event


def clean_event(event):
    event_type = event.get("event_type")

    if event_type == "session_start":
        return clean_session_start(event)

    if event_type == "add_to_basket":
        return clean_add_to_basket(event)

    if event_type == "make_decision":
        return clean_make_decision(event)

    return event


print(f"Reading from topic: {ENRICHED_TOPIC}")
print(f"Writing to topic: {FINAL_TOPIC}")

for message in consumer:
    enriched_event = message.value

    final_event = clean_event(enriched_event)

    producer.send(
        topic=FINAL_TOPIC,
        key=final_event["session_id"],
        value=final_event
    )

    producer.flush()

    with open("data/debug/final_events.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(final_event) + "\n")

    print(json.dumps(final_event, indent=2))