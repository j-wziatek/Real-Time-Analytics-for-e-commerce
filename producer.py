import json
import random
import time
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import os
from kafka import KafkaProducer

base_dir = Path.cwd()
data_path = os.path.join(base_dir, "data")
with open(os.path.join(data_path, "base", "categories.json"), "r", encoding="utf-8") as f:
    categories = json.load(f)
with open(os.path.join(data_path, "products.json"), "r", encoding="utf-8") as f:
    products = json.load(f)
with open(os.path.join(data_path, "customers.json"), "r", encoding="utf-8") as f:
    customers = json.load(f)

os.makedirs(os.path.dirname("data/debug/events.jsonl"), exist_ok=True)
open("data/debug/events.jsonl", "w").close()


active_sessions = {}
next_session_id = 1
completed_sessions = 0
n_sessions = 1000

simulated_time = datetime.now().replace(
    hour=12,
    minute=0,
    second=0,
    microsecond=0
)

events_since_time_change = 0
time_change_every = max(1, min(5, n_sessions // 100))

event_id = 1


KAFKA_TOPIC = "raw_events"
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "broker:9092")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    key_serializer=lambda key: str(key).encode("utf-8")
)


def create_event(event_type, customer_id, session_id, payload=None):
    global simulated_time
    global events_since_time_change
    global event_id

    if events_since_time_change >= time_change_every:
        simulated_time += timedelta(
            minutes=random.randint(1, 5),
            seconds=random.randint(0, 59)
        )
        events_since_time_change = 0
    else:
        simulated_time += timedelta(
            seconds=random.randint(15, 59)
        )

    events_since_time_change += 1
    
    return {
        "event_id": str(event_id),
        "event_time": simulated_time.isoformat(),
        "ingestion_time": datetime.now().isoformat(),
        "event_type": event_type,
        "customer_id": customer_id,
        "session_id": session_id,
        "payload": payload or {}
    }


def append_event(event, output_path = "data/debug/events.jsonl"):
    output_path = Path(output_path)

    with open(output_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    producer.send(
        topic=KAFKA_TOPIC,
        key=event["session_id"],
        value=event
        )

    producer.flush()


def start_session():
    global next_session_id
    
    active_customer_ids = {
        session["customer"]["customer_id"]
        for session in active_sessions.values()
    }

    available_customers = [
        customer
        for customer in customers
        if customer["customer_id"] not in active_customer_ids
    ]

    if not available_customers:
        return None

    customer = random.choice(
        available_customers
    )

    session_id = next_session_id
    next_session_id += 1

    session_interest = {}

    n_categories = random.randint(
        1,
        min(2, len(categories))
    )

    selected_categories = random.sample(
        categories,
        k=n_categories
    )

    for category in selected_categories:
        category_name = category["category_name"]

        product_types = [
            product["product_type"]
            for product in category["product_types"]
        ]

        n_product_types = random.randint(
            1,
            min(3, len(product_types))
        )

        selected_product_types = random.sample(
            product_types,
            k=n_product_types
        )

        session_interest[category_name] = (
            selected_product_types
        )

    active_sessions[session_id] = {
        "session_id": session_id,
        "customer": customer,
        "session_interest": session_interest,
        "basket": [],
        "status": "started"
    }

    return create_event(
        event_type="session_start",
        customer_id=customer["customer_id"],
        session_id=session_id,
        payload={"session_interest": session_interest}
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


def add_to_basket(session):

    customer = session["customer"]

    basket = []

    for category_name, base_products in session["session_interest"].items():

        for base_product in base_products:

            products_of_type = [
                product
                for product in products
                if product["category_name"] == category_name
                and product["base_product"] == base_product
            ]

            if not products_of_type:
                continue

            best_product = score_products(customer, products_of_type)

            basket.append(best_product["product_id"])

    session["basket"] = basket
    session["status"] = "basket_ready"

    return create_event(
        event_type="add_to_basket",
        customer_id=customer["customer_id"],
        session_id=session["session_id"],
        payload={"product_ids": basket}
    )


def make_decision(session):

    customer = session["customer"]

    decision = (
        "abandoned"
        if random.random() <= customer["abandon_probability"]
        else "purchased"
    )

    session["status"] = "closed"

    active_sessions.pop(
        session["session_id"],
        None
    )

    return create_event(
        event_type="make_decision",
        customer_id=customer["customer_id"],
        session_id=session["session_id"],
        payload={
            "decision": decision,
            "product_ids": session["basket"]
        }
    )


while completed_sessions < n_sessions:

    sessions_waiting_for_basket = [
        session for session in active_sessions.values()
        if session["status"] == "started"
    ]

    sessions_ready_for_decision = [
        session for session in active_sessions.values()
        if session["status"] == "basket_ready"
    ]

    active_customer_ids = {
        session["customer"]["customer_id"]
        for session in active_sessions.values()
    }

    can_start_new_session = (
        len(active_customer_ids) < len(customers)
        and completed_sessions + len(active_sessions) < n_sessions
    )

    possible_actions = []

    if can_start_new_session:
        possible_actions.append("start_session")

    if sessions_waiting_for_basket:
        possible_actions.append("add_to_basket")

    if sessions_ready_for_decision:
        possible_actions.append("make_decision")

    action = random.choice(possible_actions)

    print(f"Selected action: {action}")

    if action == "start_session":
        event = start_session()

    elif action == "add_to_basket":
        session = random.choice(sessions_waiting_for_basket)
        event = add_to_basket(session)

    elif action == "make_decision":
        session = random.choice(sessions_ready_for_decision)
        event = make_decision(session)
        completed_sessions += 1

    append_event(event)
    print(json.dumps(event, indent=2))
    event_id+=1
    time.sleep(0.50)


producer.close()