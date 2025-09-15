import json
import uuid
from functools import reduce
from typing import Tuple
from .domain import Cart, Order, Product, User, Category


# Загрузка исходных данных
def load_seed(
    path: str,
) -> tuple[
    Tuple[Category, ...], Tuple[Product, ...], Tuple[User, ...], Tuple[Order, ...]
]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    categories = tuple(map(lambda c: Category(**c), data["categories"]))
    products = tuple(map(lambda p: Product(**p), data["products"]))
    users = tuple(map(lambda u: User(**u), data["users"]))
    orders = tuple(map(lambda o: Order(**o), data["orders"]))

    return categories, products, users, orders


# Добавление товара в корзину
def add_to_cart(cart: Cart, product_id: str, qty: int) -> Cart:
    updated_items = tuple(
        map(
            lambda item: (item[0], item[1] + qty) if item[0] == product_id else item,
            cart.items,
        )
    )

    if not any(map(lambda item: item[0] == product_id, cart.items)):
        updated_items += ((product_id, qty),)

    return Cart(id=cart.id, user_id=cart.user_id, items=updated_items)


# Удаление товара из корзины
def remove_from_cart(cart: Cart, product_id: str) -> Cart:
    filtered_items = tuple(filter(lambda item: item[0] != product_id, cart.items))
    return Cart(id=cart.id, user_id=cart.user_id, items=filtered_items)


# Оформление заказа
def checkout(cart: Cart, ts: str, products: Tuple[Product, ...]) -> Order:
    def get_price(pid: str) -> int:
        return next(p.price for p in products if p.id == pid)

    total = reduce(
        lambda acc, item: acc + get_price(item[0]) * item[1],
        cart.items,
        0,
    )

    return Order(
        id=str(uuid.uuid4()),
        user_id=cart.user_id,
        items=cart.items,
        total=total,
        ts=ts,
        status="paid",
    )


# Подсчет общей суммы продаж
def total_sales(orders: Tuple[Order, ...]) -> int:
    return reduce(lambda acc, o: acc + o.total, orders, 0)
