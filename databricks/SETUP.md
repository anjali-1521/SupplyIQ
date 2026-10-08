# Running SupplyIQ on Databricks Free Edition

This runs `supplyiq_lakehouse.py` on Databricks Free Edition. It needs no cluster setup because Free Edition uses serverless compute and Unity Catalog.
Button names can change slightly between releases, so follow the intent if a label looks different.

## 1. Create a Databricks account
1. Go to the Databricks Free Edition sign-up page (search "Databricks Free Edition").
2. Sign up with your email or Google account. No credit card is needed.
3. When the workspace opens you land on the home page. Your catalog is called `workspace` and it already has a schema called `default`.

## 2. Create a Volume and upload the dataset
A Volume is a folder in Unity Catalog where raw files live.

1. In the left sidebar, click **Catalog**.
2. Open `workspace` > `default`.
3. Click **Create** > **Volume**. Name it exactly `supplyiq`, keep it as a managed volume, and click **Create**.
4. Open the `supplyiq` volume and click **Upload to this volume**.
5. Upload `data/raw/DataCoSupplyChainDataset.csv` from this repo (the original Kaggle file, not the processed ones).
6. The file path is now `/Volumes/workspace/default/supplyiq/DataCoSupplyChainDataset.csv`. This is the path in the notebook's config cell.

## 3. Import the notebook
1. Click **Workspace** in the left sidebar.
2. Click the **...** menu (or **Create**) > **Import**.
3. Choose **File**, and select `databricks/supplyiq_lakehouse.py` from this repo.
4. Click **Import**. It opens as a notebook with the cells already separated.

## 4. Run it
1. At the top of the notebook, make sure the compute dropdown says **Serverless**. Click **Connect** if it is not connected.
2. Click **Run all**.
3. The Python cells take a few minutes. The SQL cells show result tables.
4. When it finishes you should see these tables under **Catalog** > `workspace` > `default`:
   * `bronze_supply_chain`
   * `silver_orders` and the six relational tables (`silver_categories`, `silver_products`, `silver_customers`, `silver_order_headers`, `silver_order_items`, `silver_shipments`)
   * `gold_shipping_risk`, `gold_monthly_revenue_by_market`, `gold_category_profitability`

If a cell fails, read the error, fix the cause (see the checklist at the end of this file), and use **Run all** again. Every write replaces the table, so re-running is safe.

## 5. Optional: build an AI/BI dashboard from the gold tables
1. Click **Dashboards** in the left sidebar > **Create dashboard**.
2. On the **Data** tab, add the three gold tables as datasets (**Add data** > choose the table from the catalog).
3. On the **Canvas** tab, add visualizations. Some ideas that match the project:
   * `gold_shipping_risk`: bar chart of `late_rate_pct` by `shipping_mode`
   * `gold_monthly_revenue_by_market`: line chart of `revenue` by `order_month`, one line per `market`
   * `gold_category_profitability`: bar chart of `profit` or `profit_margin_pct` by `category_name`
4. Click **Publish**.

## 6. Optional: ask questions with Genie
1. Click **Genie** in the left sidebar > **New**.
2. Add the table `workspace.default.silver_orders` as the data source.
3. Ask questions in plain English, for example "Which shipping mode has the highest late delivery rate?".
4. Use the "Show generated code" option to read the SQL Genie wrote. Compare it with the queries in the notebook.

`silver_orders` is the best table for Genie because it is one flat table with the personal columns already removed.

## Checklist if something fails
* **Path not found**: the Volume must be named `supplyiq` and sit in `workspace.default`, or change `CATALOG`, `SCHEMA` and `DATASET_FILE` in the config cell.
* **Garbled characters in text columns**: the CSV is read as `ISO-8859-1`. Do not re-save the file as UTF-8 before uploading.
* **Cast or date parse error**: serverless runs with strict (ANSI) SQL, so a value that cannot be cast stops the cell instead of becoming null. The error names the column.
* **Table already exists with a different schema**: the notebook uses `overwriteSchema`, so re-running replaces it. If you created a table with the same name by hand, drop it first.
