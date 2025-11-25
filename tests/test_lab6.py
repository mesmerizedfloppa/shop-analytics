import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.frp import (
    EventBus,
    create_event,
    create_shop_event_bus,
    initial_state,
    apply_events,
)


def test_eventbus_immutability():
    """EventBus должен быть иммутабельным"""
    bus1 = EventBus()
    bus2 = bus1.subscribe("TEST", lambda e, s: s)

    assert bus1.subscribers == ()
    assert len(bus2.subscribers) == 1
    assert bus1 is not bus2


def test_add_to_cart_event():
    """Событие ADD_TO_CART должно обновлять корзины"""
    bus = create_shop_event_bus()
    state = initial_state()

    event = create_event(
        "ADD_TO_CART", {"cart_id": "c1", "product_id": "p1", "qty": 2}
    )

    new_state = bus.publish(event, state)

    assert "c1" in new_state["active_carts"]
    assert new_state["active_carts"]["c1"]["p1"] == 2
    assert new_state["last_event"] == "ADD_TO_CART"


def test_checkout_event():
    """Событие CHECKOUT должно добавлять продажу"""
    bus = create_shop_event_bus()
    state = initial_state()

    event = create_event(
        "CHECKOUT", {"order_id": "o1", "user_id": "u1", "total": 50000}
    )

    new_state = bus.publish(event, state)

    assert len(new_state["current_sales"]) == 1
    assert new_state["total_revenue"] == 50000
    assert new_state["current_sales"][0]["order_id"] == "o1"


def test_refund_event():
    """Событие REFUND должно учитывать возвраты"""
    bus = create_shop_event_bus()
    state = initial_state()

    event = create_event("REFUND", {"order_id": "o1", "amount": 20000})

    new_state = bus.publish(event, state)

    assert len(new_state["refunds"]) == 1
    assert new_state["total_refunded"] == 20000


def test_remove_from_cart_event():
    """Событие REMOVE должно удалять товар из корзины"""
    bus = create_shop_event_bus()

    # Сначала добавим товар
    state = initial_state()
    add_event = create_event(
        "ADD_TO_CART", {"cart_id": "c1", "product_id": "p1", "qty": 3}
    )
    state = bus.publish(add_event, state)

    # Теперь удалим
    remove_event = create_event("REMOVE", {"cart_id": "c1", "product_id": "p1"})
    new_state = bus.publish(remove_event, state)

    assert "p1" not in new_state["active_carts"]["c1"]


def test_event_sequence():
    """Последовательность событий должна корректно применяться"""
    bus = create_shop_event_bus()
    state = initial_state()

    events = (
        create_event("ADD_TO_CART", {"cart_id": "c1", "product_id": "p1", "qty": 2}),
        create_event("ADD_TO_CART", {"cart_id": "c1", "product_id": "p2", "qty": 1}),
        create_event("CHECKOUT", {"order_id": "o1", "user_id": "u1", "total": 30000}),
    )

    final_state = apply_events(bus, events, state)

    assert len(final_state["active_carts"]["c1"]) == 2
    assert final_state["total_revenue"] == 30000
    assert len(final_state["current_sales"]) == 1