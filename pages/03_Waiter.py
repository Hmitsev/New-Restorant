import streamlit as st

from streamlit_autorefresh import st_autorefresh
from database.db import get_connection


# =====================================
# НАСТРОЙКИ НА СТРАНИЦАТА
# =====================================

st.set_page_config(
    page_title="Сервитьор",
    page_icon="🤵",
    layout="wide"
)
# =====================================
# ДОСТЪП ДО СЕРВИТЬОР
# =====================================

WAITER_PASSWORD = "waiter2026"

if "waiter_auth" not in st.session_state:
    st.session_state.waiter_auth = False

if not st.session_state.waiter_auth:

    password = st.text_input(
        "Парола",
        type="password"
    )

    if st.button("Вход"):

        if password == WAITER_PASSWORD:

            st.session_state.waiter_auth = True
            st.rerun()

    st.stop()
# =====================================
# ЗАГЛАВИЕ
# =====================================
st.title("🤵 Сервитьор")
# =====================================
# ИСТОРИЯ НА ПРИКЛЮЧЕНИ ПОРЪЧКИ (24Ч)
# =====================================

def get_completed_orders():

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                o.id AS order_id,
                rt.table_number,
                o.created_at,
                o.order_status,
                o.total_amount,
                oi.id AS order_item_id,
                mi.item_name,
                oi.quantity,
                oi.notes,
                mi.department,
                oi.kitchen_status
            FROM orders o
            JOIN restaurant_tables rt
                ON rt.id = o.table_id
            JOIN order_items oi
                ON oi.order_id = o.id
            JOIN menu_items mi
                ON mi.id = oi.item_id
            WHERE o.order_status = 'COMPLETED'
              AND o.completed_at >= NOW() - INTERVAL '24 HOURS'
            ORDER BY
                o.completed_at DESC,
                o.id DESC,
                oi.id ASC
        """)

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()

# =====================================
# ЗАРЕЖДАНЕ НА АКТИВНИ ПОРЪЧКИ
# =====================================

def get_waiter_orders():

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                o.id AS order_id,
                rt.table_number,
                o.created_at,
                o.order_status,
                o.total_amount,
                oi.id AS order_item_id,
                mi.item_name,
                oi.quantity,
                oi.notes,
                mi.department,
                oi.kitchen_status
            FROM orders o
            JOIN restaurant_tables rt
                ON rt.id = o.table_id
            JOIN order_items oi
                ON oi.order_id = o.id
            JOIN menu_items mi
                ON mi.id = oi.item_id
            WHERE o.order_status <> 'COMPLETED'
              AND oi.kitchen_status IN (
                  'NEW',
                  'PREPARING',
                  'READY',
                  'SERVED'
              )
            ORDER BY
                o.created_at ASC,
                o.id ASC,
                oi.id ASC
            """
        )

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()


# =====================================
# БРОЙ АКТИВНИ ПОРЪЧКИ
# =====================================

active_rows = get_waiter_orders()

active_count = len(
    set(row[0] for row in active_rows)
)


# =====================================
# АВТОМАТИЧНО ОБНОВЯВАНЕ
# =====================================

st_autorefresh(
    interval=15000,
    key="waiter_refresh"
)

view_mode = st.radio(
    "Изглед",
    [
        f"🤵 Активни поръчки ({active_count})",
        "📜 История (24ч)"
    ],
    horizontal=True,
    label_visibility="collapsed",
    key="waiter_view_mode"
)

# =====================================
# CALLBACK ЗА ЧЕКБОКСА
# =====================================

def handle_served_checkbox(
    order_item_id,
    checkbox_key,
    department
):
    pass

# =====================================
# ФИНАЛИЗИРАНЕ НА ПОРЪЧКА
# =====================================

def complete_order(order_id):

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            UPDATE orders
            SET
                order_status = 'COMPLETED',
                updated_at = CURRENT_TIMESTAMP,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (order_id,)
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

# =====================================
# ИЗВЕСТИЯ
# =====================================
def get_waiter_notifications():

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT
                id,
                table_id,
                notification_type,
                message,
                created_at
            FROM notifications
            WHERE is_read = FALSE
             AND notification_type = 'CALL_WAITER'
            ORDER BY created_at DESC
            """
        )

        return cur.fetchall()

    finally:

        cur.close()
        conn.close()



def mark_notification_read(notification_id):

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            UPDATE notifications
            SET is_read = TRUE
            WHERE id = %s
            """,
            (notification_id,)
        )

        conn.commit()

    finally:

        cur.close()
        conn.close()
# =====================================
# ИЗВЕСТИЯ НА СЕРВИТЬОРА
# =====================================

notifications = get_waiter_notifications()

if notifications:

    st.subheader("🔔 Известия")

    for notification in notifications:

        notification_id = notification[0]
        message = notification[3]
        created_at = notification[4]

        with st.container(border=True):

            st.warning(
                f"🔔 {message}"
            )

            st.caption(
                f"⏰ {created_at.strftime('%H:%M:%S')}"
            )

            if st.button(
                "✅ Обработено",
                key=f"notif_{notification_id}",
                use_container_width=True
            ):

                mark_notification_read(
                    notification_id
                )

                st.rerun()

    st.divider()

# =====================================
# ЗАРЕЖДАНЕ И ГРУПИРАНЕ ПО ПОРЪЧКА
# =====================================

if view_mode.startswith("🤵 Активни поръчки"):

    rows = active_rows

else:

    rows = get_completed_orders()


orders = {}

for row in rows:
    order_id = row[0]

    if order_id not in orders:
        orders[order_id] = {
            "table_number": row[1],
            "created_at": row[2],
            "order_status": row[3],
            "total_amount": row[4],
            "items": []
        }

    orders[order_id]["items"].append(
        {
            "row_id": row[5],
            "name": row[6],
            "quantity": row[7],
            "notes": row[8],
            "department": row[9],
            "status": row[10]
        }
    )


# =====================================
# ПОКАЗВАНЕ НА ПОРЪЧКИТЕ
# =====================================

if not orders:
    st.success("Няма активни поръчки.")

else:

    for order_id, order_data in orders.items():

        table_number = order_data["table_number"]
        created_at = order_data["created_at"]
        total_amount = order_data["total_amount"]
        items = order_data["items"]

        with st.container(border=True):

            title_col, details_col, waiter_col = st.columns([4, 2, 2])

            with title_col:

                st.subheader(
                    f"🍽️ Поръчка №{order_id}"
                )

                st.markdown(
                    f"""
                    <div style="
                        color:#FF8C42;
                        font-size:34px;
                        font-weight:800;
                        margin-top:5px;
                        margin-bottom:10px;
                    ">
                       Маса № {table_number}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with details_col:

                if created_at:

                    from datetime import timedelta

                    local_time = created_at + timedelta(hours=3)
                    
                    st.caption(
                        "Получена: "
                        f"{local_time.strftime('%H:%M:%S')}"
                    )

                if total_amount is not None:

                    st.markdown(
                        f"**Общо: € {float(total_amount):.2f}**"
                    )

            with waiter_col:

                selected_waiter = st.selectbox(
                    "🤵 Сервитьор",
                    [
                        "Сервитьор 1",
                        "Сервитьор 2",
                        "Сервитьор 3",
                        "Сервитьор 4",
                        "Сервитьор 5"
                    ],
                    key=f"waiter_{order_id}"
                )
            # =====================================
            # ОБЩ СТАТУС
            # =====================================

            all_served_status = True
            all_ready_or_served = True
            
            for item in items:
            
                department = str(
                    item["department"] or ""
                ).lower()
            
                status = item["status"]
            
                # напитките винаги са готови
                if department == "bar":
                    continue
            
                if status != "SERVED":
                    all_served_status = False
            
                if status not in ("READY", "SERVED"):
                    all_ready_or_served = False

            any_preparing = any(
                item["status"] == "PREPARING"
                for item in items
            )

            if all_served_status:
                st.success(
                    "✅ ВСИЧКИ АРТИКУЛИ СА СЕРВИРАНИ"
                )
            elif all_ready_or_served:
                st.success(
                    "🟢 ПОРЪЧКАТА Е ГОТОВА"
                )
            elif any_preparing:
                st.warning(
                    "🟡 ПОРЪЧКАТА Е В ПОДГОТОВКА"
                )
            else:
                st.error(
                    "🔴 НОВА ПОРЪЧКА"
                )

            # =====================================
            # АРТИКУЛИ И ЧЕКБОКСИ
            # =====================================

            st.markdown("#### Артикули")

            for item in items:
                item_row_id = item["row_id"]
                item_name = item["name"]
                quantity = item["quantity"]
                notes = item["notes"]
                department = str(
                    item["department"] or ""
                ).lower()
                item_status = item["status"]

                item_col, status_col, served_col = st.columns(
                    [5, 2, 2],
                    vertical_alignment="center"
                )

                with item_col:
                    st.write(
                        f"**{item_name} x{quantity}**"
                    )

                    if notes:
                        st.caption(
                            f"📝 Коментар: {notes}"
                        )

                with status_col:
                    if item_status == "SERVED":
                        st.info("✅ Сервирано")
                    elif department == "bar":
                        st.info("🥛 Напитка")
                    elif item_status == "NEW":
                        st.error("🔴 Нова")
                    elif item_status == "PREPARING":
                        st.warning("🟡 Приготвя се")
                    elif item_status == "READY":
                        st.success("🟢 Готово")

                with served_col:
                    checkbox_key = (
                        f"waiter_served_{order_id}_{item_row_id}"
                    )

                    is_bar_item = department == "bar"

                    can_be_served = (
                        is_bar_item
                        or item_status in ("READY", "SERVED")
                    )

                    st.checkbox(
                        "Сервирано",
                        value=False,
                        disabled=False,
                        key=checkbox_key
                    )
                    
                    st.divider()

            # =====================================
            # ОБОБЩЕНИЕ
            # =====================================

            ready_count = sum(
                1
                for item in items
                if item["status"] == "READY"
            )

            served_count = sum(
                1
                for item in items
                if item["status"] == "SERVED"
            )

            total_count = len(items)

            progress_col1, progress_col2 = st.columns(2)

            with progress_col1:
                st.write(
                    f"🟢 Готови за сервиране: {ready_count}"
                )

            with progress_col2:
                st.write(
                    f"✅ Сервирани: {served_count}/{total_count}"
                )

            if total_count > 0:
                st.progress(
                    served_count / total_count
                )

            

            # =====================================
            # ФИНАЛЕН БУТОН
            # =====================================

            if st.button(
                "✅ Финализирай поръчката",
                key=f"complete_{order_id}",
                type="primary",
                disabled=not all_ready_or_served,
                use_container_width=True
            ):
                try:
                    complete_order(order_id)

                    st.rerun()

                except Exception as error:
                    st.error(
                        f"Грешка при финализиране: {error}"
                    )

            if not all_ready_or_served:
                st.caption(
                    "Финализирането ще се активира, "
                    "когато всички артикули са отбелязани "
                    "като сервирани."
                )
