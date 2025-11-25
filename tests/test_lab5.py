import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.domain import Order
from core.lazy import iter_orders_by_day, lazy_top_customers

orders = (
    Order(
        id="o1",
        user_id="u1",
        items=(),
        total=1000,
        ts="2025-06-22T10:00:00",
        status="paid",
    ),
    Order(
        id="o2",
        user_id="u1",
        items=(),
        total=2000,
        ts="2025-06-23T09:00:00",
        status="paid",
    ),
    Order(
        id="o3",
        user_id="u2",
        items=(),
        total=3000,
        ts="2025-06-22T15:00:00",
        status="paid",
    ),
)


def test_iter_orders_by_day():
    result = list(iter_orders_by_day(orders, "2025-06-22"))
    assert len(result) == 2
    assert all(o.ts.startswith("2025-06-22") for o in result)


def test_lazy_top_customers_ordering():
    top = list(lazy_top_customers(orders, k=2))
    assert top[0][0] == "u1"  # самый большой total
    assert len(top) == 2


def test_lazy_top_customers_yield_behavior():
    gen = lazy_top_customers(orders, k=1)
    assert hasattr(gen, "__iter__")
    assert hasattr(gen, "__next__") or hasattr(gen, "__anext__")


def test_iter_orders_by_day_empty():
    result = list(iter_orders_by_day(orders, "2025-01-01"))
    assert result == []


def test_lazy_top_customers_total_sum():
    top = dict(lazy_top_customers(orders, k=10))
    assert top["u1"] == 3000
    assert top["u2"] == 3000
