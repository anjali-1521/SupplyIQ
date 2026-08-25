"""
SupplyIQ Assistant — ask the supply chain MySQL database questions in plain English.

Run with:
    streamlit run app/app.py

Requires:
    - MySQL running locally with the SupplyIQ schema loaded (see sql/01_schema_setup.sql)
    - A free Gemini API key (see .env.example)
"""
import os

import streamlit as st
from dotenv import load_dotenv
from google import genai

from sqlalchemy.exc import SQLAlchemyError

from db import get_engine
from nl_sql import GeminiUnavailableError, UnsafeQueryError, answer_question

load_dotenv()

st.set_page_config(page_title="SupplyIQ Assistant", page_icon="🚚", layout="centered")

SAMPLE_QUESTIONS = [
    "Which shipping mode has the highest late delivery rate?",
    "What were total sales by month in 2017?",
    "Which product category has the worst on-time delivery performance?",
    "Which customer segment is most profitable?",
    "How does discount rate relate to late delivery risk?",
]


@st.cache_resource
def get_db_engine():
    return get_engine()


@st.cache_resource
def get_client() -> genai.Client:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("Set GOOGLE_API_KEY in your environment or a .env file to use the assistant.")
        st.stop()
    return genai.Client(api_key=api_key)


st.title("🚚 SupplyIQ Assistant")
st.caption(
    "Ask questions about 180K+ global orders in plain English. "
    "Gemini translates your question into SQL against the normalized SupplyIQ MySQL schema, "
    "runs it, and explains the result."
)

with st.sidebar:
    st.subheader("Try a sample question")
    for q in SAMPLE_QUESTIONS:
        if st.button(q, use_container_width=True):
            st.session_state["question_input"] = q

question = st.text_input(
    "Your question",
    key="question_input",
    placeholder="e.g. Which region has the worst late-delivery rate?",
)
ask = st.button("Ask", type="primary")

if ask and question.strip():
    client = get_client()
    with st.spinner("Thinking..."):
        try:
            engine = get_db_engine()
            result = answer_question(client, engine, question)
        except UnsafeQueryError as e:
            st.error(f"Blocked an unsafe query: {e}")
        except GeminiUnavailableError as e:
            st.warning(f"⏳ {e}")
        except SQLAlchemyError as e:
            st.error(
                f"Database error: {e}\n\n"
                "Make sure MySQL is running and the `supplyiq` schema is loaded "
                "(see sql/01_schema_setup.sql), and that your MYSQL_* env vars are correct."
            )
        except Exception as e:  # noqa: BLE001
            st.error(f"Something went wrong: {e}")
        else:
            st.markdown("### Answer")
            st.write(result.answer)

            with st.expander("Show generated SQL"):
                st.code(result.sql, language="sql")

            with st.expander(f"Show data ({len(result.dataframe)} rows)"):
                st.dataframe(result.dataframe, use_container_width=True)
elif ask:
    st.warning("Type a question first.")
