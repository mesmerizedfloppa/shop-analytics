import sys
import os
import streamlit as st
from functools import reduce
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.domain import Cart, Order
from core.transforms import (
    load_seed,
    add_to_cart,
    remove_from_cart,
    checkout,
    by_category,
    by_price_range,
    by_tag,
    top_products,
    safe_product,
    validate_order,
)
from Analytics_Service.report import (
    sales_summary,
    bestsellers_report,
    top_customers_report,
    retention_rate,
    sales_by_hour,
)
from core.frp import create_shop_event_bus, create_event, initial_state
from core.async_ops import run_async_pipeline
from core.lazy import iter_orders_by_day, lazy_top_customers


# ============ Кэширование данных ============
@st.cache_data
def get_data():
    return load_seed("data/seed.json")


@st.cache_resource
def get_event_bus():
    return create_shop_event_bus()


# ============ Инициализация ============
st.set_page_config(
    page_title="FP Shop Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

categories, products, users, orders = get_data()

# Инициализация состояния
if "cart" not in st.session_state:
    st.session_state.cart = Cart(id="cart_default", user_id=users[0].id, items=())

if "frp_state" not in st.session_state:
    st.session_state.frp_state = initial_state()


# ============ Вспомогательные функции ============
def apply_filters(products, category_id=None, min_p=0, max_p=200000, tag=None):
    """Чистая функция фильтрации товаров"""
    filters = []

    if category_id:
        filters.append(by_category(category_id))
    if min_p or max_p:
        filters.append(by_price_range(min_p, max_p))
    if tag:
        filters.append(by_tag(tag))

    # Композиция всех фильтров
    def combined_filter(p):
        return all(f(p) for f in filters)

    return tuple(filter(combined_filter, products))


def format_price(kopecks: int) -> str:
    """Форматирует цену из копеек в тенге"""
    return f"{kopecks / 100:.2f} ₸"


# ============ HEADER ============
st.title("🛒 Функциональный интернет-магазин")
st.caption("💻 Python 3.11+ | 📚 Лабораторные 1-8 | 👥 Алмаз, Нурдаулет, Бакашар")

# ============ SIDEBAR - Навигация ============
with st.sidebar:
    st.header("📂 Навигация")
    page = st.radio(
        "Выберите раздел:",
        [
            "📊 Overview",
            "🏪 Каталог",
            "🛒 Корзина",
            "📈 Статистика",
            "📑 Reports",
            "⚡ FRP Events",
            "🚀 Async Analytics",
            "🧪 Tests Demo",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("### 🎯 Реализованные лабы")
    st.success("✅ Лаба 1: Чистые функции")
    st.success("✅ Лаба 2: Замыкания + рекурсия")
    st.success("✅ Лаба 3: Мемоизация")
    st.success("✅ Лаба 4: Maybe/Either")
    st.success("✅ Лаба 5: Ленивые вычисления")
    st.success("✅ Лаба 6: FRP/Events")
    st.success("✅ Лаба 7: Композиция")
    st.success("✅ Лаба 8: Async/Parallel")


# ============ PAGE: OVERVIEW ============
if page == "📊 Overview":
    st.header("📦 Обзор системы")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📂 Категории", len(categories))
    with col2:
        st.metric("📦 Товары", len(products))
    with col3:
        st.metric("👥 Пользователи", len(users))
    with col4:
        st.metric("🧾 Заказы", len(orders))

    st.divider()

    # Сводка по продажам
    summary = sales_summary(orders)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Выручка", format_price(summary["total_revenue"]))
        st.metric("✅ Оплачено", summary["paid_orders"])
    with col2:
        st.metric("💵 Чистая выручка", format_price(summary["net_revenue"]))
        st.metric("↩️ Возвраты", summary["refunded_orders"])
    with col3:
        st.metric("📊 Средний чек", format_price(int(summary["average_order_value"])))
        st.metric("❌ Отменено", summary["cancelled_orders"])

    st.divider()

    # График продаж по часам
    st.subheader("⏰ Продажи по времени суток")
    hourly = sales_by_hour(orders)
    if hourly:
        st.bar_chart(hourly)


# ============ PAGE: КАТАЛОГ ============
elif page == "🏪 Каталог":
    st.header("🏪 Каталог товаров")

    # Фильтры
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_cat = st.selectbox(
            "📂 Категория",
            ["Все"] + [c.name for c in categories],
            key="catalog_cat",
        )
    with col2:
        price_range = st.slider(
            "💰 Цена (₸)", 0, 2000, (0, 2000), step=50, key="catalog_price"
        )
    with col3:
        all_tags = sorted({t for p in products for t in p.tags})
        selected_tag = st.selectbox("🏷️ Тег", ["Все"] + all_tags, key="catalog_tag")

    # Применяем фильтры
    cat_id = (
        next((c.id for c in categories if c.name == selected_cat), None)
        if selected_cat != "Все"
        else None
    )
    tag = selected_tag if selected_tag != "Все" else None

    filtered = apply_filters(
        products, cat_id, price_range[0] * 100, price_range[1] * 100, tag
    )

    st.info(f"🔍 Найдено товаров: **{len(filtered)}**")
    st.divider()

    # Отображение товаров
    if not filtered:
        st.warning("Товары не найдены. Попробуйте изменить фильтры.")
    else:
        for p in filtered[:20]:  # Показываем первые 20
            with st.container():
                cols = st.columns([5, 2, 2, 2])
                with cols[0]:
                    st.markdown(f"**{p.title}**")
                    st.caption(f"🏷️ {', '.join(p.tags)}")
                with cols[1]:
                    st.write(format_price(p.price))
                with cols[2]:
                    qty = st.number_input(
                        "Кол-во",
                        min_value=1,
                        value=1,
                        key=f"qty_{p.id}",
                        label_visibility="collapsed",
                    )
                with cols[3]:
                    if st.button("➕ В корзину", key=f"add_{p.id}"):
                        st.session_state.cart = add_to_cart(
                            st.session_state.cart, p.id, qty
                        )
                        st.success(f"✅ {p.title} × {qty}", icon="✅")
                st.divider()


# ============ PAGE: КОРЗИНА ============
elif page == "🛒 Корзина":
    st.header("🛒 Ваша корзина")

    cart = st.session_state.cart

    if not cart.items:
        st.info("🛍️ Корзина пуста. Перейдите в каталог!")
    else:
        # Вычисляем итоговую сумму
        def calc_item_price(item):
            pid, qty = item
            product = next((p for p in products if p.id == pid), None)
            return product.price * qty if product else 0

        total_sum = reduce(lambda acc, item: acc + calc_item_price(item), cart.items, 0)

        # Отображение товаров
        for pid, qty in cart.items:
            product = next((p for p in products if p.id == pid), None)
            if product:
                cols = st.columns([5, 2, 2, 1])
                with cols[0]:
                    st.write(f"**{product.title}**")
                with cols[1]:
                    st.write(f"× {qty}")
                with cols[2]:
                    st.write(format_price(product.price * qty))
                with cols[3]:
                    if st.button("🗑️", key=f"remove_{pid}"):
                        st.session_state.cart = remove_from_cart(cart, pid)
                        st.rerun()

        st.divider()
        st.markdown(f"### 💰 Итого: **{format_price(total_sum)}**")

        # Оформление заказа
        if st.button("✅ Оформить заказ", type="primary", use_container_width=True):
            order_result = checkout(cart, "2025-11-25T12:00:00", products)

            if order_result.is_right:
                order = order_result.get_or_else(None)
                st.success(f"🎉 Заказ оформлен! Сумма: {format_price(order.total)}")
                st.session_state.cart = Cart(
                    id="cart_default", user_id=users[0].id, items=()
                )
                st.balloons()
            else:
                error = order_result.get_or_else({})
                st.error(f"❌ Ошибка: {error.get('error', 'Неизвестная ошибка')}")


# ============ PAGE: СТАТИСТИКА ============
elif page == "📈 Статистика":
    st.header("📈 Статистика и аналитика")

    tab1, tab2, tab3 = st.tabs(
        ["👥 Пользователи", "📦 Товары", "🔄 Ленивые вычисления"]
    )

    with tab1:
        st.subheader("👥 Сегментация пользователей")

        vip = [u for u in users if u.tier == "VIP"]
        regular = [u for u in users if u.tier == "regular"]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("👑 VIP", len(vip))
        with col2:
            st.metric("👤 Regular", len(regular))

        st.divider()

        # Ретеншен
        retention = retention_rate(orders)
        st.subheader("🔁 Retention Rate")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Всего клиентов", retention["total_customers"])
        with col2:
            st.metric("Повторные покупки", retention["repeat_customers"])
        with col3:
            st.metric("% Retention", f"{retention['retention_rate']:.1f}%")

    with tab2:
        st.subheader("📦 Топ товаров")
        k = st.slider("Количество товаров:", 5, 20, 10, key="top_products_slider")

        start = time.perf_counter()
        top = top_products(orders, products, k)
        cached_time = (time.perf_counter() - start) * 1000

        st.caption(f"⏱️ Время выполнения (с кэшем): {cached_time:.2f} ms")

        for idx, p in enumerate(top, 1):
            st.write(f"{idx}. **{p.title}** — {format_price(p.price)}")

    with tab3:
        st.subheader("🔄 Потоковая обработка заказов")

        day = st.date_input("Выберите день:", value=None, key="lazy_day_input")
        if day and st.button("Показать заказы", key="lazy_show"):
            day_str = day.strftime("%Y-%m-%d")
            day_orders = list(iter_orders_by_day(orders, day_str))

            if day_orders:
                st.success(f"✅ Найдено заказов: {len(day_orders)}")
                for o in day_orders[:10]:  # Первые 10
                    st.write(f"• Order {o.id}: {format_price(o.total)}")
            else:
                st.warning("Заказов за этот день не найдено.")

        st.divider()

        # Топ покупателей
        st.subheader("🏆 Топ покупателей (ленивое вычисление)")
        k_customers = st.slider("Количество:", 3, 15, 5, key="lazy_top_slider")

        if st.button("Показать топ", key="lazy_top_btn"):
            top_cust = list(lazy_top_customers(orders, k_customers))
            for uid, total in top_cust:
                st.write(f"• **{uid}**: {format_price(total)}")


# ============ PAGE: REPORTS ============
elif page == "📑 Reports":
    st.header("📑 Отчёты и анализ")

    tab1, tab2, tab3 = st.tabs(["🏆 Бестселлеры", "👥 Топ клиенты", "🔍 Maybe/Either"])

    with tab1:
        st.subheader("🏆 Бестселлеры")
        bestsellers = bestsellers_report(orders, products, k=10)

        for item in bestsellers:
            cols = st.columns([3, 2, 2, 2])
            with cols[0]:
                st.write(f"**{item['title']}**")
            with cols[1]:
                st.write(f"Продано: {item['quantity_sold']}")
            with cols[2]:
                st.write(format_price(item["price"]))
            with cols[3]:
                st.write(f"💰 {format_price(item['revenue'])}")

    with tab2:
        st.subheader("👥 Топ клиенты")
        top_cust = top_customers_report(orders, k=10)

        for item in top_cust:
            cols = st.columns([2, 2, 2, 2])
            with cols[0]:
                st.write(f"**{item['user_id']}**")
            with cols[1]:
                st.write(f"Заказов: {item['order_count']}")
            with cols[2]:
                st.write(format_price(item["total_spent"]))
            with cols[3]:
                st.write(f"Ср. чек: {format_price(item['avg_order'])}")

    with tab3:
        st.subheader("🔍 Безопасные операции (Maybe/Either)")

        st.markdown("##### Поиск товара (Maybe)")
        pid = st.text_input("ID товара:", "p1", key="maybe_search")
        if st.button("Найти", key="maybe_btn"):
            result = safe_product(products, pid)
            if not result.is_none():
                p = result.get_or_else(None)
                st.success(f"✅ Найден: **{p.title}** ({format_price(p.price)})")
            else:
                st.warning(f"❌ Товар `{pid}` не найден")

        st.divider()

        st.markdown("##### Валидация заказа (Either)")
        if st.button("Проверить тестовый заказ", key="either_btn"):
            test_order = Order(
                id="test",
                user_id="u1",
                items=(("p1", 2), ("p2", 1)),
                total=0,
                ts="2025-11-25",
                status="pending",
            )
            stock = {"p1": 5, "p2": 0}  # p2 нет в наличии!

            result = validate_order(test_order, stock, ())
            if result.is_right:
                st.success("✅ Заказ прошёл валидацию")
            else:
                error = result.get_or_else({})
                st.error(f"❌ Ошибка: {error['error']}")


# ============ PAGE: FRP EVENTS ============
elif page == "⚡ FRP Events":
    st.header("⚡ Reactive Event Bus (FRP)")

    bus = get_event_bus()

    st.markdown(
        """
    Демонстрация функционального реактивного программирования.  
    Все обработчики событий — **чистые функции**.
    """
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📤 Генерация событий")

        if st.button("ADD_TO_CART", type="primary", key="frp_add"):
            event = create_event(
                "ADD_TO_CART", {"cart_id": "c1", "product_id": "p1", "qty": 2}
            )
            st.session_state.frp_state = bus.publish(event, st.session_state.frp_state)
            st.success("✅ Событие ADD_TO_CART опубликовано")

        if st.button("CHECKOUT", type="primary", key="frp_checkout"):
            event = create_event(
                "CHECKOUT", {"order_id": "o_new", "user_id": "u1", "total": 50000}
            )
            st.session_state.frp_state = bus.publish(event, st.session_state.frp_state)
            st.success("✅ Событие CHECKOUT опубликовано")

        if st.button("REFUND", key="frp_refund"):
            event = create_event("REFUND", {"order_id": "o1", "amount": 10000})
            st.session_state.frp_state = bus.publish(event, st.session_state.frp_state)
            st.warning("⚠️ Событие REFUND опубликовано")

    with col2:
        st.subheader("📊 Текущее состояние")

        state = st.session_state.frp_state

        st.metric("💰 Выручка", format_price(state.get("total_revenue", 0)))
        st.metric("↩️ Возвраты", format_price(state.get("total_refunded", 0)))
        st.metric("🛒 Активных корзин", len(state.get("active_carts", {})))
        st.metric("📦 Продаж", len(state.get("current_sales", [])))

        st.divider()
        st.caption(f"Последнее событие: **{state.get('last_event', 'N/A')}**")


# ============ PAGE: ASYNC ANALYTICS ============
elif page == "🚀 Async Analytics":
    st.header("🚀 Асинхронная аналитика (Лаба 8)")

    st.markdown(
        """
    Параллельная обработка данных с использованием `asyncio`.  
    Все анализы выполняются **одновременно**.
    """
    )

    if st.button("▶️ Запустить полный анализ", type="primary", key="async_run"):
        with st.spinner("⏳ Выполняется асинхронный анализ..."):
            start = time.perf_counter()
            result = run_async_pipeline(list(orders), list(products), list(users))
            elapsed = (time.perf_counter() - start) * 1000

        st.success(f"✅ Анализ завершён за {elapsed:.2f} ms")

        tab1, tab2, tab3, tab4 = st.tabs(
            ["📅 По дням", "👥 По юзерам", "📦 Товары", "🎯 Сегменты"]
        )

        with tab1:
            st.subheader("📅 Продажи по дням")
            sales_by_day = result.get("sales_by_day", {})
            for day, total in sorted(sales_by_day.items())[-7:]:
                st.write(f"**{day}**: {format_price(total)}")

        with tab2:
            st.subheader("👥 Продажи по пользователям")
            sales_by_user = result.get("sales_by_user", {})
            for uid, total in sorted(
                sales_by_user.items(), key=lambda x: x[1], reverse=True
            )[:10]:
                st.write(f"**{uid}**: {format_price(total)}")

        with tab3:
            st.subheader("📦 Топ товары")
            for item in result.get("top_products", [])[:10]:
                st.write(
                    f"**{item['title']}**: {item['quantity_sold']} шт, {format_price(item['revenue'])}"
                )

        with tab4:
            st.subheader("🎯 Сегменты клиентов")
            segments = result.get("customer_segments", {})
            for segment, user_ids in segments.items():
                st.write(f"**{segment.upper()}**: {len(user_ids)} пользователей")


# ============ PAGE: TESTS DEMO ============
elif page == "🧪 Tests Demo":
    st.header("🧪 Демонстрация тестов")

    st.markdown(
        """
    Для запуска тестов используйте команду:
    ```bash
    pytest -v
    ```
    """
    )

    if st.button("▶️ Запустить тесты (демо)", key="run_tests"):
        st.code(
            """
# Пример теста из test_lab4.py
def test_maybe_some_and_none_behavior():
    just = Maybe.some(42)
    nothing = Maybe.nothing()
    
    assert not just.is_none()
    assert nothing.is_none()
    assert just.get_or_else(0) == 42
    assert nothing.get_or_else(0) == 0
    
✅ PASSED
        """,
            language="python",
        )

    st.divider()

    st.markdown("### 📋 Список тестов")
    tests = {
        "test_lab1.py": "Чистые функции, HOF, иммутабельность",
        "test_lab2.py": "Замыкания, рекурсия",
        "test_lab3.py": "Мемоизация, lru_cache",
        "test_lab4.py": "Maybe/Either",
        "test_lab5.py": "Ленивые вычисления",
        "test_lab6.py": "FRP, EventBus",
        "test_lab7.py": "Композиция, сервисы",
        "test_lab8.py": "Async, параллелизм",
    }

    for test_file, description in tests.items():
        st.success(f"✅ **{test_file}**: {description}")
