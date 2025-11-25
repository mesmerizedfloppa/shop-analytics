import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.domain import Category, Product, User
from core.transforms import by_category, by_price_range, by_tag, by_user_tier
from core.recursion import flatten_categories, collect_products_recursive

# Тесты для замыканий


def test_by_category_filter():
    cat_id = "c001"
    f = by_category(cat_id)
    prods = [
        Product(id="p1", title="A", price=1000, category_id="c001", tags=("x",)),
        Product(id="p2", title="B", price=2000, category_id="c002", tags=("x",)),
    ]
    assert list(filter(f, prods)) == [prods[0]]


def test_by_price_range_filter():
    f = by_price_range(1000, 2000)
    prods = [
        Product(id="p1", title="A", price=500, category_id="c", tags=()),
        Product(id="p2", title="B", price=1500, category_id="c", tags=()),
        Product(id="p3", title="C", price=2500, category_id="c", tags=()),
    ]
    result = list(filter(f, prods))
    assert len(result) == 1 and result[0].id == "p2"


def test_by_tag_filter():
    f = by_tag("tech")
    prods = [
        Product(id="p1", title="A", price=1000, category_id="c", tags=("tech", "new")),
        Product(id="p2", title="B", price=2000, category_id="c", tags=("sale",)),
    ]
    assert list(filter(f, prods)) == [prods[0]]


def test_by_user_tier_filter():
    f = by_user_tier("VIP")
    users = [
        User(id="u1", name="A", tier="regular"),
        User(id="u2", name="B", tier="VIP"),
        User(id="u3", name="C", tier="regular"),
    ]
    assert list(filter(f, users)) == [users[1]]


# Тесты для рекурсивных функций


def test_flatten_categories_nested_tree():
    cats = (
        Category(id="c001", name="Root", parent_id=None),
        Category(id="c002", name="Sub1", parent_id="c001"),
        Category(id="c003", name="Sub2", parent_id="c002"),
        Category(id="c004", name="Other", parent_id=None),
    )
    flattened = flatten_categories(cats, "c001")
    ids = {c.id for c in flattened}
    assert ids == {"c001", "c002", "c003"}


def test_collect_products_recursive_deep():
    cats = (
        Category(id="c001", name="Root", parent_id=None),
        Category(id="c002", name="Sub", parent_id="c001"),
        Category(id="c003", name="Leaf", parent_id="c002"),
    )
    prods = (
        Product(id="p1", title="A", price=1000, category_id="c001", tags=()),
        Product(id="p2", title="B", price=2000, category_id="c002", tags=()),
        Product(id="p3", title="C", price=3000, category_id="c003", tags=()),
        Product(id="p4", title="D", price=4000, category_id="cXXX", tags=()),
    )
    collected = collect_products_recursive(cats, prods, "c001")
    ids = {p.id for p in collected}
    assert ids == {"p1", "p2", "p3"}


def test_collect_products_recursive_root_only():
    cats = (Category(id="c001", name="Root", parent_id=None),)
    prods = (
        Product(id="p1", title="A", price=1000, category_id="c001", tags=()),
        Product(id="p2", title="B", price=2000, category_id="c002", tags=()),
    )
    result = collect_products_recursive(cats, prods, "c001")
    assert len(result) == 1 and result[0].id == "p1"
