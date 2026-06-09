from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    to_timestamp,
    window,
    count,
    max as spark_max
)


_spark = None


def get_spark_session():
    global _spark

    if _spark is None:
        _spark = (
            SparkSession.builder
            .appName("DashboardAnalytics")
            .master("local[*]")
            .getOrCreate()
        )

        _spark.sparkContext.setLogLevel("WARN")

    return _spark


def get_peak_session_starts(events_df, window_minutes, slide_minutes=1):
    if events_df.empty:
        return None

    required_columns = {
        "event_type",
        "event_time",
        "session_id"
    }

    if not required_columns.issubset(events_df.columns):
        return None

    df = events_df.copy()

    df = df[
        df["event_type"] == "session_start"
    ]

    if df.empty:
        return None

    spark = get_spark_session()

    spark_df = spark.createDataFrame(df)

    spark_df = spark_df.withColumn(
        "event_time",
        to_timestamp(col("event_time"))
    )

    peak_df = (
        spark_df
        .groupBy(
            window(
                col("event_time"),
                f"{window_minutes} minutes",
                f"{slide_minutes} minutes"
            )
        )
        .agg(
            count("*").alias("session_starts")
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("session_starts")
        )
        .orderBy(
            col("session_starts").desc(),
            col("window_start").asc()
        )
        .limit(1)
    )

    rows = peak_df.collect()

    if not rows:
        return None

    row = rows[0]

    return {
        "window_start": row["window_start"],
        "window_end": row["window_end"],
        "session_starts": int(row["session_starts"])
    }


def get_peak_active_sessions(active_sessions_df, window_minutes, slide_minutes=1):
    if active_sessions_df.empty:
        return None

    required_columns = {
        "event_time",
        "active_sessions"
    }

    if not required_columns.issubset(active_sessions_df.columns):
        return None

    spark = get_spark_session()

    spark_df = spark.createDataFrame(
        active_sessions_df.copy()
    )

    spark_df = spark_df.withColumn(
        "event_time",
        to_timestamp(col("event_time"))
    )

    peak_df = (
        spark_df
        .groupBy(
            window(
                col("event_time"),
                f"{window_minutes} minutes",
                f"{slide_minutes} minutes"
            )
        )
        .agg(
            spark_max("active_sessions").alias("peak_active_sessions")
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("peak_active_sessions")
        )
        .orderBy(
            col("peak_active_sessions").desc(),
            col("window_start").asc()
        )
        .limit(1)
    )

    rows = peak_df.collect()

    if not rows:
        return None

    row = rows[0]

    return {
        "window_start": row["window_start"],
        "window_end": row["window_end"],
        "active_sessions": int(row["peak_active_sessions"])
    }