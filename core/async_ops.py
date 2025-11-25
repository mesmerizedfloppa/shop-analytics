import asyncio
from typing import List, Dict, Tuple
from functools import reduce
from .domain import Order, Product, User


# ============ Асинхронные агрегации ============


async def sales_by_day_async(orders: List[Order], days: List[str]) -> Dict[str, int]:
    """
    Асинхронно вычисляет продажи по списку дней
    Каждый день обрабатывается параллельно
    """

    async def calculate_day_sales(day: str) -> Tuple[str, int]:
        """Вычисляет продажи за один день"""
        await asyncio.sleep(0.01)

        day_orders = [o for o in orders if o.ts.startswith(day) and o.status == "paid"]
        total = reduce(lambda acc, o: acc + o.total, day_orders, 0)
        return (day, total)

    # Запускаем все дни параллельно
    tasks = [calculate_day_sales(day) for day in days]
    results = await asyncio.gather(*tasks)

    return dict(results)


async def sales_by_user_async(
    orders: List[Order], user_ids: List[str]
) -> Dict[str, int]:
    """
    Асинхронно вычисляет продажи по списку пользователей
    """

    async def calculate_user_sales(user_id: str) -> Tuple[str, int]:
        await asyncio.sleep(0.01)

        user_orders = [o for o in orders if o.user_id == user_id and o.status == "paid"]
        total = reduce(lambda acc, o: acc + o.total, user_orders, 0)
        return (user_id, total)

    tasks = [calculate_user_sales(uid) for uid in user_ids]
    results = await asyncio.gather(*tasks)

    return dict(results)


async def product_performance_async(
    orders: List[Order], products: List[Product]
) -> List[Dict]:
    """
    Асинхронно анализирует производительность каждого товара
    ИСПРАВЛЕНО: используем reduce вместо мутабельных переменных
    """

    async def analyze_product(product: Product) -> Dict:
        await asyncio.sleep(0.01)

        # Функция для агрегации продаж через reduce
        def accumulate_sales(acc: Tuple[int, int], order: Order) -> Tuple[int, int]:
            if order.status != "paid":
                return acc

            qty_sold, revenue = acc

            # Ищем товар в заказе
            item = next((item for item in order.items if item[0] == product.id), None)
            if item:
                pid, qty = item
                return (qty_sold + qty, revenue + product.price * qty)
            return acc

        qty_sold, revenue = reduce(accumulate_sales, orders, (0, 0))

        return {
            "product_id": product.id,
            "title": product.title,
            "price": product.price,
            "quantity_sold": qty_sold,
            "revenue": revenue,
            "roi": revenue / product.price if product.price > 0 else 0,
        }

    tasks = [analyze_product(p) for p in products]
    results = await asyncio.gather(*tasks)

    # Сортируем по выручке
    return sorted(results, key=lambda x: x["revenue"], reverse=True)


async def customer_segmentation_async(
    orders: List[Order], users: List[User]
) -> Dict[str, List[str]]:
    """
    Асинхронная сегментация клиентов по поведению
    VIP, Regular, One-time
    """

    async def segment_user(user: User) -> Tuple[str, str]:
        await asyncio.sleep(0.01)

        user_orders = [o for o in orders if o.user_id == user.id and o.status == "paid"]
        order_count = len(user_orders)
        total_spent = reduce(lambda acc, o: acc + o.total, user_orders, 0)

        # Логика сегментации
        if order_count == 0:
            segment = "inactive"
        elif order_count == 1:
            segment = "one_time"
        elif total_spent > 500000:  # > 5000 тенге
            segment = "vip"
        else:
            segment = "regular"

        return (segment, user.id)

    tasks = [segment_user(u) for u in users]
    results = await asyncio.gather(*tasks)

    # Группируем по сегментам (иммутабельно через reduce)
    def group_by_segment(acc: dict, item: Tuple[str, str]) -> dict:
        segment, user_id = item
        current_list = acc.get(segment, [])
        return {**acc, segment: current_list + [user_id]}

    return reduce(group_by_segment, results, {})


# ============ Параллельная обработка пакетами ============


async def batch_process_orders(
    orders: List[Order], batch_size: int = 10
) -> Dict[str, any]:
    """
    Обрабатывает заказы пакетами параллельно
    Возвращает агрегированную статистику
    """

    async def process_batch(batch: List[Order]) -> Dict:
        await asyncio.sleep(0.01)

        paid = [o for o in batch if o.status == "paid"]
        refunded = [o for o in batch if o.status == "refunded"]

        return {
            "total": len(batch),
            "paid": len(paid),
            "refunded": len(refunded),
            "revenue": reduce(lambda acc, o: acc + o.total, paid, 0),
        }

    # Разбиваем на батчи
    batches = [orders[i : i + batch_size] for i in range(0, len(orders), batch_size)]

    # Обрабатываем параллельно
    tasks = [process_batch(batch) for batch in batches]
    results = await asyncio.gather(*tasks)

    # Агрегируем результаты
    return {
        "total_orders": sum(r["total"] for r in results),
        "paid_orders": sum(r["paid"] for r in results),
        "refunded_orders": sum(r["refunded"] for r in results),
        "total_revenue": sum(r["revenue"] for r in results),
        "batches_processed": len(results),
    }


# ============ End-to-End Pipeline ============


async def comprehensive_analysis_pipeline(
    orders: List[Order], products: List[Product], users: List[User]
) -> Dict:
    """
    Полный аналитический пайплайн с параллельным выполнением
    Запускает все анализы одновременно
    """

    # Получаем уникальные дни из заказов
    days = sorted(set(o.ts[:10] for o in orders))[-7:]  # Последние 7 дней

    # Получаем ID пользователей
    user_ids = [u.id for u in users[:20]]  # Топ-20 для примера

    # Запускаем все анализы параллельно
    (
        sales_by_day,
        sales_by_user,
        product_perf,
        segments,
        batch_stats,
    ) = await asyncio.gather(
        sales_by_day_async(orders, days),
        sales_by_user_async(orders, user_ids),
        product_performance_async(orders, products[:30]),  # Топ-30 товаров
        customer_segmentation_async(orders, users),
        batch_process_orders(orders),
    )

    return {
        "sales_by_day": sales_by_day,
        "sales_by_user": sales_by_user,
        "top_products": product_perf[:10],
        "customer_segments": segments,
        "batch_statistics": batch_stats,
        "analysis_complete": True,
    }


# ============ Синхронные обёртки для совместимости ============


def run_async_sales_by_day(orders: List[Order], days: List[str]) -> Dict[str, int]:
    """Синхронная обёртка для использования в UI"""
    return asyncio.run(sales_by_day_async(orders, days))


def run_async_pipeline(
    orders: List[Order], products: List[Product], users: List[User]
) -> Dict:
    """Синхронная обёртка для полного пайплайна"""
    return asyncio.run(comprehensive_analysis_pipeline(orders, products, users))


# ============ Параллельная фильтрация с async ============


async def async_filter_orders(
    orders: List[Order], predicates: List[callable]
) -> List[List[Order]]:
    """
    Применяет несколько фильтров параллельно
    Возвращает список отфильтрованных результатов
    """

    async def apply_filter(predicate: callable) -> List[Order]:
        await asyncio.sleep(0.01)
        return [o for o in orders if predicate(o)]

    tasks = [apply_filter(pred) for pred in predicates]
    return await asyncio.gather(*tasks)
