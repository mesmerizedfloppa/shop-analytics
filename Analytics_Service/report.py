from typing import Tuple, Dict, List
from functools import reduce
from core.domain import Order, Product, User


# ============ Отчёты по продажам ============


def sales_by_period(
    orders: Tuple[Order, ...], start_date: str, end_date: str
) -> Dict[str, int]:
    """
    Продажи за период по дням (иммутабельная агрегация через reduce)
    Возвращает: {date: total_sales}
    """
    period_orders = tuple(
        filter(
            lambda o: start_date <= o.ts[:10] <= end_date and o.status == "paid",
            orders,
        )
    )

    # Группируем по дням через reduce
    def accumulate_by_day(acc: dict, order: Order) -> dict:
        day = order.ts[:10]
        return {**acc, day: acc.get(day, 0) + order.total}

    return reduce(accumulate_by_day, period_orders, {})


def average_order_value(orders: Tuple[Order, ...]) -> float:
    """Средний чек (только paid заказы)"""
    paid_orders = tuple(filter(lambda o: o.status == "paid", orders))

    if not paid_orders:
        return 0.0

    total = reduce(lambda acc, o: acc + o.total, paid_orders, 0)
    return total / len(paid_orders)


def sales_summary(orders: Tuple[Order, ...]) -> dict:
    """Сводка по продажам"""
    paid = tuple(filter(lambda o: o.status == "paid", orders))
    refunded = tuple(filter(lambda o: o.status == "refunded", orders))
    cancelled = tuple(filter(lambda o: o.status == "cancelled", orders))

    total_paid = reduce(lambda acc, o: acc + o.total, paid, 0)
    total_refunded = reduce(lambda acc, o: acc + o.total, refunded, 0)

    return {
        "total_orders": len(orders),
        "paid_orders": len(paid),
        "refunded_orders": len(refunded),
        "cancelled_orders": len(cancelled),
        "total_revenue": total_paid,
        "total_refunded": total_refunded,
        "net_revenue": total_paid - total_refunded,
        "average_order_value": average_order_value(orders),
    }


# ============ Отчёты по товарам ============


def bestsellers_report(
    orders: Tuple[Order, ...], products: Tuple[Product, ...], k: int = 10
) -> List[dict]:
    """
    Топ-K бестселлеров с деталями (иммутабельная агрегация)
    """

    # Агрегируем количество через reduce
    def accumulate_product_qty(acc: dict, order: Order) -> dict:
        if order.status != "paid":
            return acc

        def add_item(inner_acc: dict, item: Tuple[str, int]) -> dict:
            pid, qty = item
            return {**inner_acc, pid: inner_acc.get(pid, 0) + qty}

        return reduce(add_item, order.items, acc)

    product_qty = reduce(accumulate_product_qty, orders, {})

    # Сортируем и берём топ-K
    top_ids = sorted(product_qty.keys(), key=product_qty.get, reverse=True)[:k]

    # Обогащаем данными о продуктах
    products_dict = {p.id: p for p in products}

    return [
        {
            "product_id": pid,
            "title": products_dict[pid].title if pid in products_dict else "Unknown",
            "price": products_dict[pid].price if pid in products_dict else 0,
            "quantity_sold": product_qty[pid],
            "revenue": (
                product_qty[pid] * products_dict[pid].price
                if pid in products_dict
                else 0
            ),
        }
        for pid in top_ids
        if pid in products_dict
    ]


def low_stock_alert(
    products: Tuple[Product, ...], orders: Tuple[Order, ...], threshold: int = 5
) -> List[dict]:
    """
    Товары, которые заканчиваются (иммутабельная агрегация)
    """
    recent_orders = orders[-20:] if len(orders) >= 20 else orders

    # Иммутабельная агрегация через reduce
    def accumulate_sales(acc: dict, order: Order) -> dict:
        if order.status != "paid":
            return acc

        def add_item(inner_acc: dict, item: Tuple[str, int]) -> dict:
            pid, qty = item
            return {**inner_acc, pid: inner_acc.get(pid, 0) + qty}

        return reduce(add_item, order.items, acc)

    recent_sales = reduce(accumulate_sales, recent_orders, {})

    return [
        {"product_id": pid, "recent_sales": qty}
        for pid, qty in recent_sales.items()
        if qty > threshold
    ]


# ============ Отчёты по пользователям ============


def customer_lifetime_value(orders: Tuple[Order, ...]) -> Dict[str, int]:
    """
    LTV по пользователям (иммутабельная агрегация)
    Возвращает: {user_id: total_spent}
    """

    def accumulate_user_totals(acc: dict, order: Order) -> dict:
        if order.status != "paid":
            return acc
        return {**acc, order.user_id: acc.get(order.user_id, 0) + order.total}

    return reduce(accumulate_user_totals, orders, {})


def top_customers_report(orders: Tuple[Order, ...], k: int = 10) -> List[dict]:
    """
    Топ-K покупателей по выручке
    """
    ltv = customer_lifetime_value(orders)
    top_users = sorted(ltv.items(), key=lambda x: x[1], reverse=True)[:k]

    # Считаем количество заказов (иммутабельно)
    def count_orders(acc: dict, order: Order) -> dict:
        if order.status != "paid":
            return acc
        return {**acc, order.user_id: acc.get(order.user_id, 0) + 1}

    order_counts = reduce(count_orders, orders, {})

    return [
        {
            "user_id": uid,
            "total_spent": total,
            "order_count": order_counts.get(uid, 0),
            "avg_order": (
                total // order_counts[uid] if order_counts.get(uid, 0) > 0 else 0
            ),
        }
        for uid, total in top_users
    ]


def retention_rate(orders: Tuple[Order, ...]) -> dict:
    """
    Процент пользователей с повторными покупками (иммутабельно)
    """

    def count_user_orders(acc: dict, order: Order) -> dict:
        if order.status != "paid":
            return acc
        return {**acc, order.user_id: acc.get(order.user_id, 0) + 1}

    user_orders = reduce(count_user_orders, orders, {})

    total_users = len(user_orders)
    repeat_users = sum(1 for count in user_orders.values() if count > 1)

    return {
        "total_customers": total_users,
        "repeat_customers": repeat_users,
        "retention_rate": (repeat_users / total_users * 100) if total_users > 0 else 0,
        "first_time_customers": total_users - repeat_users,
    }


# ============ Отчёты по корзинам (конверсия) ============


def cart_abandonment_rate(carts: Tuple, orders: Tuple[Order, ...]) -> dict:
    """
    Процент брошенных корзин
    """
    completed_orders = len(tuple(filter(lambda o: o.status == "paid", orders)))
    total_carts = len(carts) if carts else completed_orders

    abandonment = (
        ((total_carts - completed_orders) / total_carts * 100) if total_carts > 0 else 0
    )

    return {
        "total_carts": total_carts,
        "completed_orders": completed_orders,
        "abandonment_rate": round(abandonment, 2),
    }


# ============ Временные паттерны ============


def sales_by_hour(orders: Tuple[Order, ...]) -> Dict[int, int]:
    """
    Продажи по часам дня (иммутабельно)
    """

    def accumulate_hourly(acc: dict, order: Order) -> dict:
        if order.status != "paid":
            return acc
        try:
            hour = int(order.ts[11:13])
            return {**acc, hour: acc.get(hour, 0) + order.total}
        except (ValueError, IndexError):
            return acc

    hourly_sales = reduce(accumulate_hourly, orders, {})
    return dict(sorted(hourly_sales.items()))


def sales_by_weekday(orders: Tuple[Order, ...]) -> Dict[str, int]:
    """
    Продажи по дням недели (иммутабельно)
    """
    from datetime import datetime

    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def accumulate_weekday(acc: dict, order: Order) -> dict:
        if order.status != "paid":
            return acc
        try:
            dt = datetime.fromisoformat(order.ts)
            day_name = weekday_names[dt.weekday()]
            return {**acc, day_name: acc.get(day_name, 0) + order.total}
        except (ValueError, IndexError):
            return acc

    return reduce(accumulate_weekday, orders, {})


# ============ Композитный отчёт ============


def comprehensive_report(
    orders: Tuple[Order, ...], products: Tuple[Product, ...], users: Tuple[User, ...]
) -> dict:
    """
    Полный аналитический отчёт (композиция всех метрик)
    """
    return {
        "sales": sales_summary(orders),
        "bestsellers": bestsellers_report(orders, products, k=5),
        "top_customers": top_customers_report(orders, k=5),
        "retention": retention_rate(orders),
        "hourly_pattern": sales_by_hour(orders),
        "weekday_pattern": sales_by_weekday(orders),
    }
