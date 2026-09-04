import streamlit as st

from database.db import get_connection


# =====================================
# КАТЕГОРИИ
# =====================================

@st.cache_data(ttl=3600)

def get_categories():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT DISTINCT
                category_name,
                sort_order
            FROM menu_categories
            ORDER BY sort_order, category_name
            """
        )

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()


# =====================================
# АРТИКУЛИ ПО КАТЕГОРИЯ
# =====================================

@st.cache_data(ttl=1)
def get_items_by_category(category_name):

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT DISTINCT ON (mi.sort_order, mi.item_name)
                mi.id,
                mi.item_name,
                mi.price,
                COALESCE(mi.description, ''),
                COALESCE(mi.drink_group, ''),
                COALESCE(mi.wine_type, ''),
                COALESCE(mi.alcohol_type, ''),
                COALESCE(mi.daily_group, '')
            FROM menu_items mi
            JOIN menu_categories mc
                ON mc.id = mi.category_id
            WHERE mc.category_name = %s
              AND mi.is_active = TRUE
              AND (
                    mc.category_name <> 'Дневно меню'
                    OR COALESCE(mi.available_today, FALSE) = TRUE
              )
            ORDER BY
                mi.sort_order,
                mi.item_name,
                mi.id
            """,
            (category_name,)
        )

        return cur.fetchall()

    finally:

        cur.close()
        conn.close()
# =====================================
# СЪЗДАВАНЕ НА ПОРЪЧКА
# =====================================

def create_order(table_number, cart):
    if not cart:
        raise ValueError("Количката е празна.")

    try:
        table_number = int(table_number)
    except (TypeError, ValueError) as error:
        raise ValueError("Невалиден номер на маса.") from error

    if table_number < 1 or table_number > 20:
        raise ValueError(
            "Номерът на масата трябва да бъде между 1 и 20."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Намираме вътрешното ID на масата
        cur.execute(
            """
            SELECT id
            FROM restaurant_tables
            WHERE table_number = %s
              AND is_active = TRUE
            LIMIT 1
            """,
            (table_number,)
        )

        table_result = cur.fetchone()

        if table_result is None:
            raise ValueError(
                f"Маса № {table_number} не е намерена или не е активна."
            )

        table_id = table_result[0]

        # Групиране по артикул и коментар
        # Еднакви ястия с различни коментари остават отделни позиции
        grouped_items = {}

        for cart_item in cart:
            item_id = int(cart_item["id"])
            item_name = str(cart_item["name"])
            price = float(cart_item["price"])
            note = str(cart_item.get("note", "")).strip()

            group_key = (item_id, note)

            if group_key not in grouped_items:
                grouped_items[group_key] = {
                    "id": item_id,
                    "name": item_name,
                    "price": price,
                    "note": note,
                    "quantity": 0
                }

            grouped_items[group_key]["quantity"] += 1

        total_amount = sum(
            grouped_item["price"] * grouped_item["quantity"]
            for grouped_item in grouped_items.values()
        )

        # Създаваме основната поръчка
        cur.execute(
            """
            INSERT INTO orders
            (
                table_id,
                total_amount,
                order_status
            )
            VALUES
            (
                %s,
                %s,
                'NEW'
            )
            RETURNING id
            """,
            (
                table_id,
                total_amount
            )
        )

        order_id = cur.fetchone()[0]

        # Записваме отделните позиции
        for grouped_item in grouped_items.values():
            cur.execute(
                """
                INSERT INTO order_items
                (
                    order_id,
                    item_id,
                    quantity,
                    notes,
                    kitchen_status,
                    bar_status
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    'NEW',
                    'NEW'
                )
                """,
                (
                    order_id,
                    grouped_item["id"],
                    grouped_item["quantity"],
                    (
                        grouped_item["note"]
                        if grouped_item["note"]
                        else None
                    )
                )
            )

        # Известие за новата поръчка
        cur.execute(
            """
            INSERT INTO notifications
            (
                table_id,
                notification_type,
                message,
                is_read
            )
            VALUES
            (
                %s,
                'NEW_ORDER',
                %s,
                FALSE
            )
            """,
            (
                table_id,
                (
                    f"Нова поръчка №{order_id} "
                    f"от маса №{table_number}"
                )
            )
        )

        conn.commit()

        return order_id

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()
# =====================================
# ФИНАЛИЗИРАНИ ПОРЪЧКИ (24 ЧАСА)
# =====================================

def get_completed_orders():

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT
                o.id,
                t.table_number,
                o.created_at,
                o.order_status,
                o.total_amount,
                NULL,
                'Финализирана поръчка',
                0,
                NULL,
                NULL,
                'COMPLETED'
            FROM orders o
            JOIN restaurant_tables t
                ON t.id = o.table_id
            WHERE o.order_status = 'COMPLETED'
              AND o.created_at >=
                  NOW() - INTERVAL '24 HOURS'
            ORDER BY o.created_at DESC
            """
        )

        return cur.fetchall()

    finally:

        cur.close()
        conn.close()
