from dataclasses import dataclass
from typing import Callable, Tuple
from .domain import Event
import uuid
from datetime import datetime


@dataclass(frozen=True)
class EventBus:
    """
    Иммутабельная шина событий (FRP)
    Подписчики - чистые функции: (Event, State) -> State
    """

    subscribers: Tuple[Tuple[str, Callable], ...] = ()

    def subscribe(
        self, event_name: str, handler: Callable[[Event, dict], dict]
    ) -> "EventBus":
        """
        Возвращает новую шину с добавленным подписчиком
        handler: (Event, current_state) -> new_state
        """
        new_subscriber = (event_name, handler)
        return EventBus(subscribers=self.subscribers + (new_subscriber,))

    def publish(self, event: Event, state: dict) -> dict:
        """
        Публикует событие, применяя все подписчики
        Возвращает новое состояние
        """
        matching_handlers = tuple(
            handler for name, handler in self.subscribers if name == event.name
        )

        # Применяем все обработчики последовательно (fold)
        def apply_handler(current_state: dict, handler: Callable) -> dict:
            return handler(event, current_state)

        from functools import reduce

        return reduce(apply_handler, matching_handlers, state)


# ============ Конструкторы событий ============


def create_event(name: str, payload: dict) -> Event:
    """Создаёт событие с автоматической меткой времени"""
    return Event(
        id=str(uuid.uuid4()),
        ts=datetime.now().isoformat(),
        name=name,
        payload=payload,
    )


# ============ Примеры чистых обработчиков событий ============


def handle_add_to_cart(event: Event, state: dict) -> dict:
    """
    Обработчик ADD_TO_CART
    Обновляет витрину активных корзин
    """
    cart_id = event.payload.get("cart_id")
    product_id = event.payload.get("product_id")
    qty = event.payload.get("qty", 1)

    active_carts = state.get("active_carts", {})

    # Обновляем корзину иммутабельно
    cart_items = active_carts.get(cart_id, {})
    updated_items = dict(cart_items)
    updated_items[product_id] = updated_items.get(product_id, 0) + qty

    # Возвращаем новое состояние
    return {
        **state,
        "active_carts": {**active_carts, cart_id: updated_items},
        "last_event": event.name,
    }


def handle_checkout(event: Event, state: dict) -> dict:
    """
    Обработчик CHECKOUT
    Добавляет заказ в список текущих продаж
    """
    order_id = event.payload.get("order_id")
    total = event.payload.get("total", 0)
    user_id = event.payload.get("user_id")

    current_sales = state.get("current_sales", [])
    new_sale = {
        "order_id": order_id,
        "total": total,
        "user_id": user_id,
        "ts": event.ts,
    }

    return {
        **state,
        "current_sales": current_sales + [new_sale],
        "total_revenue": state.get("total_revenue", 0) + total,
        "last_event": event.name,
    }


def handle_refund(event: Event, state: dict) -> dict:
    """
    Обработчик REFUND
    Обновляет список возвратов
    """
    order_id = event.payload.get("order_id")
    amount = event.payload.get("amount", 0)

    refunds = state.get("refunds", [])
    new_refund = {"order_id": order_id, "amount": amount, "ts": event.ts}

    return {
        **state,
        "refunds": refunds + [new_refund],
        "total_refunded": state.get("total_refunded", 0) + amount,
        "last_event": event.name,
    }


def handle_remove_from_cart(event: Event, state: dict) -> dict:
    """
    Обработчик REMOVE
    Удаляет товар из корзины
    """
    cart_id = event.payload.get("cart_id")
    product_id = event.payload.get("product_id")

    active_carts = state.get("active_carts", {})
    cart_items = active_carts.get(cart_id, {})

    # Удаляем товар иммутабельно
    updated_items = {pid: qty for pid, qty in cart_items.items() if pid != product_id}

    return {
        **state,
        "active_carts": {**active_carts, cart_id: updated_items},
        "last_event": event.name,
    }


# ============ Вспомогательные функции ============


def create_shop_event_bus() -> EventBus:
    """
    Создаёт предконфигурированную шину для интернет-магазина
    """
    bus = EventBus()
    bus = bus.subscribe("ADD_TO_CART", handle_add_to_cart)
    bus = bus.subscribe("REMOVE", handle_remove_from_cart)
    bus = bus.subscribe("CHECKOUT", handle_checkout)
    bus = bus.subscribe("REFUND", handle_refund)
    return bus


def initial_state() -> dict:
    """Начальное состояние приложения"""
    return {
        "active_carts": {},
        "current_sales": [],
        "refunds": [],
        "total_revenue": 0,
        "total_refunded": 0,
        "last_event": None,
    }


# ============ Композиция событий ============


def apply_events(bus: EventBus, events: Tuple[Event, ...], state: dict) -> dict:
    """
    Применяет последовательность событий к состоянию
    Чистая функция: (events, initial_state) -> final_state
    """
    from functools import reduce

    return reduce(lambda s, e: bus.publish(e, s), events, state)
