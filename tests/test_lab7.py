import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.service import CatalogService, OrderService, AnalyticsService
from core.transforms import load_seed
from core.compose import compose, pipe

categories, products, users, orders = load_seed("data/seed.json")


def test_compose_and_pipe():
    def f(x):
        return x + 1

    def g(x):
        return x * 2

    assert compose(f, g)(3) == 7
    assert pipe(f, g)(3) == 8


def test_catalog_service():
    svc = CatalogService(categories, products)
    res = svc.products_by_category(categories[0].id)
    assert isinstance(res, tuple)


def test_order_service_by_day():
    svc = OrderService(orders)
    res = svc.orders_by_day("2025-10-21")
    assert all(o.ts.startswith("2025-10-21") for o in res)


def test_top_customers_lazy():
    svc = OrderService(orders)
    top = svc.top_customers(5)
    assert len(top) <= 5


def test_analytics_daily_report():
    cat = CatalogService(categories, products)
    ords = OrderService(orders)
    analytics = AnalyticsService(cat, ords)
    rep = analytics.daily_report("2025-10-21")
    assert "orders" in rep and "total_sales" in rep
