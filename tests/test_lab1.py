import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.domain import Cart, Order
from core.transforms import (
    load_seed,
    add_to_cart,
    remove_from_cart,
    checkout,
    total_sales,
)

# еальные данные из seed.json
categories, products, users, orders = load_seed("data/seed.json")

# преобразование списка продуктов в словарь для быстрого доступа по id
PRODUCTS_DICT = {p.id: p for p in products}


def test_load_seed():
    """Проверка загрузки данных из seed.json"""
    assert len(products) > 0
    assert len(users) > 0
    assert len(orders) >= 0


def test_add_to_cart():
    """Проверка добавления товаров в корзину"""
    cart = Cart(id="c1", user_id=users[0].id, items=())
    product = products[0]
    updated = add_to_cart(cart, product.id, 2)
    assert updated != cart
    assert (product.id, 2) in updated.items


def test_remove_from_cart():
    """Проверка удаления товаров из корзины"""
    cart = Cart(
        id="c1", user_id=users[0].id, items=((products[0].id, 2), (products[1].id, 1))
    )
    updated = remove_from_cart(cart, products[0].id)
    assert (products[0].id, 2) not in updated.items
    assert (products[1].id, 1) in updated.items


def test_checkout_creates_order():
    """Проверка создания заказа при оформлении корзины"""
    cart = Cart(id="c1", user_id=users[0].id, items=((products[0].id, 2),))
    order = checkout(cart, ts="2025-09-15T12:00:00", products=products)
    assert isinstance(order, Order)
    assert order.total == products[0].price * 2
    assert order.status == "paid"


def test_total_sales_reduce():
    """Проверка суммарных продаж"""
    cart1 = Cart(id="c1", user_id=users[0].id, items=((products[0].id, 1),))
    cart2 = Cart(id="c2", user_id=users[0].id, items=((products[1].id, 3),))
    order1 = checkout(cart1, ts="2025-09-15T12:00:00", products=products)
    order2 = checkout(cart2, ts="2025-09-15T13:00:00", products=products)
    total = total_sales((order1, order2))
    expected_total = (products[0].price * 1) + (products[1].price * 3)
    assert total == expected_total
