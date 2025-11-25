from core.transforms import total_sales
from core.recursion import flatten_categories, collect_products_recursive
from core.lazy import iter_orders_by_day, lazy_top_customers
from core.compose import pipe, compose
from typing import Tuple
from core.domain import Category, Product, Order


class CatalogService:
    """
    Фасад для работы с каталогом
    Методы - композиции чистых функций
    """

    def __init__(
        self, categories: Tuple[Category, ...], products: Tuple[Product, ...]
    ):
        self.categories = categories
        self.products = products

    def products_by_category(self, root_id: str) -> Tuple[Product, ...]:
        """
        Возвращает все товары категории и её подкатегорий
        Композиция: flatten → collect
        """
        # ИСПРАВЛЕНО: правильная композиция без лишних lambda
        return collect_products_recursive(self.categories, self.products, root_id)

    def filter_products(self, predicate) -> Tuple[Product, ...]:
        """Фильтрует товары по предикату"""
        return tuple(filter(predicate, self.products))

    def get_category_tree(self, root_id: str) -> Tuple[Category, ...]:
        """Возвращает дерево категорий от корня"""
        return flatten_categories(self.categories, root_id)


class OrderService:
    """
    Фасад для работы с заказами
    Использует ленивые вычисления
    """

    def __init__(self, orders: Tuple[Order, ...]):
        self.orders = orders

    def orders_by_day(self, day: str) -> Tuple[Order, ...]:
        """Заказы за день (материализация ленивого генератора)"""
        return tuple(iter_orders_by_day(self.orders, day))

    def top_customers(self, k: int = 5) -> Tuple[Tuple[str, int], ...]:
        """Топ-K покупателей (материализация)"""
        return tuple(lazy_top_customers(self.orders, k))

    def paid_orders(self) -> Tuple[Order, ...]:
        """Только оплаченные заказы"""
        return tuple(filter(lambda o: o.status == "paid", self.orders))

    def total_revenue(self) -> int:
        """Общая выручка (только paid)"""
        return total_sales(self.paid_orders())


class AnalyticsService:
    """
    Аналитический фасад
    Композирует функции из CatalogService и OrderService
    """

    def __init__(self, catalog_service: CatalogService, order_service: OrderService):
        self.catalog = catalog_service
        self.orders = order_service

    def daily_report(self, day: str) -> dict:
        """
        Дневной отчёт через композицию чистых функций
        Pipeline: orders → filter → aggregate → top customers
        """
        # Получаем заказы за день
        day_orders = self.orders.orders_by_day(day)

        # Композиция: фильтрация → агрегация
        sales_pipeline = compose(
            lambda orders: tuple(filter(lambda o: o.status == "paid", orders)),
            total_sales,
        )

        return {
            "day": day,
            "orders": day_orders,
            "total_sales": sales_pipeline(day_orders),
            "order_count": len(day_orders),
            "top_customers": list(self.orders.top_customers(3)),
        }

    def category_sales_report(self, category_id: str) -> dict:
        """
        Отчёт по продажам категории
        """
        # Получаем товары категории
        category_products = self.catalog.products_by_category(category_id)
        product_ids = {p.id for p in category_products}

        # Фильтруем заказы с товарами из категории
        def has_category_products(order: Order) -> bool:
            return any(pid in product_ids for pid, _ in order.items)

        relevant_orders = tuple(filter(has_category_products, self.orders.paid_orders()))

        # Вычисляем продажи только по товарам категории
        def category_total(order: Order) -> int:
            return sum(
                qty * next((p.price for p in category_products if p.id == pid), 0)
                for pid, qty in order.items
                if pid in product_ids
            )

        from functools import reduce

        total = reduce(lambda acc, o: acc + category_total(o), relevant_orders, 0)

        return {
            "category_id": category_id,
            "products_count": len(category_products),
            "orders_count": len(relevant_orders),
            "total_sales": total,
        }

    def user_retention_report(self) -> dict:
        """
        Отчёт по повторным покупкам
        Pipeline: group by user → count orders → filter repeat customers
        """
        from collections import defaultdict

        # Группируем заказы по пользователям
        user_orders = defaultdict(list)
        for order in self.orders.paid_orders():
            user_orders[order.user_id].append(order)

        # Считаем метрики
        total_users = len(user_orders)
        repeat_customers = sum(1 for orders in user_orders.values() if len(orders) > 1)
        retention_rate = (
            (repeat_customers / total_users * 100) if total_users > 0 else 0
        )

        return {
            "total_users": total_users,
            "repeat_customers": repeat_customers,
            "retention_rate": round(retention_rate, 2),
            "orders_per_user": {
                uid: len(orders) for uid, orders in user_orders.items()
            },
        }