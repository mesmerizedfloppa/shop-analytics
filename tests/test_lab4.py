import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.ftypes import Maybe, Either
from core.domain import Product, Order
from core.transforms import safe_product, validate_order


# ТЕСТЫ Maybe
def test_maybe_some_and_none_behavior():
    just = Maybe.some(42)
    nothing = Maybe.nothing()

    assert not just.is_none()
    assert nothing.is_none()
    assert just.get_or_else(0) == 42
    assert nothing.get_or_else(0) == 0


def test_maybe_map_and_bind():
    maybe_val = Maybe.some(10)
    mapped = maybe_val.map(lambda x: x * 2)
    bound = maybe_val.bind(lambda x: Maybe.some(x + 5))

    assert mapped.get_or_else(0) == 20
    assert bound.get_or_else(0) == 15


def test_safe_product_found_and_not_found():
    products = (
        Product(id="p1", title="Phone", price=10000, category_id="c1", tags=("tech",)),
    )
    found = safe_product(products, "p1")
    not_found = safe_product(products, "p999")

    assert not found.is_none()
    assert found.get_or_else(None).title == "Phone"
    assert not_found.is_none()


# ТЕСТЫ Either
def test_either_left_and_right_behavior():
    right_val = Either.right(100)
    left_val = Either.left("error")

    assert right_val.is_right
    assert not left_val.is_right
    assert right_val.get_or_else(0) == 100
    assert left_val.get_or_else(0) == 0


def test_either_map_and_bind():
    val = Either.right(5)
    mapped = val.map(lambda x: x * 2)
    bound = val.bind(lambda x: Either.right(x + 3))

    assert mapped.get_or_else(0) == 10
    assert bound.get_or_else(0) == 8


def test_validate_order_success_and_failure():
    order_ok = Order(
        id="o1",
        user_id="u1",
        items=(("p1", 1), ("p2", 2)),
        total=0,
        ts="2025-10-21",
        status="pending",
    )
    order_fail = Order(
        id="o2",
        user_id="u1",
        items=(("p1", 5), ("p2", 1)),
        total=0,
        ts="2025-10-21",
        status="pending",
    )

    stock = {"p1": 2, "p2": 10}

    result_ok = validate_order(order_ok, stock, ())
    result_fail = validate_order(order_fail, stock, ())

    assert result_ok.is_right
    assert not result_fail.is_right
    assert isinstance(result_fail.get_or_else({}), dict)
