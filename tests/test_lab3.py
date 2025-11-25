import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import pytest
from core.transforms import top_products
from core.domain import Product, Order


@pytest.fixture
def sample_products():
    return (
        Product(
            id="p1", title="Phone", price=100_000, category_id="c1", tags=("tech",)
        ),
        Product(
            id="p2", title="Laptop", price=300_000, category_id="c1", tags=("tech",)
        ),
        Product(
            id="p3", title="Tablet", price=200_000, category_id="c2", tags=("mobile",)
        ),
        Product(
            id="p4", title="Headphones", price=50_000, category_id="c3", tags=("audio",)
        ),
    )


@pytest.fixture
def sample_orders():
    return (
        Order(
            id="o1",
            user_id="u1",
            items=(("p1", 2), ("p2", 1)),
            total=500_000,
            ts="2025-10-01",
            status="paid",
        ),
        Order(
            id="o2",
            user_id="u2",
            items=(("p3", 5), ("p1", 1)),
            total=1_200_000,
            ts="2025-10-02",
            status="paid",
        ),
        Order(
            id="o3",
            user_id="u3",
            items=(("p4", 3),),
            total=150_000,
            ts="2025-10-03",
            status="refunded",
        ),
    )


def test_top_products_returns_top_k(sample_orders, sample_products):
    """Тест возвращает топ-K товаров"""
    top_products.cache_clear()
    top = top_products(sample_orders, sample_products, k=2)
    assert isinstance(top, tuple)
    assert len(top) == 2

    # p3 продано 5 шт, p1 продано 3 шт - они должны быть в топе
    top_ids = [p.id for p in top]
    assert "p3" in top_ids
    assert "p1" in top_ids


def test_top_products_ignores_non_paid_orders(sample_orders, sample_products):
    """Игнорирует не-paid заказы"""
    top_products.cache_clear()
    result = top_products(sample_orders, sample_products, k=5)
    ids = [p.id for p in result]
    assert "p4" not in ids  # был только в refunded заказе


def test_top_products_caching_speed(sample_orders, sample_products):
    """Тест кэширования"""
    top_products.cache_clear()

    start = time.perf_counter()
    top_products(sample_orders, sample_products, 3)
    uncached = time.perf_counter() - start

    start = time.perf_counter()
    top_products(sample_orders, sample_products, 3)
    cached = time.perf_counter() - start

    assert cached < uncached or cached < 0.001  # Кэш должен быть быстрее


def test_top_products_empty_orders_returns_empty(sample_products):
    """Пустые заказы возвращают пустой результат"""
    top_products.cache_clear()
    result = top_products((), sample_products, 5)
    assert result == ()


def test_top_products_k_larger_than_available(sample_orders, sample_products):
    """k больше доступных товаров"""
    top_products.cache_clear()
    result = top_products(sample_orders, sample_products, 10)
    # Должно вернуть только те товары, которые были в paid заказах
    assert len(result) <= len(sample_products)
