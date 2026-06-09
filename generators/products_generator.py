import json
import random
import pandas as pd
import os
from pathlib import Path


base_dir = Path.cwd()
data_path = os.path.join(base_dir, "data")


with open(os.path.join(data_path, "base", "categories.json"), "r", encoding="utf-8") as f:
    categories = json.load(f)

with open(os.path.join(data_path, "base", "brands.json"), "r", encoding="utf-8") as f:
    brands = json.load(f)

with open(os.path.join(data_path, "base", "variants.json"), "r", encoding="utf-8") as f:
    variants = json.load(f)

def generate_products(n_products, seed = 42):

    random.seed(seed)

    products = []
    product_id = 1

    for category in categories:
        category_id = category["category_id"]
        category_name = category["category_name"]

        for _ in range(n_products):
            template = random.choice(category["product_types"])

            base_product = template["product_type"]
            base_price = template["base_price"]

            brand = random.choice(list(brands[category_name].keys()))
            brand_multiplier = brands[category_name][brand]

            variant = random.choices(
                population=list(variants.keys()),
                weights=[v["weight"] for v in variants.values()],
                k=1
            )[0]

            random_price_factor = random.uniform(0.70, 1.30)

            price = round(
                base_price
                * random_price_factor
                * brand_multiplier
                * variants[variant]["price_multiplier"],
                2
            )

            margin_pct = round(
                random.uniform(*variants[variant]["margin_range"]),
                2
            )

            products.append({
                "product_id": product_id,
                "category_id": category_id,
                "category_name": category_name,
                "base_product": base_product,
                "product_name": f"{brand} {base_product} {variant}",
                "brand": brand,
                "variant": variant,
                "price": price,
                "premium_level": variants[variant]["premium_score"],
                "base_popularity": round(random.uniform(0.05, 1.00), 2),
                "margin_pct": margin_pct
            })

            product_id += 1

    df_products = pd.DataFrame(products)

    output_path = os.path.join(data_path, "products.json")
    df_products.to_json(output_path, orient="records", indent=4)

    print(f"Generated {len(df_products)} products in {output_path}")

    return output_path
