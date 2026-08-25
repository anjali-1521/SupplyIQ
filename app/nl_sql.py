"""
Natural-language -> SQL assistant for the SupplyIQ MySQL database.

Takes a plain-English question, asks Gemini (free tier) to translate it into a
single read-only MySQL query grounded in the known schema, executes it against
MySQL, and asks Gemini to summarize the result in plain English.
"""
import re
from dataclasses import dataclass

import pandas as pd
from google import genai
from google.genai.errors import ServerError
from sqlalchemy.engine import Engine

MODEL = "gemini-3.5-flash-lite"

SCHEMA_DESCRIPTION = """
categories(category_id, category_name, department_id, department_name)
products(product_card_id, product_name, product_price, product_status, category_id)
customers(customer_id, first_name, last_name, email, segment, city, state, street, country, zipcode)
orders(order_id, customer_id, order_date, order_status, order_region, order_state, order_city, order_country, order_zipcode, market, payment_type, latitude, longitude)
order_items(order_item_id, order_id, product_card_id, quantity, product_price, discount, discount_rate, profit_ratio, sales, order_item_total, profit_per_order, benefit_per_order, sales_per_customer)
shipments(order_item_id, shipping_date, shipping_mode, delivery_status, days_for_shipping_real, days_for_shipment_scheduled, late_delivery_risk)

Relationships:
- orders.customer_id -> customers.customer_id
- order_items.order_id -> orders.order_id
- order_items.product_card_id -> products.product_card_id
- products.category_id -> categories.category_id
- shipments.order_item_id -> order_items.order_item_id

Notes:
- late_delivery_risk is 1 if the shipment was late, 0 otherwise.
- shipping_mode is one of: First Class, Second Class, Same Day, Standard Class.
- This is MySQL, so use MySQL date functions (YEAR(), MONTH(), DAYNAME(), etc.).
""".strip()

SQL_SYSTEM_PROMPT = f"""You are a SQL analyst for the SupplyIQ supply chain database (MySQL).

Schema:
{SCHEMA_DESCRIPTION}

Rules:
- Output ONLY a single MySQL SELECT statement. No prose, no markdown fences, no explanation.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or any statement that isn't a SELECT.
- Always add a LIMIT (200 max) unless the question clearly asks for an aggregate/single row.
- Use explicit JOINs based on the relationships above.
"""

ANSWER_SYSTEM_PROMPT = """You are a supply chain analyst explaining query results to a business stakeholder.
Given the user's question and the resulting data (as a small table), write a concise, plain-English answer
(2-5 sentences). Call out concrete numbers. Do not mention SQL or the word "query"."""

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|attach|detach|pragma|create|replace|grant|revoke)\b",
    re.IGNORECASE,
)


class UnsafeQueryError(Exception):
    pass


class GeminiUnavailableError(Exception):
    """Raised when Gemini's free tier is overloaded (the SDK already retries internally)."""


def _call_gemini(client: "genai.Client", **kwargs):
    try:
        return client.models.generate_content(**kwargs)
    except ServerError as e:
        raise GeminiUnavailableError(
            "Gemini's free tier is experiencing high demand right now. "
            "This is temporary — please try again in a minute."
        ) from e


@dataclass
class NLQueryResult:
    question: str
    sql: str
    dataframe: pd.DataFrame
    answer: str


def _extract_sql(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^```(sql)?", "", text.strip(), flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text.strip()).strip()
    return text


def _validate_sql(sql: str) -> None:
    if not sql.lower().lstrip().startswith("select"):
        raise UnsafeQueryError("Only SELECT statements are allowed.")
    if ";" in sql.strip().rstrip(";"):
        raise UnsafeQueryError("Only a single statement is allowed.")
    if _FORBIDDEN.search(sql):
        raise UnsafeQueryError("Query contains a disallowed keyword.")


def generate_sql(client: "genai.Client", question: str) -> str:
    resp = _call_gemini(
        client,
        model=MODEL,
        contents=question,
        config={"system_instruction": SQL_SYSTEM_PROMPT},
    )
    return _extract_sql(resp.text)


def run_sql(engine: Engine, sql: str) -> pd.DataFrame:
    _validate_sql(sql)
    with engine.connect() as conn:
        return pd.read_sql_query(sql, conn)


def summarize_result(client: "genai.Client", question: str, df: pd.DataFrame) -> str:
    table_preview = df.head(30).to_markdown(index=False) if not df.empty else "(no rows returned)"
    user_content = f"Question: {question}\n\nResult data:\n{table_preview}"
    resp = _call_gemini(
        client,
        model=MODEL,
        contents=user_content,
        config={"system_instruction": ANSWER_SYSTEM_PROMPT},
    )
    return resp.text


def answer_question(client: "genai.Client", engine: Engine, question: str) -> NLQueryResult:
    sql = generate_sql(client, question)
    df = run_sql(engine, sql)
    answer = summarize_result(client, question, df)
    return NLQueryResult(question=question, sql=sql, dataframe=df, answer=answer)
