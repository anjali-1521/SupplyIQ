# SupplyIQ — Model Evaluation Report

**Task:** Binary classification — predict `Late_delivery_risk` (1 = late, 0 = on-time) using only information known at order time (before dispatch).

**Dataset:** 180,519 order line items. 80/20 stratified train/test split (144,415 train / 36,104 test).

**Features used:** Shipping Mode, Order Region, Market, Category Name (one-hot encoded), Order Item Discount Rate, Order Item Quantity, order month, order weekday.

---

## Model comparison

| Model | Accuracy | Precision (late) | Recall (late) | F1 (late) | ROC-AUC |
|---|---|---|---|---|---|
| Logistic Regression (baseline) | 0.70 | 0.85 | 0.54 | 0.66 | 0.7296 |
| **Random Forest (final)** | **0.69** | **0.80** | **0.59** | **0.68** | **0.7348** |
| Random Forest (class_weight='balanced') | 0.70 | 0.83 | 0.57 | 0.68 | 0.7347 |

**Selected model: Random Forest (unweighted).** It has the best ROC-AUC of the three and the best recall on the late-delivery class among the non-tuned options, which matters operationally — missing an actual late shipment is generally costlier than a false alarm.

**Note on class weighting:** `class_weight='balanced'` was tested to try to improve recall on the late class further. It produced virtually no change in ROC-AUC (0.7347 vs. 0.7348) and slightly *reduced* recall on the late class (57% vs. 59%) while improving precision. Net effect was a wash, so the unweighted model was kept as final rather than adding complexity for no measurable gain.

---

## Feature importance

The model's top predictors, by importance:

| Feature | Importance (approx.) |
|---|---|
| Shipping Mode: Standard Class | ~0.68 |
| Shipping Mode: Second Class | ~0.15 |
| Shipping Mode: Same Day | ~0.06 |
| Order Item Discount Rate | ~0.03 |
| order_weekday | ~0.02 |
| order_month | ~0.02 |
| Order Item Quantity | ~0.01 |
| All category/region dummy variables (70+ features) | negligible individually |

**The three shipping-mode dummy variables together account for roughly 90% of total feature importance.** This independently confirms the finding from the SQL analysis layer (`docs/findings.md`): late delivery risk in this dataset is overwhelmingly explained by shipping mode, not by region, product category, customer segment, or discounting. Two separate analytical approaches — SQL aggregation and a trained classifier — converged on the same conclusion, which is a strong validation of the finding rather than an artifact of one method.

---

## Interpretation & limitations

- **Why this isn't "too easy":** despite shipping mode's dominance, ROC-AUC tops out at ~0.735, not near-perfect. Shipping mode is a strong signal but not deterministic — plenty of Standard Class orders still arrive late and plenty of First Class orders arrive on time, so the model has genuine predictive work to do beyond just reading off one column.
- **No target leakage:** all features used (shipping mode, region, market, category, discount, order timing) are known at the moment an order is placed, before the shipment is dispatched — so this model reflects a realistic "flag this order as high-risk before it ships" use case, not a model that's cheating by using post-hoc shipping information.
- **Recall ceiling:** at 59% recall on the late class, the model would still miss roughly 4 in 10 late deliveries if deployed as-is. Future improvement paths: gradient boosting (XGBoost/LightGBM), hyperparameter tuning via grid search, or probability threshold tuning (lowering the classification threshold below 0.5 to trade some precision for higher recall, which may be the right call operationally).

## Business framing

Given that shipping mode alone drives ~90% of late-delivery risk, the highest-leverage operational fix identified by this project isn't a smarter model — it's revisiting the **scheduled delivery windows for Standard and Second Class shipping**, which appear to be set unrealistically tight relative to what's operationally achievable. The model's value is in flagging individual high-risk orders in the meantime, while that structural fix is addressed.