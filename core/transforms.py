import json
import uuid
from functools import reduce, lru_cache
from typing import Tuple, Callable

from .domain import Cart, Order, Product, User, Category


# Загрузка исходных данных
def load_seed(
    path: str,
) -> Tuple[
    Tuple[Category, ...], Tuple[Product, ...], Tuple[User, ...], Tuple[Order, ...]
]:
    """
    Загружает seed.json и возвращает кортежи (categories, products, users, orders)
    Приводит списки items в orders к tuple[tuple[str,int], ...], tags -> tuple
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    categories = tuple(map(lambda c: Category(**c), data.get("categories", [])))

    def _to_product(p):
        p2 = dict(p)
        p2["tags"] = tuple(p2.get("tags", []))
        return Product(**p2)

    products = tuple(map(_to_product, data.get("products", [])))
    users = tuple(map(lambda u: User(**u), data.get("users", [])))

    def _to_order(o):
        # items может быть list[list] приводим к tuple[tuple]
        items = tuple((str(item[0]), int(item[1])) for item in o.get("items", []))
        return Order(
            id=str(o.get("id", uuid.uuid4())),
            user_id=str(o.get("user_id")),
            items=items,
            total=int(o.get("total", 0)),
            ts=str(o.get("ts", "")),
            status=str(o.get("status", "paid")),
        )

    orders = tuple(map(_to_order, data.get("orders", [])))

    return categories, products, users, orders


# Cart operations


def add_to_cart(cart: Cart, product_id: str, qty: int) -> Cart:
    """
    Возвращает новый Cart с добавленным количеством товара
    Если товар уже есть увеличиваем количество
    """
    if qty <= 0:
        return cart

    updated_items = tuple(
        map(
            lambda item: (item[0], item[1] + qty) if item[0] == product_id else item,
            cart.items,
        )
    )

    if not any(map(lambda item: item[0] == product_id, cart.items)):
        updated_items = updated_items + ((product_id, qty),)

    return Cart(id=cart.id, user_id=cart.user_id, items=updated_items)


def remove_from_cart(cart: Cart, product_id: str) -> Cart:
    """
    Возвращает новый Cart без записей с product_id
    """
    filtered_items = tuple(filter(lambda item: item[0] != product_id, cart.items))
    return Cart(id=cart.id, user_id=cart.user_id, items=filtered_items)


# Checkout


def checkout(cart: Cart, ts: str, products: Tuple[Product, ...]) -> Order:
    """
    Оформляет корзину — возвращает Order с вычислённым total (в копейках)
    Если product_id не найден выбрасывает ValueError
    """

    def get_price(pid: str) -> int:
        found = next((p.price for p in products if p.id == pid), None)
        if found is None:
            raise ValueError(f"Product id '{pid}' not found in products.")
        return found

    total = reduce(lambda acc, item: acc + get_price(item[0]) * item[1], cart.items, 0)

    return Order(
        id=str(uuid.uuid4()),
        user_id=cart.user_id,
        items=cart.items,
        total=total,
        ts=str(ts),
        status="paid",
    )


# Aggregation


def total_sales(orders: Tuple[Order, ...]) -> int:
    """
    Сумма полей total во всех заказах (reduce)
    """
    return reduce(lambda acc, o: acc + int(o.total), orders, 0)


# Замыкания-фильтры


def by_category(cat_id: str) -> Callable[[Product], bool]:
    """Возвращает функцию-предикат, оставляющую товары заданной категории"""
    return lambda p: p.category_id == cat_id


def by_price_range(min_price: int, max_price: int) -> Callable[[Product], bool]:
    """Возвращает предикат по диапазону цен (в тех же единицах, что и Product.price)"""
    return lambda p: min_price <= p.price <= max_price


def by_tag(tag: str) -> Callable[[Product], bool]:
    """Возвращает предикат, проверяющий наличие тега у товара"""
    return lambda p: tag in p.tags


def by_user_tier(tier: str) -> Callable[[User], bool]:
    """Возвращает предикат для пользователей по полю tier"""
    return lambda u: (u.tier or "").lower() == (tier or "").lower()


## дорогая функция поиска бесстселеров 

@lru_cache
def top_products(
    orders: Tuple[Order, ...],
    products: Tuple[Product, ...],
    k: int = 10
) -> Tuple[Product, ...]:
    product_sales = {}

    for order in orders:
        if order.status != "paid":
            continue
        for pid, qty in order.items:
            product_sales[pid] = product_sales.get(pid, 0) + qty

    ranked_ids = sorted(product_sales, key=product_sales.get, reverse=True)[:k]
    return tuple(p for p in products if p.id in ranked_ids)