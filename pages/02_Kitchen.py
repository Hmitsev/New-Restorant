import streamlit as st

from streamlit_autorefresh import st_autorefresh
from database.db import get_connection


# =====================================
# НАСТРОЙКИ
# =====================================

st.set_page_config(
    page_title="Кухня",
    page_icon="👨‍🍳",
    layout="wide"
)
# =====================================
# ДОСТЪП ДО КУХНЯ
# =====================================

KITCHEN_PASSWORD = "kitchen2026"

if "kitchen_auth" not in st.session_state:
    st.session_state.kitchen_auth = False

if not st.session_state.kitchen_auth:

    password = st.text_input(
        "Парола",
        type="password"
    )

    if st.button("Вход"):

        if password == KITCHEN_PASSWORD:

            st.session_state.kitchen_auth = True
            st.rerun()

    st.stop()

# =====================================
# КАТАЛОГ НА ДНЕВНОТО МЕНЮ
# =====================================

def get_daily_menu_catalog():

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT
                id,
                item_name,
                price,
                COALESCE(daily_group, ''),
                COALESCE(available_today, FALSE)
            FROM menu_items
            WHERE is_daily_item = TRUE
              AND is_active = TRUE
            ORDER BY
                daily_group,
                item_name
            """
        )

        return cur.fetchall()

    finally:

        cur.close()
        conn.close()


# =====================================
# ЗАПИС НА ИЗБРАНОТО ДНЕВНО МЕНЮ
# =====================================

def save_daily_menu(selected_item_ids):

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            UPDATE menu_items
            SET available_today = FALSE
            WHERE is_daily_item = TRUE
            """
        )

        if selected_item_ids:

            cur.execute(
                """
                UPDATE menu_items
                SET available_today = TRUE
                WHERE id = ANY(%s)
                  AND is_daily_item = TRUE
                """,
                (list(selected_item_ids),)
            )

        conn.commit()
        st.cache_data.clear()

    except Exception:

        conn.rollback()
        raise

    finally:

        cur.close()
        conn.close()


# =====================================
# РЪЧНО ДОБАВЯНЕ КЪМ ДНЕВНОТО МЕНЮ
# =====================================

def add_custom_daily_item(
    item_name,
    price,
    daily_group
):

    clean_name = str(item_name).strip()

    if not clean_name:

        raise ValueError(
            "Въведете име на артикула."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT id
            FROM menu_categories
            WHERE category_name = 'Дневно меню'
            LIMIT 1
            """
        )

        category_result = cur.fetchone()

        if category_result is None:

            raise ValueError(
                "Категорията „Дневно меню“ не е намерена."
            )

        category_id = category_result[0]

        cur.execute(
            """
            SELECT id
            FROM menu_items
            WHERE category_id = %s
              AND LOWER(TRIM(item_name))
                  = LOWER(TRIM(%s))
            LIMIT 1
            """,
            (
                category_id,
                clean_name
            )
        )

        existing_item = cur.fetchone()

        if existing_item:

            cur.execute(
                """
                UPDATE menu_items
                SET
                    price = %s,
                    daily_group = %s,
                    department = 'kitchen',
                    is_daily_item = TRUE,
                    available_today = TRUE,
                    is_active = TRUE
                WHERE id = %s
                """,
                (
                    float(price),
                    daily_group,
                    existing_item[0]
                )
            )

        else:

            cur.execute(
                """
                INSERT INTO menu_items
                (
                    category_id,
                    item_name,
                    price,
                    description,
                    department,
                    daily_group,
                    is_daily_item,
                    available_today,
                    is_active
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    '',
                    'kitchen',
                    %s,
                    TRUE,
                    TRUE,
                    TRUE
                )
                """,
                (
                    category_id,
                    clean_name,
                    float(price),
                    daily_group
                )
            )

        conn.commit()
        st.cache_data.clear()

    except Exception:

        conn.rollback()
        raise

    finally:

        cur.close()
        conn.close()

# =====================================
# ЗАГЛАВИЕ И ДНЕВНО МЕНЮ
# =====================================

title_col, daily_menu_col = st.columns([5, 2])

with title_col:

    st.title("👨‍🍳 Кухня")

with daily_menu_col:

    with st.popover(
        "📅 Дневно меню",
        use_container_width=True
    ):

        st.markdown(
            "### 📅 Управление на дневното меню"
        )

        daily_catalog = get_daily_menu_catalog()

        daily_labels = {
            row[0]: (
                f"{row[3]} | "
                f"{row[1]} | "
                f"€ {float(row[2]):.2f}"
            )
            for row in daily_catalog
        }

        daily_ids = [
            row[0]
            for row in daily_catalog
        ]

        active_daily_ids = [
            row[0]
            for row in daily_catalog
            if row[4]
        ]

        selected_daily_ids = st.multiselect(
            "Избери предложенията за деня",
            options=daily_ids,
            default=active_daily_ids,
            format_func=lambda item_id:
                daily_labels.get(
                    item_id,
                    str(item_id)
                ),
            key="selected_daily_menu_items"
        )

        if st.button(
            "💾 Запази дневното меню",
            use_container_width=True,
            type="primary",
            key="save_daily_menu"
        ):

            save_daily_menu(
                selected_daily_ids
            )

            st.success(
                "Дневното меню е обновено."
            )

            st.rerun()

        st.divider()

        st.markdown(
            "### 🗑️ Изтрий артикул"
        )

        delete_item_id = st.selectbox(
            "Избери артикул за изтриване",
            options=daily_ids,
            format_func=lambda item_id:
                daily_labels.get(
                    item_id,
                    str(item_id)
                ),
            key="delete_daily_item"
        )
        if st.button(
            "🗑️ Изтрий избрания артикул",
            use_container_width=True,
            key="delete_daily_menu_item"
        ):
        
            try:
        
                conn = get_connection()
                cur = conn.cursor()
        
                cur.execute(
                    """
                    DELETE FROM menu_items
                    WHERE id = %s
                      AND is_daily_item = TRUE
                    """,
                    (delete_item_id,)
                )
        
                conn.commit()
        
                cur.close()
                conn.close()
        
                st.success(
                    "Артикулът е изтрит."
                )
        
                st.rerun()
        
            except Exception as error:
        
                st.error(
                    f"Грешка при изтриване: {error}"
                )

        st.divider()

        st.markdown(
            "### ➕ Нов артикул"
        )

        custom_daily_group = st.selectbox(
            "Секция",
            [
                "🍲 Супи",
                "🍽️ Готови ястия",
                "🍰 Десерт"
            ],
            key="custom_daily_group"
        )

        custom_daily_name = st.text_input(
            "Име на артикула",
            placeholder="Например: Крем супа от броколи",
            key="custom_daily_name"
        )

        custom_daily_price = st.number_input(
            "Цена в евро",
            min_value=0.00,
            step=0.10,
            format="%.2f",
            key="custom_daily_price"
        )

        if st.button(
            "➕ Добави и активирай",
            use_container_width=True,
            key="add_custom_daily_item"
        ):

            try:

                add_custom_daily_item(
                    item_name=custom_daily_name,
                    price=custom_daily_price,
                    daily_group=custom_daily_group
                )

                st.success(
                    "Артикулът е добавен към дневното меню."
                )

                st.rerun()

            except Exception as error:

                st.error(
                    f"Грешка при добавяне: {error}"
                )

# =====================================
# АВТОМАТИЧНО ОБНОВЯВАНЕ
# =====================================

st_autorefresh(
    interval=15000,
    key="kitchen_refresh"
)

# =====================================
# ЗАРЕЖДАНЕ НА АКТИВНИТЕ ПОРЪЧКИ
# =====================================

def get_kitchen_orders():

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
                oi.id AS order_item_id,
                mi.item_name,
                oi.quantity,
                oi.notes,
                oi.kitchen_status
            FROM orders o
            JOIN restaurant_tables rt
                ON rt.id = o.table_id
            JOIN order_items oi
                ON oi.order_id = o.id
            JOIN menu_items mi
                ON mi.id = oi.item_id
            WHERE o.order_status <> 'COMPLETED'
              AND mi.department = 'kitchen'
              AND oi.kitchen_status IN (
                  'NEW',
                  'PREPARING',
                  'READY'
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
# СТАТУС НА ЕДИН АРТИКУЛ
# =====================================

def update_item_status(order_item_id, new_status):

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            UPDATE order_items
            SET kitchen_status = %s
            WHERE id = %s
            """,
            (
                new_status,
                order_item_id
            )
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# =====================================
# ВСИЧКИ АРТИКУЛИ В ПОДГОТОВКА
# =====================================

def start_order(order_id):

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            UPDATE order_items
            SET kitchen_status = 'PREPARING'
            WHERE order_id = %s
              AND kitchen_status = 'NEW'
            """,
            (order_id,)
        )

        cur.execute(
            """
            UPDATE orders
            SET
                order_status = 'IN_PROGRESS',
                updated_at = CURRENT_TIMESTAMP
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
# ЦЯЛАТА ПОРЪЧКА Е ГОТОВА
# =====================================

def finish_order(order_id):

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            UPDATE order_items
            SET kitchen_status = 'READY'
            WHERE order_id = %s
              AND kitchen_status IN (
                  'NEW',
                  'PREPARING'
              )
            """,
            (order_id,)
        )

        cur.execute(
            """
            UPDATE orders
            SET
                order_status = 'READY',
                updated_at = CURRENT_TIMESTAMP
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
# ГРУПИРАНЕ ПО ПОРЪЧКА
# =====================================

rows = get_kitchen_orders()
active_count = len(set(row[0] for row in rows))

st.info(
    f"👨‍🍳 Активни поръчки: {active_count}"
)
orders = {}

for row in rows:

    order_id = row[0]
    table_number = row[1]
    created_at = row[2]
    order_status = row[3]

    order_item = {
        "row_id": row[4],
        "name": row[5],
        "quantity": row[6],
        "notes": row[7],
        "status": row[8]
    }

    if order_id not in orders:

        orders[order_id] = {
            "table_number": table_number,
            "created_at": created_at,
            "order_status": order_status,
            "items": []
        }

    orders[order_id]["items"].append(order_item)


# =====================================
# ПОКАЗВАНЕ
# =====================================

if not orders:

    st.success("Няма активни поръчки.")

else:

    for order_id, order_data in orders.items():

        table_number = order_data["table_number"]
        created_at = order_data["created_at"]
        order_status = order_data["order_status"]
        items = order_data["items"]

        with st.container(border=True):

            title_col, time_col = st.columns([4, 2])

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

            with time_col:

                if created_at:

                    from datetime import timedelta

                    local_time = created_at + timedelta(hours=3)
                    
                    st.caption(
                        "Получена: "
                        f"{local_time.strftime('%H:%M:%S')}"
                    )

            # =====================================
            # ОБЩ СТАТУС
            # =====================================

            if order_status == "NEW":

                st.error("🔴 НОВА ПОРЪЧКА")

            elif order_status == "IN_PROGRESS":

                st.warning("🟡 В ПОДГОТОВКА")

            elif order_status == "READY":

                st.success("🟢 ГОТОВА ПОРЪЧКА")

            st.markdown("#### Артикули")

            # =====================================
            # АРТИКУЛИ С ОТМЕТКИ
            # =====================================

            for item in items:

                item_row_id = item["row_id"]
                item_name = item["name"]
                quantity = item["quantity"]
                notes = item["notes"]
                item_status = item["status"]

                item_col, status_col = st.columns(
                    [5, 2],
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

                    if item_status == "NEW":
                        st.error("🔴 Нова")
                
                    elif item_status == "PREPARING":
                        st.warning("🟡 Приготвя се")
                
                    elif item_status == "READY":
                        st.success("🟢 Готово")


                if item_status == "NEW":

                    st.caption("🔴 Не е започнато")

                elif item_status == "PREPARING":

                    st.caption("🟡 Приготвя се")

                elif item_status == "READY":

                    st.caption("🟢 Готово")

                st.divider()

            # =====================================
            # БУТОНИ ЗА ЦЯЛАТА ПОРЪЧКА
            # =====================================

            preparing_col, ready_col = st.columns(2)

            with preparing_col:

                if st.button(
                    "🟡 Приготвя се",
                    key=f"start_order_{order_id}",
                    use_container_width=True
                ):

                    start_order(order_id)

                    st.rerun()

            with ready_col:

                if st.button(
                    "✅ Цялата поръчка е готова",
                    key=f"finish_order_{order_id}",
                    type="primary",
                    use_container_width=True
                ):

                    finish_order(order_id)

                    st.rerun()
