import json
import random
import os
from pathlib import Path


base_dir = Path.cwd()
data_path = os.path.join(base_dir, "data")


with open(os.path.join(data_path, "base", "categories.json"), "r", encoding="utf-8") as f:
    categories = json.load(f)


association_rules_seed = [
    {"if": ["Laptop"], "then": ["Keyboard"], "probability": 0.45},
    {"if": ["Laptop", "Keyboard"], "then": ["Wireless Mouse"], "probability": 0.75},

    {"if": ["Smartphone"], "then": ["Power Bank"], "probability": 0.75},

    {"if": ["Coffee Beans"], "then": ["Chocolate"], "probability": 0.35},
    {"if": ["Coffee Beans", "Chocolate"], "then": ["Cookies"], "probability": 0.70},

    {"if": ["Shampoo"], "then": ["Conditioner"], "probability": 0.40},
    {"if": ["Shampoo", "Conditioner"], "then": ["Hair Mask"], "probability": 0.80},

    {"if": ["Running Shoes"], "then": ["Fitness Band"], "probability": 0.35},
    {"if": ["Running Shoes", "Fitness Band"], "then": ["Protein Shaker"], "probability": 0.75},

    {"if": ["Office Chair"], "then": ["Desk Lamp"], "probability": 0.45}
]


def generate_transactions(n_transactions, output_path, seed=42):

    output_path = os.path.join(data_path, output_path)

    random.seed(seed)

    def _generate_random_basket():
        basket = []

        n_categories = random.randint(2, min(5, len(categories)))

        selected_categories = random.sample(categories, k=n_categories)

        for category in selected_categories:
            product_types = [
                product["product_type"]
                for product in category["product_types"]
            ]

            n_products = random.randint(2, min(6, len(product_types)))

            basket.extend(random.sample(product_types, k=n_products))

        return list(set(basket))
    
    def _add_noise_products(basket, probability=0.25, max_products=3):
        basket_set = set(basket)

        if random.random() <= probability:
            all_product_types = [
                product["product_type"]
                for category in categories
                for product in category["product_types"]
            ]

            n_noise_products = random.randint(1, max_products)

            basket_set.update(random.sample(all_product_types, k=n_noise_products))

        return list(basket_set)

    def _apply_association_rules_seed(basket):
        basket_set = set(basket)

        for rule in association_rules_seed:
            if all(item in basket_set for item in rule["if"]):
                for item in rule["then"]:
                    if random.random() <= rule["probability"]:
                        basket_set.add(item)

        return list(basket_set)

    purchases = []

    for transaction_id in range(1, n_transactions + 1):
        basket = _generate_random_basket()
        basket = _apply_association_rules_seed(basket)
        basket = _add_noise_products(basket)

        purchases.append({
            "transaction_id": transaction_id,
            "basket": basket
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(purchases, f, indent=4)

    print(f"Generated {len(purchases)} historical transactions in {output_path}")

    return output_path