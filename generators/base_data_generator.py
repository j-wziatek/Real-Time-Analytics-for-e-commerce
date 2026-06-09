import json
import os
from pathlib import Path


categories = [
    {"category_id": 1, "category_name": "electronics"},
    {"category_id": 2, "category_name": "home"},
    {"category_id": 3, "category_name": "beauty"},
    {"category_id": 4, "category_name": "grocery"},
    {"category_id": 5, "category_name": "sport"}
]


product_templates = {
    "electronics": [
        {"name": "Smartphone", "base_price": 2500},
        {"name": "Laptop", "base_price": 4500},
        {"name": "Tablet", "base_price": 1800},
        {"name": "Smartwatch", "base_price": 900},
        {"name": "Headphones", "base_price": 350},
        {"name": "Monitor", "base_price": 1200},
        {"name": "Keyboard", "base_price": 200},
        {"name": "Wireless Mouse", "base_price": 120},
    ],
    "home": [
        {"name": "Vacuum Cleaner", "base_price": 1200},
        {"name": "Air Humidifier", "base_price": 350},
        {"name": "Coffee Machine", "base_price": 900},
        {"name": "Microwave", "base_price": 700},
        {"name": "Desk Lamp", "base_price": 120},
        {"name": "Office Chair", "base_price": 800},
        {"name": "Wall Clock", "base_price": 80},
        {"name": "Storage Box", "base_price": 50},
    ],
    "beauty": [
        {"name": "Perfume", "base_price": 300},
        {"name": "Face Serum", "base_price": 120},
        {"name": "Face Cream", "base_price": 80},
        {"name": "Shampoo", "base_price": 30},
        {"name": "Conditioner", "base_price": 30},
        {"name": "Hair Mask", "base_price": 45},
        {"name": "Body Lotion", "base_price": 35},
        {"name": "Shower Gel", "base_price": 20},
    ],
    "grocery": [
        {"name": "Coffee Beans", "base_price": 45},
        {"name": "Tea", "base_price": 20},
        {"name": "Cereal", "base_price": 18},
        {"name": "Pasta", "base_price": 8},
        {"name": "Rice", "base_price": 10},
        {"name": "Olive Oil", "base_price": 35},
        {"name": "Cookies", "base_price": 12},
        {"name": "Chocolate", "base_price": 10},
    ],
    "sport": [
        {"name": "Running Shoes", "base_price": 400},
        {"name": "Fitness Band", "base_price": 250},
        {"name": "Dumbbells", "base_price": 180},
        {"name": "Yoga Mat", "base_price": 90},
        {"name": "Sports Backpack", "base_price": 220},
        {"name": "Water Bottle", "base_price": 40},
        {"name": "Jump Rope", "base_price": 30},
        {"name": "Protein Shaker", "base_price": 35},
    ]
}


variants = {
    "ValueForMoney": {
        "weight": 20,
        "price_multiplier": 0.75,
        "margin_range": (0.10, 0.30),
        "premium_score": 0.85
    },
    "Standard": {
        "weight": 50,
        "price_multiplier": 1.00,
        "margin_range": (0.20, 0.35),
        "premium_score": 1
    },
    "Plus": {
        "weight": 20,
        "price_multiplier": 1.25,
        "margin_range": (0.35, 0.45),
        "premium_score": 2
    },
    "Premium": {
        "weight": 10,
        "price_multiplier": 1.75,
        "margin_range": (0.50, 0.65),
        "premium_score": 4
    }
}


brands = {
    "electronics": {
        "TechNova": 1.20,
        "ElectroMax": 1.10,
        "SmartEdge": 1.00,
        "Voltix": 0.90,
        "Nexora": 0.80
    },
    "home": {
        "HomeNest": 1.20,
        "CasaLine": 1.10,
        "Comforto": 1.00,
        "UrbanHome": 0.90,
        "Domio": 0.80
    },
    "beauty": {
        "PureGlow": 1.20,
        "Belleza": 1.10,
        "Skinova": 1.00,
        "LumaCare": 0.90,
        "VelvetSkin": 0.80
    },
    "grocery": {
        "FreshFarm": 1.20,
        "DailyBite": 1.10,
        "Naturio": 1.00,
        "Foodly": 0.90,
        "GreenTaste": 0.80
    },
    "sport": {
        "FitCore": 1.20,
        "ActivePro": 1.10,
        "Sportiva": 1.00,
        "Runix": 0.90,
        "PowerMove": 0.80
    }
}

base_dir = Path.cwd()
data_path = os.path.join(base_dir, "data", "base")
os.makedirs(data_path, exist_ok=True)

categories_with_products = []

for category in categories:
    category_name = category["category_name"]

    categories_with_products.append({
        "category_id": category["category_id"],
        "category_name": category_name,
        "product_types": [
            {
                "product_type": product["name"],
                "base_price": product["base_price"]
            }
            for product in product_templates[category_name]
        ]
    })

with open(os.path.join(data_path, "categories.json"), "w", encoding="utf-8") as f:
    json.dump(categories_with_products, f, indent=4)

with open(os.path.join(data_path, "brands.json"), "w", encoding="utf-8") as f:
    json.dump(brands, f, indent=4)

with open(os.path.join(data_path, "variants.json"), "w", encoding="utf-8") as f:
    json.dump(variants, f, indent=4)