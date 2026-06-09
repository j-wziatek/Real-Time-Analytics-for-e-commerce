import json
import random
import os
from pathlib import Path
from collections import Counter


base_dir = Path.cwd()
data_path = os.path.join(base_dir, "data")


with open(os.path.join(data_path, "base", "categories.json"), "r", encoding="utf-8") as f:
    categories = json.load(f)

with open(os.path.join(data_path, "base", "brands.json"), "r", encoding="utf-8") as f:
    brands = json.load(f)


segments = {
    "budget": {
        "weight": 25,
        "premium_affinity": (0.00, 0.20),
        "price_sensitivity": (0.80, 1.00),
        "brand_affinity": (0.10, 0.30),
        "abandon_probability": (0.25, 0.50)
    },
    "regular": {
        "weight": 45,
        "premium_affinity": (0.30, 0.60),
        "price_sensitivity": (0.40, 0.70),
        "brand_affinity": (0.30, 0.60),
        "abandon_probability": (0.15, 0.30)
    },
    "premium": {
        "weight": 15,
        "premium_affinity": (0.80, 1.00),
        "price_sensitivity": (0.00, 0.30),
        "brand_affinity": (0.50, 0.80),
        "abandon_probability": (0.05, 0.20)
    },
    "brand_loyal": {
        "weight": 10,
        "premium_affinity": (0.30, 0.70),
        "price_sensitivity": (0.20, 0.60),
        "brand_affinity": (0.80, 1.00),
        "abandon_probability": (0.10, 0.25)
    },
    "browser": {
        "weight": 5,
        "premium_affinity": (0.20, 0.50),
        "price_sensitivity": (0.40, 0.80),
        "brand_affinity": (0.10, 0.40),
        "abandon_probability": (0.55, 0.90)
    }
}


def generate_customers(n_customers, output_path, seed = 42):

    output_path = os.path.join(data_path, output_path)

    random.seed(seed)
    customers = []

    for customer_id in range(1, n_customers + 1):
        segment = random.choices(
            population=list(segments.keys()),
            weights=[selected_segment["weight"] for selected_segment in segments.values()],
            k=1
        )[0]

        selected_segment = segments[segment]

        preferred_brands = {}

        for category in categories:
            category_name = category["category_name"]
            preferred_brands[category_name] = random.choice(
                list(brands[category_name].keys())
            )


        customers.append({
            "customer_id": customer_id,
            "segment": segment,
            "preferred_brands": preferred_brands,
            "premium_affinity": round(random.uniform(*selected_segment["premium_affinity"]), 2),
            "price_sensitivity": round(random.uniform(*selected_segment["price_sensitivity"]), 2),
            "brand_affinity": round(random.uniform(*selected_segment["brand_affinity"]), 2),
            "abandon_probability": round(random.uniform(*selected_segment["abandon_probability"]), 2)
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(customers, f, indent=4)

    print(f"Generated {len(customers)} customers in: {output_path}")

    segment_counts = Counter(customer["segment"] for customer in customers)
    for segment, count in sorted(segment_counts.items()):
        print(f"  {segment}: {count}")

    return output_path