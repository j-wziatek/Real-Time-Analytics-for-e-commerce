import json
import os
from pathlib import Path
from kafka import KafkaConsumer, KafkaProducer
import random

base_dir = Path.cwd()
data_path = os.path.join(base_dir, "data")
with open(os.path.join(data_path, "association_rules.json"), "r", encoding="utf-8") as f:
    association_rules  = json.load(f)
with open(os.path.join(data_path, "products.json"), "r", encoding="utf-8") as f:
    products = json.load(f)
with open(os.path.join(data_path, "customers.json"), "r", encoding="utf-8") as f:
    customers = json.load(f)


SCORE_THRESHOLD = 0.65

RAW_TOPIC = "raw_events"
ENRICHED_TOPIC = "enriched_events"

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")


customers_by_id = {
    customer["customer_id"]: customer
    for customer in customers
}

products_by_id = {
    product["product_id"]: product
    for product in products
}


producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    key_serializer=lambda key: str(key).encode("utf-8")
)

consumer = KafkaConsumer(
    RAW_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset="latest",
    enable_auto_commit=True,
    group_id="recommendation_consumer",
    value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    key_deserializer=lambda key: key.decode("utf-8") if key else None
)


def score_products(customer, products_of_type):

    prices = [product["price"] for product in products_of_type]

    min_price = min(prices)
    max_price = max(prices)
    avg_price = sum(prices) / len(prices)

    scored_products = []

    for product in products_of_type:
        popularity_score = product["base_popularity"]

        premium_score = 1 + customer["premium_affinity"] * ((product["premium_level"] - 1) / 3)

        if max_price == min_price:
            price_position = 0
            price_range_ratio = 0

        else:
            price_position = (product["price"] - min_price) / (max_price - min_price)
            price_range_ratio = (max_price - min_price) / avg_price

        price_score = 1 - (customer["price_sensitivity"] * price_position * price_range_ratio)
        price_score = max(0.05, min(1, price_score))

        preferred_brand = customer["preferred_brands"][product["category_name"]]

        brand_score = 1

        if product["brand"] == preferred_brand:
            brand_score += customer["brand_affinity"]

        raw_score = (
            popularity_score
            * premium_score
            * price_score
            * brand_score
        )

        score = raw_score / (1 + raw_score)

        scored_products.append({
            **product,
            "score": round(score, 4)
        })

    return max(scored_products, key=lambda product: product["score"])


def get_rule_values(rule):
    antecedents = set(rule["antecedents"])
    consequents = rule["consequents"]
    
    if isinstance(antecedents, str):
        antecedents = [antecedents]

    if isinstance(consequents, str):
        consequents = [consequents]

    return antecedents, consequents


def enrich_add_to_basket_event(event):
    customer_id = event["customer_id"]
    customer = customers_by_id.get(customer_id)

    basket_product_ids = event["payload"].get("product_ids", [])

    basket_products = [
        products_by_id[product_id]
        for product_id in basket_product_ids
        if product_id in products_by_id
    ]

    basket_base_products = {
        product["base_product"]
        for product in basket_products
    }

    candidate_by_base_product = {}

    recommendation = {
        "shown": False,
        "recommended_products": []
    }

    candidate_recommendations = []

    for rule in association_rules:
        antecedents, consequents = get_rule_values(rule)

        if set(antecedents).issubset(basket_base_products):
            for recommended_base_product in consequents:
                if recommended_base_product in basket_base_products:
                    continue

                products_of_type = [
                    product
                    for product in products
                    if product["base_product"] == recommended_base_product
                ]

                if not products_of_type:
                    continue

                best_product = score_products(customer, products_of_type)

                candidate_recommendations.append({
                    "product_id": best_product["product_id"],
                    "base_product": best_product["base_product"],
                    "score": best_product["score"]
                })

    if not candidate_recommendations:
        event["recommendation"] = recommendation
        return event

    unique_recommendations = {}
    for rec in candidate_recommendations:
        product_id = rec["product_id"]
        if (product_id not in unique_recommendations):
            unique_recommendations[product_id] = rec
    
    candidate_recommendations = list(unique_recommendations.values())
    candidate_recommendations = sorted(
        candidate_recommendations,
        key=lambda x: x["score"],
        reverse=True
    )

    for rec in candidate_recommendations:
        rec["score"] = rec["score"] + random.uniform(0, 0.3)
        rec["accepted"] = rec["score"] > SCORE_THRESHOLD
    
    recommendation["shown"] = True
    recommendation["recommended_products"] = candidate_recommendations

    event["recommendation"] = recommendation
    return event


def process_event(event):
    if event["event_type"] != "add_to_basket":
        return event

    return enrich_add_to_basket_event(event)


print(f"Reading from topic: {RAW_TOPIC}")
print(f"Writing to topic: {ENRICHED_TOPIC}")

for message in consumer:
    event = message.value

    final_event = process_event(event)

    producer.send(
        topic=ENRICHED_TOPIC,
        key=final_event["session_id"],
        value=final_event
    )

    producer.flush()

    if final_event["event_type"] == "add_to_basket":
        print(json.dumps(final_event, indent=2))