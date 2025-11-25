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
    total_sales,
    by_category,
    by_price_range,
    by_tag,
    top_products,
    safe_product,
    validate_order,
)
from core.service import CatalogService, OrderService, AnalyticsService


# Кэширование загрузки данных
@st.cache_data
def get_data():
    return load_seed("data/seed.json")


# Инициализация состояния
if "cart" not in st.session_state:
    categories, products, users, orders = get_data()
    st.session_state.cart = Cart(id="cart_default", user_id=users[0].id, items=())
else:
    categories, products, users, orders = get_data()


# Настройки интерфейса
st.set_page_config(page_title="FP Shop Analytics", layout="wide")
st.title("Функциональный интернет-магазин")
st.caption("Проект: Алмаз, Нурдаулет, Бакашар — лабораторные 1–2")


# Вкладки
tab_overview, tab_catalog, tab_cart, tab_stats, tab_reports = st.tabs(
    ["Overview", "Каталог", "Корзина", "Статистика", "Reports"]
)

# OVERVIEW
with tab_overview:
    st.header("📦 Общая информация")
    st.metric("Категорий", len(categories))
    st.metric("Товаров", len(products))
    st.metric("Пользователей", len(users))
    st.metric("Заказов", len(orders))

    total = total_sales(tuple(o for o in orders if o.status == "paid"))
    st.metric("💰 Общая сумма продаж", f"{total / 100:.2f} ₸")


# КАТАЛОГ
with tab_catalog:
    st.header("🛒 Каталог товаров")

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_category = st.selectbox(
            "Категория", ["Все"] + [c.name for c in categories], index=0
        )
    with col2:
        # Фильтр по диапазону цен от 0 до 2000
        min_price, max_price = st.slider(
            "Диапазон цены (₸)", 0, 2000, (0, 2000), step=10
        )
    with col3:
        all_tags = sorted({t for p in products for t in p.tags})
        selected_tag = st.selectbox("Тег", ["Все"] + all_tags, index=0)

    # Преобразование фильтров в копейки
    min_price_kop, max_price_kop = min_price * 100, max_price * 100

    # Замыкания-фильтры
    category_filter = (
        by_category(
            next((c.id for c in categories if c.name == selected_category), None)
        )
        if selected_category != "Все"
        else lambda _: True
    )
    price_filter = by_price_range(min_price_kop, max_price_kop)
    tag_filter = by_tag(selected_tag) if selected_tag != "Все" else lambda _: True

    # Применяем рекурсию и фильтры
    filtered_products = tuple(
        filter(
            lambda p: category_filter(p) and price_filter(p) and tag_filter(p),
            products,
        )
    )

    st.markdown(f"### Найдено товаров: {len(filtered_products)}")
    st.divider()

    # Вывод карточек
    for p in filtered_products:
        with st.container():
            cols = st.columns([4, 2, 2, 2])
            with cols[0]:
                st.markdown(f"**{p.title}**")
                st.caption(f"Теги: {', '.join(p.tags)}")
            with cols[1]:
                st.write(f"{p.price / 100:.2f} ₸")
            with cols[2]:
                qty = st.number_input(
                    "Кол-во",
                    min_value=1,
                    value=1,
                    key=f"qty_{p.id}",
                    label_visibility="collapsed",
                )
            with cols[3]:
                if st.button("🛒 Добавить", key=f"add_{p.id}"):
                    st.session_state.cart = add_to_cart(
                        st.session_state.cart, p.id, qty
                    )
                    st.success(f"Добавлено: {p.title} × {qty}", icon="✅")
            st.markdown("---")

    # Базовые фильтры
    category_filter = (
        by_category(
            next((c.id for c in categories if c.name == selected_category), None)
        )
        if selected_category != "Все"
        else lambda _: True
    )
    price_filter = by_price_range(min_price, max_price)
    tag_filter = by_tag(selected_tag) if selected_tag != "Все" else lambda _: True

    # Применяем рекурсию и фильтры
    filtered_products = tuple(
        filter(
            lambda p: category_filter(p) and price_filter(p) and tag_filter(p),
            products,
        )
    )

    st.markdown(f"### Найдено товаров: {len(filtered_products)}")
    st.divider()

    # Вывод карточек
    for p in filtered_products:
        with st.container():
            cols = st.columns([4, 2, 2, 2])
            with cols[0]:
                st.markdown(f"**{p.title}**")
                st.caption(f"Теги: {', '.join(p.tags)}")
            with cols[1]:
                st.write(f"{p.price / 100:.2f} ₸")
            with cols[2]:
                qty = st.number_input(
                    "Кол-во",
                    min_value=1,
                    value=1,
                    key=f"qty_{p.id}",
                    label_visibility="collapsed",
                )
            with cols[3]:
                if st.button("🛒 Добавить", key=f"add_{p.id}"):
                    st.session_state.cart = add_to_cart(
                        st.session_state.cart, p.id, qty
                    )
                    st.success(f"Добавлено: {p.title} × {qty}", icon="✅")
            st.markdown("---")


# КОРЗИНА
with tab_cart:
    st.header("🧺 Ваша корзина")

    cart = st.session_state.cart

    if not cart.items:
        st.info("Корзина пуста. Перейдите в каталог, чтобы добавить товары.")
    else:
        total_sum = reduce(
            lambda acc, item: acc
            + next(p.price for p in products if p.id == item[0]) * item[1],
            cart.items,
            0,
        )

        st.markdown("### Содержимое корзины:")
        for pid, qty in cart.items:
            product = next((p for p in products if p.id == pid), None)
            if product:
                cols = st.columns([5, 2, 1])
                with cols[0]:
                    st.write(f"{product.title}")
                with cols[1]:
                    st.write(f"× {qty} = {(product.price * qty) / 100:.2f} ₸")
                with cols[2]:
                    if st.button("✖", key=f"remove_{pid}"):
                        st.session_state.cart = remove_from_cart(cart, pid)
                        st.warning(f"Товар {product.title} удалён", icon="⚠️")

        st.divider()
        st.markdown(f"### 💰 Итого: {total_sum / 100:.2f} ₸")

        # Кнопка оформления заказа
        if st.button("✅ Оформить заказ"):
            new_order = checkout(cart, ts="2025-10-14T12:00:00", products=products)
            st.success(f"Заказ оформлен на сумму {new_order.total / 100:.2f} ₸!")

            # Очистка корзины после оформления
            st.session_state.cart = Cart(
                id="cart_default",
                user_id=users[0].id,
                items=(),
            )

# СТАТИСТИКА
with tab_stats:
    st.header("Статистика пользователей и продаж")

    vip_users = [u for u in users if u.tier == "VIP"]
    regular_users = [u for u in users if u.tier == "regular"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("👑 VIP-пользователей", len(vip_users))
    with col2:
        st.metric("👤 Обычных пользователей", len(regular_users))

    st.metric("Всего заказов", len(orders))
    st.metric("Оплаченных заказов", len([o for o in orders if o.status == "paid"]))
    st.markdown("---")

    ## ленивые вычисления
    st.markdown("## Потоковая обработка заказов")

    from core.lazy import iter_orders_by_day, lazy_top_customers

    selected_day = st.text_input(
        "Введите день (YYYY-MM-DD):", "2025-06-22", key="lazy_day"
    )
    if st.button("Показать заказы за день", key="lazy_day_btn"):
        day_orders = list(iter_orders_by_day(orders, selected_day))
        st.info(f"Найдено заказов за {selected_day}: {len(day_orders)}")
        if day_orders:
            st.table(
                {
                    "Order ID": [o.id for o in day_orders],
                    "User ID": [o.user_id for o in day_orders],
                    "Total (₸)": [o.total / 100 for o in day_orders],
                }
            )
        else:
            st.warning("Заказы за указанный день не найдены.")

    st.divider()

    k = st.slider("Показать топ покупателей:", 1, 10, 5, key="lazy_top_slider")
    if st.button("Показать топ покупателей", key="lazy_top_btn"):

        from core.lazy import lazy_top_customers

        top = list(lazy_top_customers(orders, k))
        st.subheader("🏆 Топ покупателей")
        st.table(
            {
                "User ID": [u for u, _ in top],
                "Total (₸)": [t / 100 for _, t in top],
            }
        )

# Reports
with tab_reports:
    st.header("📈 Отчёты — Top Products (cached)")

    k = st.slider("Количество топ-товаров", 5, 20, 10)
    start = time.perf_counter()
    top_uncached = top_products.__wrapped__(orders, products, k)  # вызов без кэша
    uncached_time = (time.perf_counter() - start) * 1000

    start = time.perf_counter()
    top_cached = top_products(orders, products, k)  # кэшированный вызов
    cached_time = (time.perf_counter() - start) * 1000

    st.subheader("⏱ Время выполнения:")
    st.write(f"Без кэша: {uncached_time:.2f} ms")
    st.write(f"С кэшем: {cached_time:.2f} ms")

    st.markdown("### 🔝 Топовые товары по продажам:")
    for idx, p in enumerate(top_cached, start=1):
        st.write(f"{idx}. {p.title} — {p.price / 100:.2f} ₸")

    ## Tab Reports
    st.divider()

with tab_reports:
    st.header("🧩 Safe Operations Maybe/Either")

    st.markdown("### 🔍 Безопасный поиск товара")
    pid_input = st.text_input("Введите ID товара для поиска:", "p1")
    if st.button("Найти товар", key="find_product"):
        product_result = safe_product(products, pid_input)
        if product_result.is_none():
            st.warning(f"❌ Товар с ID `{pid_input}` не найден.")
        else:
            product = product_result.get_or_else(None)
            st.success(
                f"✅ Найден товар: **{product.title}**, {product.price / 100:.2f} ₸"
            )

    st.markdown("### ✅ Проверка заказа (Either)")
    fake_order = Order(
        id="order_ui",
        user_id=users[0].id,
        items=(("p1", 2), ("p2", 1)),
        total=0,
        ts="2025-10-21",
        status="pending",
    )

    stock = {"p1": 3, "p2": 0, "p3": 10}

    if st.button("Проверить заказ", key="check_order"):
        order_result = validate_order(fake_order, stock, ())
        if order_result.is_left:
            st.success("✅ Заказ успешно прошёл проверку — все товары в наличии!")
        else:
            error = order_result.get_or_else({})
            st.error(f"❌ Ошибка проверки: {error.get('error')}")

    st.divider()

with tab_reports:
    st.markdown("### 📆 Дневной отчёт")

    day = st.text_input("Введите дату (ГГГГ-ММ-ДД):", "2025-10-21")
    if st.button("Сформировать дневной отчёт"):
        catalog = CatalogService(categories, products)
        orders_svc = OrderService(orders)
        analytics = AnalyticsService(catalog, orders_svc)

        report = analytics.daily_report(day)

        st.subheader(f"🗓️ Отчёт за {day}")
        st.write(f"Заказов: {len(report['orders'])}")
        st.write(f"Суммарные продажи: {report['total_sales'] / 100:.2f} ₸")

        st.markdown("### 👥 Топ клиентов:")
        for uid, total in report["top_customers"]:
            st.write(f"• {uid}: {total / 100:.2f} ₸")
