from typing import Iterator, Iterable
from collections import defaultdict
from .domain import Order


## ленивый генератор, возвращает заказы созданные в указанный день (ГГГГ-ММ-ДД)
def iter_orders_by_day(orders: Iterable[Order], day: str) -> Iterator[Order]:
    for order in orders:
        if order.ts.startswith(day):
            yield order


## лениво вычисляет топ-к пользователй по объему покупок
## не хранит все промежуточные результаты в памяти
def lazy_top_customers(orders: Iterable[Order], k: int) -> Iterator[tuple[str, int]]:
    totals = defaultdict(int)
    for order in orders:
        totals[order.user_id] += order.total

    # сортировка только в конце
    for user_id, total in sorted(totals.items(), key=lambda x: x[1], reverse=True)[:k]:
        yield (user_id, total)
