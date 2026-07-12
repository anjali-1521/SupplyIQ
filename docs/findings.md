# SupplyIQ — Findings

Business insights from the SQL analysis layer (`sql/02_business_queries.sql`), run against the DataCo Smart Supply Chain dataset (180,519 order line items, Jan 2015–Jan 2018).

---

## 1. Shipping mode is the dominant driver of late delivery — not region, category, or discount

| Shipping Mode | Late Delivery Rate |
|---|---|
| First Class | **95.3%** |
| Second Class | 76.6% |
| Same Day | 45.7% |
| Standard Class | 38.1% |

This is the single strongest pattern in the dataset, and it's counterintuitive: **First Class shipping is almost 2.5x more likely to arrive late than Standard Class.** Every other dimension tested — order region, product category, customer segment, discount level, market — clusters tightly around a ~55% late-delivery baseline with only a few percentage points of spread. Shipping mode is the outlier by a wide margin.

**Interpretation:** this points to the *scheduled* delivery windows for First Class being set unrealistically tight relative to what's operationally achievable, rather than any regional, product, or customer-driven cause. A shipping-mode-level SLA/scheduling fix would likely have far more impact on on-time performance than any regional or category-level intervention.

## 2. Everything else is comparatively flat

- **Region/country** (Q2): late rates range 59–67% across the worst-performing countries — no dramatic outlier once shipping mode is controlled for.
- **Product category** (Q3): ranges 48–69%, but the bulk of categories cluster tightly around 55%.
- **Customer segment** (Q5): Consumer (54.8%), Corporate (54.7%), Home Office (55.1%) — essentially no difference.
- **Discount level** (Q6): No Discount (55.8%) vs. High 20%+ Discount (55.7%) — discounting has **no meaningful relationship** with late delivery, despite the intuitive assumption that heavily discounted/promotional orders might ship less reliably.
- **Market** (Q7): 54–55% across all five markets — flat.
- **Order weekday** (Q9): order volume is nearly identical every day of the week (9,367–9,430 orders), no weekend spike or midweek dip.
- **Top 10 products by sales** (Q10): every top product sits in a tight 50–55% late-delivery band regardless of price point or product type — a $6.9M gun safe and a $663K laptop have nearly the same late rate.

**Takeaway:** delivery risk in this dataset is not product-specific, not region-specific, and not driven by discounting. It's overwhelmingly explained by shipping mode.

## 3. Data quality note: pricing anomaly in the final months (Nov 2017–Jan 2018)

Monthly revenue trend (Q4) showed a sharp decline in the last three months of the dataset — order *counts* stayed roughly flat (~2,100/month) but revenue collapsed:

| Month | Orders | Avg. Line-Item Sales | Total Revenue |
|---|---|---|---|
| Oct 2017 | 2,101 | $476.27 | $1,073,994 |
| Nov 2017 | 2,055 | $305.07 | $626,914 |
| Dec 2017 | 2,124 | $237.25 | $503,911 |
| Jan 2018 | 2,123 | $156.22 | $331,650 |

Since order volume held steady while average sale value steadily declined, this is not a real demand drop — it's a pricing data anomaly in the source dataset's final months (a known quirk of this public dataset). **Decision:** revenue/sales-trend analysis is scoped to data through October 2017; late-delivery and shipping analysis uses the full dataset, since `late_delivery_risk` and `shipping_mode` are unaffected by the pricing issue. This distinction is called out explicitly rather than silently dropping data or reporting a misleading revenue decline.

## 4. Shipping delay patterns (Q8)

Average delay (actual days − scheduled days) for Second Class shipments runs consistently 1.9–2.2 days across nearly every region, reinforcing the Q1 finding: the delay is structural to the shipping mode's scheduling, not concentrated in any particular geography.

---

## Implications for the predictive model (Phase 4)

Given the above, the delivery-risk classification model should treat **shipping mode as the primary expected predictor**, with region, category, and discount included as secondary features to confirm (via feature importance) that they contribute comparatively little — which would validate what the SQL layer already shows.