import json
import uuid
from functools import reduce, lru_cache
from typing import Tuple, Callable
from .ftypes import Maybe, Either
from .domain import Cart, Order, Product, User, Category


def load_seed(
    path: str,
) -> Tuple[
    Tuple[Category, ...], Tuple[Product, ...], Tuple[User, ...], Tuple[Order, ...]
]:
    """Загружает seed.json и возвращает кортежи иммутабельных данных"""
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


# ============ Cart operations (чистые функции) ============


def add_to_cart(cart: Cart, product_id: str, qty: int) -> Cart:
    """Возвращает новый Cart с добавленным товаром (иммутабельно)"""
    if qty <= 0:
        return cart

    # Проверяем, есть ли уже товар
    existing_item = next((item for item in cart.items if item[0] == product_id), None)

    if existing_item:
        # Обновляем количество существующего товара
        updated_items = tuple(
            (pid, q + qty) if pid == product_id else (pid, q) for pid, q in cart.items
        )
    else:
        # Добавляем новый товар
        updated_items = cart.items + ((product_id, qty),)

    return Cart(id=cart.id, user_id=cart.user_id, items=updated_items)


def remove_from_cart(cart: Cart, product_id: str) -> Cart:
    """Возвращает новый Cart без товара с product_id"""
    filtered_items = tuple(filter(lambda item: item[0] != product_id, cart.items))
    return Cart(id=cart.id, user_id=cart.user_id, items=filtered_items)


# ============ Checkout с Either для безопасности ============


def checkout(cart: Cart, ts: str, products: Tuple[Product, ...]) -> Either[dict, Order]:
    """
    Оформляет корзину → Either[error, Order]
    Left(error) если товар не найден
    Right(Order) при успехе
    """

    def get_price(pid: str) -> Maybe[int]:
        found = next((p.price for p in products if p.id == pid), None)
        return Maybe.some(found) if found is not None else Maybe.nothing()

    # Вычисляем total через fold с проверкой каждого товара
    def accumulate_total(acc: Either[dict, int], item: Tuple[str, int]):
        if acc.is_left:
            return acc  # Ошибка уже произошла

        pid, qty = item
        price_maybe = get_price(pid)

        if price_maybe.is_none():
            return Either.left({"error": f"Product '{pid}' not found"})

        current_total = acc.get_or_else(0)
        return Either.right(current_total + price_maybe.get_or_else(0) * qty)

    total_result = reduce(accumulate_total, cart.items, Either.right(0))

    # Если была ошибка, возвращаем Left
    if total_result.is_left:
        return total_result

    # Создаём заказ
    order = Order(
        id=str(uuid.uuid4()),
        user_id=cart.user_id,
        items=cart.items,
        total=total_result.get_or_else(0),
        ts=str(ts),
        status="paid",
    )

    return Either.right(order)


# ============ Aggregation ============


def total_sales(orders: Tuple[Order, ...]) -> int:
    """Сумма всех заказов через reduce"""
    return reduce(lambda acc, o: acc + int(o.total), orders, 0)


# ============ Замыкания-фильтры (HOF) ============


def by_category(cat_id: str) -> Callable[[Product], bool]:
    """Фильтр по категории"""
    return lambda p: p.category_id == cat_id


def by_price_range(min_price: int, max_price: int) -> Callable[[Product], bool]:
    """Фильтр по диапазону цен"""
    return lambda p: min_price <= p.price <= max_price


def by_tag(tag: str) -> Callable[[Product], bool]:
    """Фильтр по наличию тега"""
    return lambda p: tag in p.tags


def by_user_tier(tier: str) -> Callable[[User], bool]:
    """Фильтр пользователей по уровню"""
    return lambda u: (u.tier or "").lower() == (tier or "").lower()


# ============ Мемоизация (Лаба 3) ============


@lru_cache
def top_products(
    orders: Tuple[Order, ...], products: Tuple[Product, ...], k: int = 10
) -> Tuple[Product, ...]:
    """
    Топ-K товаров по продажам (только paid заказы)
    Кэшируется через lru_cache
    """

    # Агрегация продаж через reduce
    def accumulate_sales(sales_dict: dict, order: Order):
        if order.status != "paid":
            return sales_dict

        for pid, qty in order.items:
            sales_dict[pid] = sales_dict.get(pid, 0) + qty
        return sales_dict

    product_sales = reduce(accumulate_sales, orders, {})

    # Сортировка и выбор топ-K
    ranked_ids = sorted(product_sales, key=product_sales.get, reverse=True)[:k]
    return tuple(p for p in products if p.id in ranked_ids)


# ============ Maybe/Either для безопасных операций (Лаба 4) ============


def safe_product(products: Tuple[Product, ...], pid: str) -> Maybe[Product]:
    """Безопасный поиск продукта по ID"""
    found = next((p for p in products if p.id == pid), None)
    return Maybe.some(found) if found is not None else Maybe.nothing()


def validate_order(
    order: Order, stock: dict, discounts: tuple = ()
) -> Either[dict, Order]:
    """
    Проверяет заказ на корректность:
    - Товары существуют в stock
    - Достаточно количества на складе
    Возвращает Either[error, validated_order]
    """

    def validate_item(item: Tuple[str, int]) -> Either[dict, Tuple[str, int]]:
        pid, qty = item
        if pid not in stock:
            return Either.left({"error": f"Товар {pid} отсутствует в базе"})
        if stock[pid] < qty:
            return Either.left({"error": f"Недостаточно товара {pid} на складе"})
        return Either.right(item)

    # Проверяем все товары
    results = [validate_item(i) for i in order.items]
    errors = [r.value for r in results if r.is_left]

    if errors:
        return Either.left(errors[0])

    # Вычисляем total (для примера)
    total = sum(qty * 1000 for _, qty in order.items)  # Заглушка
    validated = Order(
        id=order.id,
        user_id=order.user_id,
        items=order.items,
        total=total,
        ts=order.ts,
        status="validated",
    )
    return Either.right(validated)
