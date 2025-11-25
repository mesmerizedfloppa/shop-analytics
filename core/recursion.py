from typing import Tuple
from .domain import Category, Product

# Рекурсивное разворачивание дерева категорий


def flatten_categories(cats: Tuple[Category, ...], root: str) -> Tuple[Category, ...]:
    """
    Возвращает все категории в поддереве, включая сам root
    ИСПРАВЛЕНО: убрано дублирование direct_children

    Пример:
      root -> (cat1, cat2)
        cat1 -> (cat3)
        cat2 -> (cat4, cat5)
      flatten_categories(...) -> (root, cat1, cat2, cat3, cat4, cat5)
    """
    root_cat = next((c for c in cats if c.id == root), None)
    if not root_cat:
        return ()

    direct_children = tuple(filter(lambda c: c.parent_id == root, cats))

    # Рекурсивно собираем всех потомков каждого прямого ребёнка
    nested = tuple(
        cat for child in direct_children for cat in flatten_categories(cats, child.id)
    )

    # Возвращаем root + прямые дети + все вложенные
    return (root_cat,) + direct_children + nested


# Рекурсивный сбор товаров по дереву категорий


def collect_products_recursive(
    cats: Tuple[Category, ...],
    prods: Tuple[Product, ...],
    root_id: str,
) -> Tuple[Product, ...]:
    """
    Рекурсивно собирает все товары, относящиеся к категории root_id и всем её потомкам
    """
    # Получаем все категории в дереве
    subcats = flatten_categories(cats, root_id)

    # Собираем все ID категорий
    cat_ids = {c.id for c in subcats}

    # Фильтруем товары по этим ID
    return tuple(filter(lambda p: p.category_id in cat_ids, prods))
