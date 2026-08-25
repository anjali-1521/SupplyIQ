# 🚚 SupplyIQ: Supply Chain & Delivery Risk Analytics

An end-to-end supply chain analytics project analyzing 180K+ global orders — combining SQL business analysis, Python EDA, a machine learning delivery-risk classifier, and an interactive Tableau dashboard.

Unlike a typical descriptive-analytics portfolio project, SupplyIQ adds a genuine predictive layer: a Random Forest model that flags shipments at risk of arriving late *before they ship*, with results that independently validate the SQL findings.

---

## 📌 Project Overview

This project analyzes global supply chain and delivery performance to answer:

- Which shipping modes are most likely to result in late delivery, and by how much?
- Which regions and product categories have the worst on-time performance?
- Can we predict which orders are at risk of late delivery *before* they ship?
- What operational lever would have the biggest impact on delivery reliability?

---

## 🔑 Headline Finding

**Shipping mode is the dominant driver of late delivery — not region, category, customer segment, or discounting.**

| Shipping Mode | Late Delivery Rate |
|---|---|
| First Class | 95.3% |
| Second Class | 76.6% |
| Same Day | 45.7% |
| Standard Class | 38.1% |

Counterintuitively, **First Class shipping has a ~2.5x higher late-delivery rate than Standard Class** — pointing to unrealistic scheduled delivery windows for faster shipping tiers rather than any regional or product-driven cause.

This finding was reached two independent ways — SQL aggregation and a trained ML classifier's feature importances — and both converged on the same answer (see `docs/findings.md` and `model/model_evaluation_report.md`).

---

## 🛠️ Tech Stack

- **Python** — Pandas, NumPy (cleaning, feature engineering)
- **SQL (MySQL)** — normalized relational schema, business queries
- **Scikit-learn** — Logistic Regression baseline + Random Forest delivery-risk classifier
- **Matplotlib / Seaborn** — EDA visualizations
- **Tableau Public** — interactive dashboard
- **Google Gemini (free tier) + Streamlit** — natural-language SQL assistant
- **Git & GitHub** — version control

---

## 📂 Project Structure

```
SupplyIQ/
├── data/
│   ├── raw/                          # Original DataCo Smart Supply Chain dataset
│   └── processed/                    # Cleaned, normalized CSVs (6 relational tables)
├── sql/
│   ├── 01_schema_setup.sql           # MySQL schema, foreign keys, data load
│   └── 02_business_queries.sql       # 10 business analysis queries
├── notebooks/
│   ├── 01_Data_Cleaning_EDA.ipynb    # Cleaning + Python visualizations
│   └── 03_Delivery_Risk_Model.ipynb  # ML model development
├── model/
│   ├── train_model.py                # Standalone model training script
│   └── model_evaluation_report.md    # Model comparison, feature importance, limitations
├── app/
│   ├── app.py                        # Streamlit UI for the SupplyIQ Assistant
│   ├── nl_sql.py                     # Natural-language -> SQL generation, validation, execution
│   └── db.py                         # MySQL connection (SQLAlchemy engine from env vars)
├── tableau/
│   └── SupplyIQ_Dashboard.twbx
├── docs/
│   ├── findings.md                   # Full SQL-layer business findings
│   └── screenshots/                  # Chart exports, dashboard screenshot
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📊 Dataset

**DataCo Smart Supply Chain for Big Data Analysis** ([Kaggle](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis))

- ~180,000 orders, 53 columns, Jan 2015 – Jan 2018, global regions
- Includes a labeled `Late_delivery_risk` field, enabling genuine supervised classification rather than a synthetic target

---

## 🗄️ Database Design

Rather than querying a single flat CSV, the dataset was normalized into 6 relational tables — `customers`, `orders`, `order_items`, `products`, `categories`, `shipments` — with proper foreign keys, matching how a real operations database would be structured.

---

## 🧠 Predictive Model: Delivery Risk Classifier

- **Task:** predict `Late_delivery_risk` using only information known at order time (shipping mode, region, market, category, discount, order timing) — no target leakage
- **Models compared:** Logistic Regression (baseline) vs. Random Forest vs. class-weighted Random Forest
- **Final model:** Random Forest — ROC-AUC 0.735, 59% recall on late deliveries
- **Feature importance:** the three shipping-mode dummy variables account for ~90% of total model importance, independently confirming the SQL findings

Full write-up: [`model/model_evaluation_report.md`](model/model_evaluation_report.md)

---

## 🤖 SupplyIQ Assistant (Natural-Language SQL)

A Streamlit app that lets you ask questions about the supply chain in plain English — no SQL required.

- You type a question (e.g. *"Which region has the worst late-delivery rate?"*)
- **Gemini** (free-tier Google API) translates it into a SQL query grounded in the actual 6-table schema
- The query runs against the live **MySQL** `supplyiq` database (the same one set up in [`sql/01_schema_setup.sql`](sql/01_schema_setup.sql) — no separate copy of the data)
- Gemini summarizes the result in plain English, with the generated SQL and raw data available to inspect

Guardrails: only single `SELECT` statements are generated and executed — write/DDL/DCL keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, …) and multi-statement queries are rejected before anything touches the database. For extra safety in a shared environment, point `MYSQL_USER` at a dedicated MySQL account that only has `SELECT` privileges on `supplyiq`.

**Setup:**
1. Load the schema and data into MySQL (if you haven't already):
   ```bash
   mysql -u root -p < sql/01_schema_setup.sql
   ```
2. Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey) — no credit card required.
3. Install dependencies and configure:
   ```bash
   pip install -r requirements.txt
   cp .env.example .env   # add your GOOGLE_API_KEY and MySQL credentials
   ```
4. Run it:
   ```bash
   streamlit run app/app.py
   ```

---

## 📈 Interactive Dashboard

The Tableau dashboard includes:
- KPI summary tiles (total orders, total revenue, overall late-delivery rate, top shipping mode)
- Late delivery rate by shipping mode (headline chart)
- Late delivery rate by country (geographic map)
- Late delivery rate by category (top 15 by volume)

🔗 **[View the live dashboard on Tableau Public](https://public.tableau.com/app/profile/anjali.s5047/viz/SupplyIQSupplyChainDeliveryRiskDashboard/Dashboard1)**

---

## 📌 Key Business Insights

- Shipping mode explains the overwhelming majority of late-delivery variation — region, category, segment, and discounting are comparatively flat.
- First Class shipping is the least reliable mode by a wide margin, suggesting its scheduled delivery windows are unrealistic relative to actual fulfillment capacity.
- A data quality issue was identified in the final 3 months of the dataset (a pricing anomaly, not a real demand drop) — investigated, diagnosed, and explicitly scoped around in the revenue analysis rather than ignored.
- A Random Forest classifier independently rediscovered the same shipping-mode-driven pattern found via SQL, validating the finding through two separate analytical methods.

---

## 🚀 Skills Demonstrated

- Relational database design & SQL querying
- Business analytics & KPI definition
- Data quality investigation & root-cause reasoning
- Exploratory data analysis & visualization
- Supervised machine learning (classification, model comparison, feature importance)
- Dashboard design (Tableau)
- LLM application development (natural-language-to-SQL, prompt design, guardrails against unsafe generated queries)
- Git version control

---

## 👩‍💻 Author

Anjali
GitHub: [anjali-1521](https://github.com/anjali-1521)
