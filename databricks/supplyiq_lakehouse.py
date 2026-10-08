# Databricks notebook source
# MAGIC %md
# MAGIC # SupplyIQ: Lakehouse Version (Databricks)
# MAGIC
# MAGIC Same project as the MySQL version, rebuilt as a **medallion architecture** on Delta Lake.
# MAGIC
# MAGIC | Layer | What it holds | Tables |
# MAGIC |---|---|---|
# MAGIC | **Bronze** | Raw CSV, untouched except column names made snake_case | `bronze_supply_chain` |
# MAGIC | **Silver** | Cleaned and typed data: a flat table plus the 6-table relational model | `silver_orders`, `silver_categories`, `silver_products`, `silver_customers`, `silver_order_headers`, `silver_order_items`, `silver_shipments` |
# MAGIC | **Gold** | Small aggregate tables ready for dashboards | `gold_shipping_risk`, `gold_monthly_revenue_by_market`, `gold_category_profitability` |
# MAGIC
# MAGIC Every table is a **Delta table**, so we get ACID writes, schema enforcement and time travel (see the last cell).
# MAGIC
# MAGIC **Data quality rule carried over from the MySQL version:** revenue analysis only uses orders before `DATA_CUTOFF` (the pricing anomaly in the last months of the dataset). Late-delivery analysis uses all rows.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Config

# COMMAND ----------

CATALOG = "workspace"
SCHEMA = "default"
DATASET_FILE = "DataCoSupplyChainDataset.csv"
CSV_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/supplyiq/{DATASET_FILE}"

# Orders on or after this date are excluded from REVENUE analysis (pricing anomaly in the source data).
# Same value as the filter in notebooks/01_Data_Cleaning_EDA.ipynb: order date < '2017-11-01'
DATA_CUTOFF = "2017-11-01"

import re
from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")


def save_table(df, name):
    """Write a DataFrame as a managed Delta table, replacing it if it already exists."""
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(name)
    print(f"saved {name}: {spark.table(name).count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Bronze: raw CSV to Delta
# MAGIC Everything is read as strings on purpose. Bronze keeps the data as it arrived; typing happens in silver.
# MAGIC Delta does not allow spaces or brackets in column names, so we convert them to snake_case here.

# COMMAND ----------

raw = (
    spark.read
    .option("header", True)
    .option("encoding", "ISO-8859-1")  # same as encoding='latin1' in pandas
    .option("escape", '"')             # the CSV escapes quotes by doubling them
    .csv(CSV_PATH)
)


def to_snake_case(name):
    # "Days for shipping (real)" -> "days_for_shipping_real"
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


bronze = raw.toDF(*[to_snake_case(c) for c in raw.columns])

save_table(bronze, "bronze_supply_chain")
print(len(bronze.columns), "columns")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Silver: clean and type the data
# MAGIC Mirrors the cleaning in `notebooks/01_Data_Cleaning_EDA.ipynb`:
# MAGIC drop junk columns, fill nulls, parse dates, dedupe. Then add `delay_days`.

# COMMAND ----------

bronze = spark.table("bronze_supply_chain")

# 1. Drop junk columns.
#    product_description is 100% empty (your notebook drops it too).
#    product_image and customer_password are never used by any table.
cleaned = bronze.drop("product_description", "product_image", "customer_password")

# 2. Cast text columns to real types (bronze has only strings).
INT_COLS = [
    "days_for_shipping_real", "days_for_shipment_scheduled", "late_delivery_risk",
    "category_id", "customer_id", "customer_zipcode", "department_id",
    "order_customer_id", "order_id", "order_item_cardprod_id", "order_item_id",
    "order_item_quantity", "product_card_id", "product_category_id", "product_status",
]
DOUBLE_COLS = [
    "benefit_per_order", "sales_per_customer", "latitude", "longitude",
    "order_item_discount", "order_item_discount_rate", "order_item_product_price",
    "order_item_profit_ratio", "sales", "order_item_total", "order_profit_per_order",
    "product_price",
]
for c in INT_COLS:
    cleaned = cleaned.withColumn(c, F.col(c).cast("int"))
for c in DOUBLE_COLS:
    cleaned = cleaned.withColumn(c, F.col(c).cast("double"))

# 3. Parse the two date columns (raw format looks like 1/31/2018 22:56) and give them shorter names.
cleaned = (
    cleaned
    .withColumn("order_date", F.to_timestamp("order_date_dateorders", "M/d/yyyy H:mm"))
    .withColumn("shipping_date", F.to_timestamp("shipping_date_dateorders", "M/d/yyyy H:mm"))
    .drop("order_date_dateorders", "shipping_date_dateorders")
)

# 4. Fill nulls the same way the pandas notebook does.
cleaned = cleaned.fillna({"order_zipcode": "UNKNOWN", "customer_lname": "UNKNOWN", "customer_zipcode": 0})

# 5. Remove exact duplicate rows.
rows_before = cleaned.count()
cleaned = cleaned.dropDuplicates()
print("rows before dedupe:", rows_before, "| after:", cleaned.count())

# 6. delay_days = actual shipping days minus scheduled days (same definition as Q8).
cleaned = cleaned.withColumn("delay_days", F.col("days_for_shipping_real") - F.col("days_for_shipment_scheduled"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2a. Flat silver table (one row per order item)
# MAGIC This is the table for dashboards and Genie, so we drop personal columns (names and street).
# MAGIC The email column is already masked in the source data.

# COMMAND ----------

PII_COLS = ["customer_fname", "customer_lname", "customer_email", "customer_street"]

silver_orders = cleaned.drop(*PII_COLS)
save_table(silver_orders, "silver_orders")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2b. Silver relational model (same 6 tables as the MySQL schema)
# MAGIC Built from `cleaned` (before the personal columns were dropped) so the shape matches `sql/01_schema_setup.sql`.
# MAGIC The orders table is called `silver_order_headers` because `silver_orders` is already the flat table.
# MAGIC Delta tables have no enforced foreign keys, so the relationships exist only in how the queries join.

# COMMAND ----------

silver_categories = (
    cleaned
    .select("category_id", "category_name", "department_id", "department_name")
    .dropDuplicates(["category_id"])
)

silver_products = (
    cleaned
    .select("product_card_id", "product_name", "product_price", "product_status", "category_id")
    .dropDuplicates(["product_card_id"])
)

silver_customers = (
    cleaned
    .selectExpr(
        "customer_id", "customer_fname AS first_name", "customer_lname AS last_name",
        "customer_email AS email", "customer_segment AS segment", "customer_city AS city",
        "customer_state AS state", "customer_street AS street", "customer_country AS country",
        "customer_zipcode AS zipcode",
    )
    .dropDuplicates(["customer_id"])
)

silver_order_headers = (
    cleaned
    .selectExpr(
        "order_id", "order_customer_id AS customer_id", "order_date", "order_status",
        "order_region", "order_state", "order_city", "order_country", "order_zipcode",
        "market", "`type` AS payment_type", "latitude", "longitude",
    )
    .dropDuplicates(["order_id"])
)

silver_order_items = cleaned.selectExpr(
    "order_item_id", "order_id", "order_item_cardprod_id AS product_card_id",
    "order_item_quantity AS quantity", "order_item_product_price AS product_price",
    "order_item_discount AS discount", "order_item_discount_rate AS discount_rate",
    "order_item_profit_ratio AS profit_ratio", "sales", "order_item_total",
    "order_profit_per_order AS profit_per_order", "benefit_per_order", "sales_per_customer",
)

silver_shipments = cleaned.select(
    "order_item_id", "shipping_date", "shipping_mode", "delivery_status",
    "days_for_shipping_real", "days_for_shipment_scheduled", "late_delivery_risk",
)

save_table(silver_categories, "silver_categories")
save_table(silver_products, "silver_products")
save_table(silver_customers, "silver_customers")
save_table(silver_order_headers, "silver_order_headers")
save_table(silver_order_items, "silver_order_items")
save_table(silver_shipments, "silver_shipments")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Data quality check: monthly volume
# MAGIC Order counts stay roughly flat while average line-item sales and revenue fall in the last months.
# MAGIC That means the drop is a pricing anomaly in the source data, not a real fall in demand.
# MAGIC This is why revenue analysis stops at `DATA_CUTOFF`.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     date_format(o.order_date, 'yyyy-MM') AS order_month,
# MAGIC     COUNT(DISTINCT o.order_id) AS total_orders,
# MAGIC     ROUND(AVG(oi.sales), 2) AS avg_line_item_sales,
# MAGIC     ROUND(SUM(oi.sales), 2) AS total_revenue
# MAGIC FROM silver_order_headers o
# MAGIC JOIN silver_order_items oi ON o.order_id = oi.order_id
# MAGIC GROUP BY 1
# MAGIC ORDER BY 1;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Business queries (ported from `sql/02_business_queries.sql`)
# MAGIC Same logic as MySQL. Syntax changes only where Spark SQL differs:
# MAGIC * table names point at the silver tables
# MAGIC * `HAVING` repeats `COUNT(*)` instead of using the alias
# MAGIC * `GROUP BY` uses column positions (`GROUP BY 1`) instead of aliases
# MAGIC * `DAYNAME()` becomes `date_format(..., 'EEEE')`

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Original Q1: Which shipping mode has the highest late-delivery rate, and by how much?
# MAGIC SELECT
# MAGIC     s.shipping_mode,
# MAGIC     COUNT(*) AS total_shipments,
# MAGIC     SUM(s.late_delivery_risk) AS late_shipments,
# MAGIC     ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
# MAGIC FROM silver_shipments s
# MAGIC GROUP BY s.shipping_mode
# MAGIC ORDER BY late_rate_pct DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Original Q2: Which regions/countries have the worst on-time delivery performance?
# MAGIC -- Spark change: HAVING repeats COUNT(*) instead of using the alias total_shipments
# MAGIC SELECT
# MAGIC     o.order_region,
# MAGIC     o.order_country,
# MAGIC     COUNT(*) AS total_shipments,
# MAGIC     SUM(s.late_delivery_risk) AS late_shipments,
# MAGIC     ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
# MAGIC FROM silver_order_items oi
# MAGIC JOIN silver_order_headers o ON oi.order_id = o.order_id
# MAGIC JOIN silver_shipments s ON oi.order_item_id = s.order_item_id
# MAGIC GROUP BY o.order_region, o.order_country
# MAGIC HAVING COUNT(*) >= 100          -- filter out tiny/noisy country counts
# MAGIC ORDER BY late_rate_pct DESC
# MAGIC LIMIT 15;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Original Q3: How does late delivery risk vary by product category?
# MAGIC SELECT
# MAGIC     c.category_name,
# MAGIC     COUNT(*) AS total_shipments,
# MAGIC     SUM(s.late_delivery_risk) AS late_shipments,
# MAGIC     ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
# MAGIC FROM silver_order_items oi
# MAGIC JOIN silver_products p ON oi.product_card_id = p.product_card_id
# MAGIC JOIN silver_categories c ON p.category_id = c.category_id
# MAGIC JOIN silver_shipments s ON oi.order_item_id = s.order_item_id
# MAGIC GROUP BY c.category_name
# MAGIC ORDER BY late_rate_pct DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Original Q4: Monthly/yearly order and revenue trend
# MAGIC -- Same as the original: this covers ALL months, including the anomalous last ones.
# MAGIC -- Spark change: GROUP BY 1, 2 (column positions) instead of aliases
# MAGIC SELECT
# MAGIC     YEAR(o.order_date) AS order_year,
# MAGIC     MONTH(o.order_date) AS order_month,
# MAGIC     COUNT(DISTINCT o.order_id) AS total_orders,
# MAGIC     ROUND(SUM(oi.sales), 2) AS total_revenue
# MAGIC FROM silver_order_headers o
# MAGIC JOIN silver_order_items oi ON o.order_id = oi.order_id
# MAGIC GROUP BY 1, 2
# MAGIC ORDER BY 1, 2;

# COMMAND ----------

# Original Q4, scoped to DATA_CUTOFF (what the Python revenue chart in the EDA notebook shows).
# This one is a Python cell so it can use the DATA_CUTOFF variable from the config cell.
display(spark.sql(f"""
    SELECT
        YEAR(o.order_date) AS order_year,
        MONTH(o.order_date) AS order_month,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(oi.sales), 2) AS total_revenue
    FROM silver_order_headers o
    JOIN silver_order_items oi ON o.order_id = oi.order_id
    WHERE o.order_date < '{DATA_CUTOFF}'
    GROUP BY 1, 2
    ORDER BY 1, 2
"""))

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Original Q5: Which customer segments generate the most profit vs. the most late-delivery complaints?
# MAGIC SELECT
# MAGIC     cu.segment,
# MAGIC     ROUND(SUM(oi.profit_per_order), 2) AS total_profit,
# MAGIC     COUNT(*) AS total_shipments,
# MAGIC     SUM(s.late_delivery_risk) AS late_shipments,
# MAGIC     ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
# MAGIC FROM silver_order_items oi
# MAGIC JOIN silver_order_headers o ON oi.order_id = o.order_id
# MAGIC JOIN silver_customers cu ON o.customer_id = cu.customer_id
# MAGIC JOIN silver_shipments s ON oi.order_item_id = s.order_item_id
# MAGIC GROUP BY cu.segment
# MAGIC ORDER BY total_profit DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Original Q6: Relationship between order quantity/discount and late delivery
# MAGIC -- Spark change: GROUP BY 1 (the CASE expression) instead of the alias discount_bucket
# MAGIC SELECT
# MAGIC     CASE
# MAGIC         WHEN oi.discount_rate = 0 THEN 'No Discount'
# MAGIC         WHEN oi.discount_rate <= 0.10 THEN 'Low (0-10%)'
# MAGIC         WHEN oi.discount_rate <= 0.20 THEN 'Medium (10-20%)'
# MAGIC         ELSE 'High (20%+)'
# MAGIC     END AS discount_bucket,
# MAGIC     COUNT(*) AS total_shipments,
# MAGIC     ROUND(AVG(oi.quantity), 2) AS avg_quantity,
# MAGIC     SUM(s.late_delivery_risk) AS late_shipments,
# MAGIC     ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
# MAGIC FROM silver_order_items oi
# MAGIC JOIN silver_shipments s ON oi.order_item_id = s.order_item_id
# MAGIC GROUP BY 1
# MAGIC ORDER BY late_rate_pct DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Original Q7: Which markets are most profitable vs. most operationally unreliable?
# MAGIC SELECT
# MAGIC     o.market,
# MAGIC     ROUND(SUM(oi.profit_per_order), 2) AS total_profit,
# MAGIC     COUNT(*) AS total_shipments,
# MAGIC     ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
# MAGIC FROM silver_order_items oi
# MAGIC JOIN silver_order_headers o ON oi.order_id = o.order_id
# MAGIC JOIN silver_shipments s ON oi.order_item_id = s.order_item_id
# MAGIC GROUP BY o.market
# MAGIC ORDER BY total_profit DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Original Q8: Average shipping delay (real days - scheduled days) by mode and region
# MAGIC SELECT
# MAGIC     s.shipping_mode,
# MAGIC     o.order_region,
# MAGIC     ROUND(AVG(s.days_for_shipping_real - s.days_for_shipment_scheduled), 2) AS avg_delay_days,
# MAGIC     COUNT(*) AS total_shipments
# MAGIC FROM silver_order_items oi
# MAGIC JOIN silver_order_headers o ON oi.order_id = o.order_id
# MAGIC JOIN silver_shipments s ON oi.order_item_id = s.order_item_id
# MAGIC GROUP BY s.shipping_mode, o.order_region
# MAGIC ORDER BY avg_delay_days DESC
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Original Q9: Which weekdays see the highest order volume?
# MAGIC -- Spark change: DAYNAME(order_date) becomes date_format(order_date, 'EEEE'); GROUP BY 1 instead of the alias
# MAGIC SELECT
# MAGIC     date_format(o.order_date, 'EEEE') AS order_weekday,
# MAGIC     COUNT(DISTINCT o.order_id) AS total_orders,
# MAGIC     ROUND(SUM(oi.sales), 2) AS total_revenue
# MAGIC FROM silver_order_headers o
# MAGIC JOIN silver_order_items oi ON o.order_id = oi.order_id
# MAGIC GROUP BY 1
# MAGIC ORDER BY total_orders DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Original Q10: Top 10 products by sales, and their individual late-delivery rates
# MAGIC SELECT
# MAGIC     p.product_name,
# MAGIC     ROUND(SUM(oi.sales), 2) AS total_sales,
# MAGIC     COUNT(*) AS total_shipments,
# MAGIC     ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
# MAGIC FROM silver_order_items oi
# MAGIC JOIN silver_products p ON oi.product_card_id = p.product_card_id
# MAGIC JOIN silver_shipments s ON oi.order_item_id = s.order_item_id
# MAGIC GROUP BY p.product_name
# MAGIC ORDER BY total_sales DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. PySpark window function: month-over-month revenue change
# MAGIC `lag()` looks at the previous row inside a window, so each month can be compared with the month before it.
# MAGIC Only months before `DATA_CUTOFF` are used, because of the pricing anomaly.

# COMMAND ----------

monthly_revenue = (
    spark.table("silver_orders")
    .where(F.col("order_date") < DATA_CUTOFF)
    .groupBy(F.date_format("order_date", "yyyy-MM").alias("order_month"))
    .agg(F.round(F.sum("sales"), 2).alias("revenue"))
)

by_month = Window.orderBy("order_month")  # one window over all months, in date order

monthly_revenue = (
    monthly_revenue
    .withColumn("prev_month_revenue", F.lag("revenue").over(by_month))
    .withColumn(
        "mom_change_pct",
        F.round((F.col("revenue") - F.col("prev_month_revenue")) / F.col("prev_month_revenue") * 100, 2),
    )
    .orderBy("order_month")
)
display(monthly_revenue)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Gold: aggregate tables for dashboards

# COMMAND ----------

silver_orders = spark.table("silver_orders")

# Shipping risk: uses ALL rows, because late delivery is not affected by the pricing anomaly.
gold_shipping_risk = (
    silver_orders
    .groupBy("shipping_mode", "market", "order_region")
    .agg(
        F.count("*").alias("total_shipments"),
        F.sum("late_delivery_risk").alias("late_shipments"),
        F.round(F.avg("late_delivery_risk") * 100, 2).alias("late_rate_pct"),
        F.round(F.avg("delay_days"), 2).alias("avg_delay_days"),
    )
)

# Monthly revenue by market: revenue, so it stops at DATA_CUTOFF.
gold_monthly_revenue_by_market = (
    silver_orders
    .where(F.col("order_date") < DATA_CUTOFF)
    .groupBy("market", F.date_format("order_date", "yyyy-MM").alias("order_month"))
    .agg(
        F.countDistinct("order_id").alias("total_orders"),
        F.round(F.sum("sales"), 2).alias("revenue"),
        F.round(F.sum("order_profit_per_order"), 2).alias("profit"),
    )
)

# Category profitability: money, so it also stops at DATA_CUTOFF.
gold_category_profitability = (
    silver_orders
    .where(F.col("order_date") < DATA_CUTOFF)
    .groupBy("category_name", "department_name")
    .agg(
        F.count("*").alias("line_items"),
        F.round(F.sum("sales"), 2).alias("revenue"),
        F.round(F.sum("order_profit_per_order"), 2).alias("profit"),
    )
    .withColumn("profit_margin_pct", F.round(F.col("profit") / F.col("revenue") * 100, 2))
)

save_table(gold_shipping_risk, "gold_shipping_risk")
save_table(gold_monthly_revenue_by_market, "gold_monthly_revenue_by_market")
save_table(gold_category_profitability, "gold_category_profitability")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Delta time travel
# MAGIC Every write to a Delta table is saved as a numbered version. We can list them and query an older one.

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE HISTORY silver_orders;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Version 0 is the first write of the table. If you re-run the notebook, newer versions appear above.
# MAGIC SELECT COUNT(*) AS rows_in_version_0 FROM silver_orders VERSION AS OF 0;
