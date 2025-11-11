from core.transforms import total_sales
from core.recursion import flatten_categories, collect_products_recursive
from core.lazy import iter_orders_by_day, lazy_top_customers
from core.compose import pipe


class CatalogService:
    def __init__(self, categories, products):
        self.categories = categories
        self.products = products

    def products_by_category(self, root_id: str):
        return pipe(
            lambda _: flatten_categories(self.categories, root_id),
            lambda _: collect_products_recursive(
                self.categories, self.products, root_id
            ),
        )(None)


class OrderService:
    def __init__(self, orders):
        self.orders = orders

    def orders_by_day(self, day: str):
        return tuple(iter_orders_by_day(self.orders, day))

    def top_customers(self, k: int = 5):
        return tuple(lazy_top_customers(self.orders, k))


class AnalyticsService:
    def __init__(self, catalog_service: CatalogService, order_service: OrderService):
        self.catalog = catalog_service
        self.orders = order_service

    def daily_report(self, day: str):
        """Композиция чистых функций (pipeline)"""
        return pipe(
            self.orders.orders_by_day,
            lambda orders: {
                "orders": orders,
                "total_sales": total_sales(orders),
                "top_customers": list(self.orders.top_customers(3)),
            },
        )(day)
