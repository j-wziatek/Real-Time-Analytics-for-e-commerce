# Real-Time Analytics E-commerce

This project demonstrates real-time processing of e-commerce events.
Simulated customer sessions are streamed through Apache Kafka, enriched
with product recommendations, stored in Redis, and presented in a
Streamlit dashboard.

## Architecture

```text
Data generators
      |
      v
producer.py
      |
      v
Kafka: raw_events
      |
      v
recommendations_engine.py
      |
      v
Kafka: enriched_events
      |
      v
consumer_clean.py
      |
      v
Kafka: final_events
      |
      v
dashboard/dashboard_consumer.py
      |
      v
Redis
      |
      v
Streamlit + Pandas + Spark
```

## Project structure

```text
rta_project/
|-- compose.yaml                          # Kafka, Redis, Jupyter, and dashboard
|-- Dockerfile                            # Python/PySpark image
|-- requirements.txt                      # Python dependencies
|-- main.ipynb                            # Demo data generation
|-- producer.py                           # Customer event simulator
|-- recommendations_engine.py             # Recommendation engine
|-- consumer_clean.py                     # Event normalization and finalization
|
|-- generators/
|   |-- base_data_generator.py            # Categories, brands, and variants
|   |-- products_generator.py             # Products
|   |-- customers_generator.py            # Customer profiles
|   |-- transactions_generator.py         # Historical transactions
|   `-- association_rules_generator.py    # Association rules
|
|-- dashboard/
|   |-- app.py                            # Streamlit interface
|   |-- dashboard_consumer.py             # Writes Kafka events to Redis
|   |-- functions.py                      # Aggregations and KPIs
|   |-- charts.py                         # Charts
|   `-- spark.py                          # Time-window analysis
|
`-- data/
    |-- base/                             # Base data
    |-- products.json
    |-- customers.json
    |-- historical_transactions.json
    |-- association_rules.json
    `-- debug/                            # Local event copies
```

## Event flow

1. `producer.py` generates `session_start`, `add_to_basket`, and
   `make_decision` events.
2. `recommendations_engine.py` enriches the basket with recommendations
   based on association rules and the customer profile.
3. `consumer_clean.py` simplifies the events and calculates the value and
   margin of the purchased basket.
4. `dashboard_consumer.py` stores final events and session state in Redis.
5. The dashboard retrieves data from Redis and displays sales, session,
   and recommendation statistics.

## Technologies

- Python 3.11
- Apache Kafka
- Redis
- Streamlit
- Pandas and PySpark
- Plotly and Matplotlib
- MLxtend FP-Growth

## Running the project

Start the infrastructure:

```bash
docker compose up --build
```

Available services:

- Jupyter: `http://localhost:8999`
- Dashboard: `http://localhost:8501`

Run the pipeline processes in the Jupyter environment or inside the project
container in the following order:

```bash
python dashboard/dashboard_consumer.py
python consumer_clean.py
python recommendations_engine.py
python producer.py
```

The `main.ipynb` notebook can be used to regenerate the input data.
