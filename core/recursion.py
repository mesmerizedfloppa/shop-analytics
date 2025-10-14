from typing import Tuple
from .domain import Category, Product

# Рекурсивное разворачивание дерева категорий


def flatten_categories(cats: Tuple[Category, ...], root: str) -> Tuple[Category, ...]:
    """
    Возвращает все категории в поддереве, включая сам root
    Пример:
      root -> (cat1, cat2)
        cat1 -> (cat3)
        cat2 -> (cat4, cat5)
      flatten_categories(...) -> (root, cat1, cat2, cat3, cat4, cat5)
    """
    root_cat = next((c for c in cats if c.id == root), None)
    direct_children = tuple(filter(lambda c: c.parent_id == root, cats))
    nested = tuple(
        cat for child in direct_children for cat in flatten_categories(cats, child.id)
    )
    # Возвращаем root + все дочерние + вложенные
    return ((root_cat,) if root_cat else ()) + direct_children + nested


# Рекурсивный сбор товаров по дереву категорий


def collect_products_recursive(
    cats: Tuple[Category, ...],
    prods: Tuple[Product, ...],
    root_id: str,
) -> Tuple[Product, ...]:
    """
    Рекурсивно собирает все товары, относящиеся к категории root_id и всем её потомкам
    """
    subcats = flatten_categories(cats, root_id)
    cat_ids = (root_id,) + tuple(map(lambda c: c.id, subcats))
    return tuple(filter(lambda p: p.category_id in cat_ids, prods))
