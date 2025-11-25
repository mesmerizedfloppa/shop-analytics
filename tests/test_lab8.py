import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
import asyncio
from core.async_ops import (
    sales_by_day_async,
    sales_by_user_async,
    product_performance_async,
    customer_segmentation_async,
    batch_process_orders,
    run_async_pipeline,
)
from core.domain import Order, Product, User


@pytest.fixture
def sample_orders():
    return [
        Order(
            id="o1",
            user_id="u1",
            items=(("p1", 2),),
            total=10000,
            ts="2025-06-22T10:00:00",
            status="paid",
        ),
        Order(
            id="o2",
            user_id="u2",
            items=(("p2", 1),),
            total=20000,
            ts="2025-06-22T11:00:00",
            status="paid",
        ),
        Order(
            id="o3",
            user_id="u1",
            items=(("p1", 1),),
            total=5000,
            ts="2025-06-23T09:00:00",
            status="paid",
        ),
    ]


@pytest.fixture
def sample_products():
    return [
        Product(
            id="p1", title="Phone", price=5000, category_id="c1", tags=("tech",)
        ),
        Product(
            id="p2", title="Laptop", price=20000, category_id="c1", tags=("tech",)
        ),
    ]


@pytest.fixture
def sample_users():
    return [
        User(id="u1", name="Alice", tier="regular"),
        User(id="u2", name="Bob", tier="VIP"),
    ]


@pytest.mark.asyncio
async def test_sales_by_day_async(sample_orders):
    """Тест асинхронного подсчёта продаж по дням"""
    days = ["2025-06-22", "2025-06-23"]
    result = await sales_by_day_async(sample_orders, days)

    assert isinstance(result, dict)
    assert result["2025-06-22"] == 30000
    assert result["2025-06-23"] == 5000


@pytest.mark.asyncio
async def test_sales_by_user_async(sample_orders):
    """Тест асинхронного подсчёта продаж по пользователям"""
    user_ids = ["u1", "u2"]
    result = await sales_by_user_async(sample_orders, user_ids)

    assert result["u1"] == 15000
    assert result["u2"] == 20000


@pytest.mark.asyncio
async def test_product_performance_async(sample_orders, sample_products):
    """Тест асинхронного анализа производительности товаров"""
    result = await product_performance_async(sample_orders, sample_products)

    assert len(result) == 2
    assert result[0]["product_id"] == "p2"  # Самая большая выручка
    assert result[0]["revenue"] == 20000


@pytest.mark.asyncio
async def test_customer_segmentation_async(sample_orders, sample_users):
    """Тест асинхронной сегментации клиентов"""
    result = await customer_segmentation_async(sample_orders, sample_users)

    assert isinstance(result, dict)
    assert "regular" in result or "one_time" in result


@pytest.mark.asyncio
async def test_batch_process_orders(sample_orders):
    """Тест пакетной обработки заказов"""
    result = await batch_process_orders(sample_orders, batch_size=2)

    assert result["total_orders"] == 3
    assert result["paid_orders"] == 3
    assert result["total_revenue"] == 35000


def test_run_async_pipeline_sync(sample_orders, sample_products, sample_users):
    """Тест синхронной обёртки для полного пайплайна"""
    result = run_async_pipeline(sample_orders, sample_products, sample_users)

    assert "sales_by_day" in result
    assert "top_products" in result
    assert "customer_segments" in result
    assert result["analysis_complete"] is True