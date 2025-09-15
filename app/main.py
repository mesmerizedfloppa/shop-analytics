import sys
import os
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.transforms import load_seed, total_sales  # noqa: E402


@st.cache_data
def get_data():
    return load_seed("data/seed.json")


def main():
    st.set_page_config(page_title="Shop Analytics", layout="centered")
    st.title("📊 Shop Analytics — Overview")

    categories, products, users, orders = get_data()

    st.subheader("Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("# Users", f"{len(users):,}")
    col2.metric("# Products", f"{len(products):,}")
    col3.metric("# Orders", f"{len(orders):,}")
    sales_value = total_sales(orders) // 100
    formatted_sales = f"{sales_value:,}".replace(",", " ")
    col4.metric("Total Sales", f"{formatted_sales} kzt")


if __name__ == "__main__":
    main()
