import json
import pandas as pd
import redis
import os

base_dir = "//home//jovyan//work"
data_path = os.path.join(base_dir, "data")

with open(os.path.join(data_path, "products.json"), "r", encoding="utf-8") as f:
    products = json.load(f)
with open(os.path.join(data_path,"base", "categories.json"), "r", encoding="utf-8") as f:
    categories = json.load(f)
with open(os.path.join(data_path, "association_rules.json"), "r", encoding="utf-8") as f:
    association_rules = json.load(f)

products_df = pd.DataFrame(products)
categories_df = pd.DataFrame(categories)

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


product_type_to_category = {}

for category in categories:
    for product_type in category["product_types"]:
        product_type_to_category[product_type["product_type"]] = category["category_name"]


def get_events_df():
    events = redis_client.lrange("all_events", 0, -1)

    if not events:
        return pd.DataFrame()

    return pd.DataFrame(
        [
            json.loads(event)
            for event in events
        ]
    )


def get_latest_event():
    latest_event = redis_client.get("latest_event")

    if not latest_event:
        return None

    return json.loads(latest_event)


def get_active_sessions():
    return redis_client.scard("active_sessions")

def get_finished_sessions():
    return int(redis_client.get("finished_sessions") or 0)

def get_active_sessions_over_time(events_df):

    if events_df.empty:
        return pd.DataFrame(
            columns=[
                "event_time",
                "active_sessions"
            ]
        )

    df = events_df.copy()
    df["event_time"] = pd.to_datetime(df["event_time"])
    df = df.sort_values("event_time")

    active_sessions = set()
    rows = []

    for _, event in df.iterrows():

        event_type = event["event_type"]
        session_id = event["session_id"]

        if event_type == "session_start":
            active_sessions.add(session_id)

        elif event_type == "decision":
            active_sessions.discard(session_id)

        rows.append({
            "event_time": event["event_time"],
            "active_sessions": len(active_sessions)
        })

    return pd.DataFrame(rows)


def get_max_active_sessions(events_df):

    active_sessions_df = get_active_sessions_over_time(events_df)

    if active_sessions_df.empty:
        return 0

    return int(active_sessions_df["active_sessions"].max())


def get_sales_kpis(events_df):

    if events_df.empty:
        return {
            "finished_transactions": 0,
            "purchase_rate": 0,
            "sales_value": 0,
            "products_sold": 0,
            "profit": 0,
            "avg_margin_pct": 0
        }
        
    decision_df = events_df[
        events_df["event_type"] == "decision"
    ]

    purchased_df = decision_df[
        decision_df["decision"] == "purchased"
    ]

    finished_transactions = len(purchased_df)

    purchase_rate = (
        finished_transactions /
        len(decision_df) * 100
        if len(decision_df) > 0
        else 0
    )

    sales_value = 0
    products_sold = 0
    profit = 0

    for _, event in purchased_df.iterrows():

        basket = event["basket"]

        sales_value += basket["value"]
        profit += basket["margin"]
        products_sold += len(
            basket["products"]
        )

    avg_margin_pct = (
        profit / sales_value * 100
        if sales_value > 0
        else 0
    )

    return {
        "finished_transactions": finished_transactions,
        "purchase_rate": round(purchase_rate, 2),
        "sales_value": round(sales_value, 2),
        "products_sold": products_sold,
        "profit": round(profit, 2),
        "avg_margin_pct": round(avg_margin_pct, 2)
    }


def get_sales_by_dimension(events_df, dimension):

    purchased_df = events_df[
        (events_df["event_type"] == "decision") &
        (events_df["decision"] == "purchased")
    ]

    rows = []

    for _, event in purchased_df.iterrows():

        for product_id in event["basket"]["products"]:

            rows.append({
                "product_id": product_id
            })

    if not rows:
        return pd.DataFrame()

    sold_df = pd.DataFrame(rows)

    sold_df = sold_df.merge(
        products_df[
            [
                "product_id",
                dimension,
                "price"
            ]
        ],
        on="product_id",
        how="left"
    )

    return (
        sold_df
        .groupby(dimension, dropna=False)
        .agg(
            products_sold=("product_id", "count"),
            sales_value=("price", "sum")
        )
        .reset_index()
        .sort_values(
            "sales_value",
            ascending=False
        )
    )


def get_sales_by_product(events_df, dimension, selection=None):

    if events_df.empty:
        return pd.DataFrame(
            columns=[
                "product_id",
                "product_name",
                dimension,
                "products_sold"
            ]
        )

    purchased_df = events_df[
        (events_df["event_type"] == "decision") &
        (events_df["decision"] == "purchased")
    ]

    rows = []

    for _, event in purchased_df.iterrows():

        for product_id in event["basket"]["products"]:

            rows.append({
                "product_id": product_id
            })

    if not rows:
        return pd.DataFrame(
            columns=[
                "product_id",
                "product_name",
                dimension,
                "products_sold"
            ]
        )

    sold_df = pd.DataFrame(rows)

    sold_df = sold_df.merge(
        products_df[
            [
                "product_id",
                "product_name",
                dimension
            ]
        ],
        on="product_id",
        how="left"
    )

    if selection is not None:
        sold_df = sold_df[
            sold_df[dimension] == selection
        ]

    return (
        sold_df
        .groupby(
            [
                "product_id",
                "product_name",
                dimension
            ]
        )
        .size()
        .reset_index(name="products_sold")
        .sort_values(
            "products_sold",
            ascending=False
        )
        .head(15)
    )


def get_sales_value_by_product(events_df, dimension, selection=None):

    if events_df.empty:
        return pd.DataFrame(
            columns=[
                "product_id",
                "product_name",
                dimension,
                "sales_value"
            ]
        )

    purchased_df = events_df[
        (events_df["event_type"] == "decision") &
        (events_df["decision"] == "purchased")
    ]

    rows = []

    for _, event in purchased_df.iterrows():

        basket = event["basket"]
        products = basket["products"]

        for product_id in products:

            rows.append({
                "product_id": product_id
            })

    if not rows:
        return pd.DataFrame(
            columns=[
                "product_id",
                "product_name",
                dimension,
                "sales_value"
            ]
        )

    sold_df = pd.DataFrame(rows)

    sold_df = sold_df.merge(
        products_df[
            [
                "product_id",
                "product_name",
                dimension,
                "price"
            ]
        ],
        on="product_id",
        how="left"
    )

    if selection is not None:
        sold_df = sold_df[
            sold_df[dimension] == selection
        ]

    return (
        sold_df
        .groupby(
            [
                "product_id",
                "product_name",
                dimension
            ],
            as_index=False
        )
        .agg(
            sales_value=("price", "sum")
        )
        .sort_values(
            "sales_value",
            ascending=False
        )
        .head(15)
    )





def get_association_rules_by_category():

    rows = []

    for rule in association_rules:

        antecedents = rule["antecedents"]
        consequents = rule["consequents"]

        all_items = antecedents + consequents

        rule_categories = {
            product_type_to_category.get(item)
            for item in all_items
        }

        rule_categories.discard(None)

        if not rule_categories:
            category_name = "unknown"
        elif len(rule_categories) == 1:
            category_name = list(rule_categories)[0]
        else:
            category_name = "mixed"

        rows.append({
            "category_name": category_name,
            "rule_text": (
                f"{', '.join(antecedents)} -> "
                f"{', '.join(consequents)}"
            ),
            "support": rule["support"],
            "confidence": rule["confidence"],
            "lift": rule["lift"]
        })

    return pd.DataFrame(rows)


def get_recommendation_kpis(events_df):

    empty_result = {
        "recommendations_shown": 0,
        "recommendations_accepted": 0,
        "acceptance_rate": 0,
        "sales_value": 0,
        "profit": 0,
        "most_popular_product_type": "—"
    }

    if events_df.empty:
        return empty_result

    decision_df = events_df[
        events_df["event_type"] == "decision"
    ].copy()

    if decision_df.empty:
        return empty_result

    closed_sessions = set(
        decision_df["session_id"]
    )

    recommendation_events_df = events_df[
        events_df["event_type"] == "add_to_basket"
    ].copy()

    recommendation_events_df = recommendation_events_df[
        recommendation_events_df["session_id"].isin(closed_sessions)
    ]

    recommendation_events_df = recommendation_events_df[
        recommendation_events_df["recommendation"].apply(
            lambda x: isinstance(x, dict) and x.get("shown") == True
        )
    ]

    recommendations_shown = len(recommendation_events_df)

    if recommendations_shown == 0:
        return empty_result

    rows = []

    for _, event in recommendation_events_df.iterrows():

        session_id = event["session_id"]

        session_decision_df = decision_df[
            decision_df["session_id"] == session_id
        ].sort_values(
            "event_time"
        )

        purchased = (
            not session_decision_df.empty
            and session_decision_df.iloc[-1]["decision"] == "purchased"
        )

        recommended_products = (
            event
            .get("recommendation", {})
            .get("recommended_products", [])
        )

        for product in recommended_products:

            if product.get("accepted") == True:

                rows.append({
                    "session_id": session_id,
                    "product_id": product.get("product_id"),
                    "base_product": product.get("base_product"),
                    "purchased": purchased
                })

    recommendations_accepted = len(rows)

    acceptance_rate = (
        recommendations_accepted / recommendations_shown * 100
        if recommendations_shown > 0
        else 0
    )

    if not rows:
        return {
            "recommendations_shown": recommendations_shown,
            "recommendations_accepted": 0,
            "acceptance_rate": round(acceptance_rate, 2),
            "sales_value": 0,
            "profit": 0,
            "most_popular_product_type": "—"
        }

    accepted_df = pd.DataFrame(rows)

    most_popular_product_type = (
        accepted_df["base_product"]
        .dropna()
        .mode()
        .iloc[0]
        if not accepted_df["base_product"].dropna().empty
        else "—"
    )

    purchased_accepted_df = accepted_df[
        accepted_df["purchased"] == True
    ].copy()

    if purchased_accepted_df.empty:
        sales_value = 0
        profit = 0
    else:
        purchased_accepted_df = purchased_accepted_df.merge(
            products_df[
                [
                    "product_id",
                    "price",
                    "margin_pct"
                ]
            ],
            on="product_id",
            how="left"
        )

        sales_value = purchased_accepted_df["price"].sum()

        profit = (
            purchased_accepted_df["price"] *
            purchased_accepted_df["margin_pct"]
        ).sum()

    return {
        "recommendations_shown": recommendations_shown,
        "recommendations_accepted": recommendations_accepted,
        "acceptance_rate": round(acceptance_rate, 2),
        "sales_value": round(sales_value, 2),
        "profit": round(profit, 2),
        "most_popular_product_type": most_popular_product_type
    }


def get_recommendation_product_stats(events_df):

    if events_df.empty:
        return None

    decision_df = events_df[
        events_df["event_type"] == "decision"
    ]

    closed_sessions = set(
        decision_df["session_id"]
    )

    recommendation_events_df = events_df[
        events_df["event_type"] == "add_to_basket"
    ].copy()

    recommendation_events_df = recommendation_events_df[
        recommendation_events_df["session_id"].isin(closed_sessions)
    ]

    rows = []

    for _, event in recommendation_events_df.iterrows():

        recommendation = event.get(
            "recommendation",
            {}
        )

        if not recommendation.get("shown"):
            continue

        for product in recommendation.get(
            "recommended_products",
            []
        ):

            rows.append({
                "Product type": product.get("base_product"),
                "Accepted": product.get("accepted", False)
            })

    if not rows:
        return pd.DataFrame(
            columns=[
                "Product type",
                "Shown",
                "Accepted",
                "Acceptance rate"
            ]
        )

    df = pd.DataFrame(rows)

    result = (
        df.groupby("Product type")
        .agg(
            Shown=("Product type", "count"),
            Accepted=("Accepted", "sum")
        )
        .reset_index()
    )

    result["Acceptance rate"] = (result["Accepted"] / result["Shown"] * 100).map("{:.2f}%".format)

    return result.sort_values(
        "Shown",
        ascending=False
    )