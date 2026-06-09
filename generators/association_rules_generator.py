import json
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules
import os
from pathlib import Path


base_dir = Path.cwd()
data_path = os.path.join(base_dir, "data")

def generate_association_rules(transactions_path, output_path, min_support=0.20, min_confidence=0.70, min_conviction=2.50):

    with open(transactions_path, "r", encoding="utf-8") as f:
        transactions = json.load(f)

    baskets = [transaction["basket"] for transaction in transactions]

    te = TransactionEncoder()
    encoded_transactions = te.fit(baskets).transform(baskets)
    df_encoded_transactions = pd.DataFrame(encoded_transactions, columns=te.columns_)

    frequent_itemsets = fpgrowth(
        df_encoded_transactions,
        min_support=min_support,
        use_colnames=True
    )

    rules = association_rules(
        frequent_itemsets,
        metric="confidence",
        min_threshold=min_confidence
    )

    rules = rules[
        (rules["confidence"] < 1)
        & (rules["conviction"] >= min_conviction)
        & (rules["antecedents"].apply(len) <= 3)
        & (rules["consequents"].apply(len) == 1)
    ].copy()

    rules["antecedents"] = rules["antecedents"].apply(lambda x: sorted(list(x)))
    rules["consequents"] = rules["consequents"].apply(lambda x: sorted(list(x)))
    rules = rules.sort_values(by=["confidence", "lift"], ascending=False)

    rules_export = rules[
        [
            "antecedents",
            "consequents",
            "support",
            "confidence",
            "lift"
        ]
    ]

    output_path = os.path.join(data_path, output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    rules_export.to_json(output_path, orient="records", indent=4)

    print(f"Generated {len(rules_export)} association rules in {output_path}")

    for _, rule in rules_export.iterrows():
        print(
            f"{rule['antecedents']} => {rule['consequents']} | "
            f"support={rule['support']:.3f}, "
            f"confidence={rule['confidence']:.3f}, "
            f"lift={rule['lift']:.3f}"
        )

    return output_path