"""
SupplyIQ — Delivery Risk Prediction Model
Standalone training script (clean version of notebooks/03_Delivery_Risk_Model.ipynb)

Trains a Random Forest classifier to predict Late_delivery_risk using
shipping mode, region, market, category, discount, quantity, and order
timing features. Saves the trained model and prints an evaluation report.
"""

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

RAW_DATA_PATH = "../data/raw/DataCoSupplyChainDataset.csv"
MODEL_OUTPUT_PATH = "delivery_risk_rf_model.joblib"
RANDOM_STATE = 42


def load_and_clean_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="latin1")
    df = df.drop(columns=["Product Description"])
    df["Order Zipcode"] = df["Order Zipcode"].fillna("UNKNOWN")
    df["Customer Lname"] = df["Customer Lname"].fillna("UNKNOWN")
    df["Customer Zipcode"] = df["Customer Zipcode"].fillna(0)
    df["order date (DateOrders)"] = pd.to_datetime(df["order date (DateOrders)"])
    return df


def build_features(df: pd.DataFrame):
    model_df = df.copy()
    model_df["order_month"] = model_df["order date (DateOrders)"].dt.month
    model_df["order_weekday"] = model_df["order date (DateOrders)"].dt.dayofweek

    feature_cols = [
        "Shipping Mode", "Order Region", "Market", "Category Name",
        "Order Item Discount Rate", "Order Item Quantity",
        "order_month", "order_weekday",
    ]
    target_col = "Late_delivery_risk"

    X = model_df[feature_cols].copy()
    y = model_df[target_col].copy()

    categorical_cols = ["Shipping Mode", "Order Region", "Market", "Category Name"]
    X = pd.get_dummies(X, columns=categorical_cols, drop_first=True)

    return X, y


def evaluate(name: str, model, X_test, y_test) -> None:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    print(f"\n=== {name} ===")
    print(classification_report(y_test, y_pred))
    print("ROC-AUC:", roc_auc_score(y_test, y_proba))


def main():
    print("Loading and cleaning data...")
    df = load_and_clean_data(RAW_DATA_PATH)

    print("Building features...")
    X, y = build_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"Train shape: {X_train.shape}, Test shape: {X_test.shape}")

    # Baseline
    log_reg = LogisticRegression(max_iter=1000)
    log_reg.fit(X_train, y_train)
    evaluate("Logistic Regression (baseline)", log_reg, X_test, y_test)

    # Final model
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=12, random_state=RANDOM_STATE, n_jobs=-1
    )
    rf.fit(X_train, y_train)
    evaluate("Random Forest (final model)", rf, X_test, y_test)

    # Feature importance
    importances = (
        pd.Series(rf.feature_importances_, index=X.columns)
        .sort_values(ascending=False)
        .head(15)
    )
    print("\nTop 15 feature importances:")
    print(importances)

    # Save the final model
    joblib.dump(rf, MODEL_OUTPUT_PATH)
    print(f"\nModel saved to {MODEL_OUTPUT_PATH}")


if __name__ == "__main__":
    main()