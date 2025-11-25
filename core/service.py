from functools import reduce
from typing import Tuple
from core.domain import Category, Product, Order
from core.transforms import total_sales
from core.recursion import flatten_categories, collect_products_recursive
from core.lazy import iter_orders_by_day, lazy_top_customers
from core.compose import pipe


class CatalogService:
    """Фасад для работы с каталогом"""

    def __init__(self, categories: Tuple[Category, ...], products: Tuple[Product, ...]):
        self.categories = categories
        self.products = products

    def products_by_category(self, root_id: str) -> Tuple[Product, ...]:
        """Возвращает все товары категории и её подкатегорий"""
        return collect_products_recursive(self.categories, self.products, root_id)

    def filter_products(self, predicate) -> Tuple[Product, ...]:
        """Фильтрует товары по предикату"""
        return tuple(filter(predicate, self.products))

    def get_category_tree(self, root_id: str) -> Tuple[Category, ...]:
        """Возвращает дерево категорий от корня"""
        return flatten_categories(self.categories, root_id)


class OrderService:
    """Фасад для работы с заказами"""

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
    """Аналитический фасад"""

    def __init__(self, catalog_service: CatalogService, order_service: OrderService):
        self.catalog = catalog_service
        self.orders = order_service

    def daily_report(self, day: str) -> dict:
        """
        Дневной отчёт через композицию чистых функций
        ИСПРАВЛЕНО: правильный порядок функций в compose
        """
        day_orders = self.orders.orders_by_day(day)

        # ИСПРАВЛЕНО: compose применяет функции справа налево
        # compose(f, g)(x) = f(g(x))
        # Нам нужно: сначала отфильтровать, потом посчитать
        # Поэтому используем pipe вместо compose
        sales_pipeline = pipe(
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
        """Отчёт по продажам категории"""
        category_products = self.catalog.products_by_category(category_id)
        product_ids = {p.id for p in category_products}

        def has_category_products(order: Order) -> bool:
            return any(pid in product_ids for pid, _ in order.items)

        relevant_orders = tuple(
            filter(has_category_products, self.orders.paid_orders())
        )

        def category_total(order: Order) -> int:
            return sum(
                qty * next((p.price for p in category_products if p.id == pid), 0)
                for pid, qty in order.items
                if pid in product_ids
            )

        total = reduce(lambda acc, o: acc + category_total(o), relevant_orders, 0)

        return {
            "category_id": category_id,
            "products_count": len(category_products),
            "orders_count": len(relevant_orders),
            "total_sales": total,
        }

    def user_retention_report(self) -> dict:
        """Отчёт по повторным покупкам"""

        # Группируем заказы по пользователям через reduce
        def group_by_user(acc: dict, order: Order) -> dict:
            if order.status != "paid":
                return acc
            user_orders = acc.get(order.user_id, [])
            return {**acc, order.user_id: user_orders + [order]}

        user_orders = reduce(group_by_user, self.orders.orders, {})

        total_users = len(user_orders)
        repeat_customers = sum(
            1 for orders_list in user_orders.values() if len(orders_list) > 1
        )
        retention_rate = (
            (repeat_customers / total_users * 100) if total_users > 0 else 0
        )

        return {
            "total_users": total_users,
            "repeat_customers": repeat_customers,
            "retention_rate": round(retention_rate, 2),
            "orders_per_user": {
                uid: len(orders_list) for uid, orders_list in user_orders.items()
            },
        }
