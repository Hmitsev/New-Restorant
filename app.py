import streamlit as st
from database.db import get_connection
from database.queries import (
    get_categories,
    get_items_by_category,
    create_order
)
# =====================================
# НАСТРОЙКИ НА СТРАНИЦАТА
# =====================================
st.set_page_config(
   page_icon="🍽️",
    layout="wide"
)


# =====================================
# ВИЗИЯ
# =====================================

import base64

@st.cache_data
def get_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(
            f.read()
        ).decode()

bg_image = get_base64(
    "assets/Designer (4).png"
)

page_style = f"""
<style>

.stApp {{
    background-image:
        linear-gradient(
            rgba(0,0,0,0.72),
            rgba(0,0,0,0.72)
        ),
        url("data:image/png;base64,{bg_image}");

    background-size: cover;
    background-attachment: fixed;
    background-position: center;
    background-repeat: no-repeat;
}}

/* =====================================
   ЛУКСОЗНИ КАТЕГОРИИ
===================================== */

[data-testid="stSegmentedControl"] button {{

    background: rgba(
        15,
        23,
        42,
        0.90
    ) !important;

    border: 1px solid #2A3347 !important;

    border-radius: 14px !important;

    color: #EAEAEA !important;

    font-weight: 700 !important;

    min-height: 48px !important;

    padding-left: 16px !important;
    padding-right: 16px !important;
}}

[data-testid="stSegmentedControl"] button:hover {{

    border: 1px solid #FFD54F !important;

    color: #FFD54F !important;
}}

[data-testid="stSegmentedControl"] button[aria-pressed="true"] {{

    background: linear-gradient(
        135deg,
        #D4AF37,
        #FFD54F
    ) !important;

    color: #111111 !important;

    border: none !important;

    font-weight: 800 !important;

    box-shadow:
        0 0 12px rgba(
            255,
            213,
            79,
            0.35
        ) !important;
}}

/* =====================================
   СКРИВА STREAMLIT STATUS
===================================== */

[data-testid="stStatusWidget"] {{
    display: none !important;
}}

div[data-testid="stStatusWidget"] {{
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
}}

[data-testid="stSpinner"] {{
    display: none !important;
}}

.stSpinner {{
    display: none !important;
}}

/* =====================================
   ХЕДЪР
===================================== */

[data-testid="stHeader"] {{
    background: rgba(0,0,0,0);
}}

[data-testid="stToolbar"] {{
    right: 2rem;
}}

</style>
"""

st.markdown(
    page_style,
    unsafe_allow_html=True
)
# =====================================
# SESSION STATE
# =====================================

if "cart" not in st.session_state:
    st.session_state.cart = []

if "last_order_id" not in st.session_state:
    st.session_state.last_order_id = None


# =====================================
# ПОМОЩНИ ФУНКЦИИ
# =====================================

def add_to_cart(item_id, item_name, price, note=""):

    st.session_state.cart.append(
        {
            "id": int(item_id),
            "name": str(item_name),
            "price": float(price),
            "note": str(note).strip()
        }
    )


def remove_one_from_cart(item_id, note):

    for index, cart_item in enumerate(st.session_state.cart):

        same_item = cart_item["id"] == item_id

        same_note = (
            cart_item.get("note", "").strip()
            == note.strip()
        )

        if same_item and same_note:
            st.session_state.cart.pop(index)
            break

def call_waiter(table_number):

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            SELECT id
            FROM restaurant_tables
            WHERE table_number = %s
            LIMIT 1
            """,
            (table_number,)
        )

        result = cur.fetchone()

        if not result:
            return

        table_id = result[0]

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
                'CALL_WAITER',
                %s,
                FALSE
            )
            """,
            (
                table_id,
                f'Маса №{table_number} извика сервитьор'
            )
        )

        conn.commit()

    finally:

        cur.close()
        conn.close()
# =====================================
# ЗАГЛАВИЕ И БАНЕР
# =====================================



try:
    st.image(
        "assets/Ластория.фон.jpeg",
        use_container_width=True
    )
except Exception:
    st.warning(
        "Банерът не беше намерен, но менюто може да се използва."
    )


# =====================================
# МАСА ОТ QR КОДА
# =====================================

raw_table_number = st.query_params.get("table", "1")

try:
    table_number = int(raw_table_number)
except (TypeError, ValueError):
    table_number = 1

if table_number < 1 or table_number > 20:
    st.error(
        "Невалиден QR код. Номерът на масата трябва да бъде между 1 и 20."
    )
    st.stop()

st.success(
    f"🍽️ Маса № {table_number}"
)
st.caption(
    "📱 ↔️ За по-добра видимост завъртете телефона хоризонтално"
)
if st.button(
    "🔔 Извикай сервитьор",
    use_container_width=True
):

    call_waiter(table_number)

    st.success(
        "Сервитьорът е уведомен."
    )


# =====================================
# МЕНЮ
# =====================================

st.markdown(
    """
    <div style="
        border:2px solid #D4AF37;
        border-radius:16px;
        padding:14px 20px 50px 20px;
        margin-bottom:35px;
        background:linear-gradient(
            135deg,
            rgba(15,23,42,0.95),
            rgba(10,18,30,0.95)
        );
        box-shadow:
            0 0 12px rgba(212,175,55,0.25);
    ">
        <span style="
            color:#F5E6C8;
            font-size:32px;
            font-weight:800;
            letter-spacing:1px;
        ">
            📋 Меню
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

categories = get_categories()

category_display = {
    "Дневно меню": "📅 🔥 ДНЕВНО МЕНЮ",
    "Салати": "🥗 Салати",
    "Разядки и студени предястия": "🧀 Предястия",
    "Топли предложения за споделяне": "🍲 За споделяне",
    "Риба и морски дарове": "🦐 Морски дарове",
    "Паста и ризото": "🍝 Паста и ризото",
    "Приготвено на плоча": "🥩 На плоча",
    "Основни ястия": "🍖 Основни ястия",
    "От краче до уше": "🍗 От краче до уше",
    "Бургери": "🍔 Бургери",
    "Десерти": "🍰 Десерти",
    "Напитки": "🥂 Напитки"
}
category_grams = {
    "Салати": "400 гр.",
    "Разядки и студени предястия": "300 гр.",
    "Топли предложения за споделяне": "350 гр.",
    "Риба и морски дарове": "450 гр.",
    "Паста и ризото": "400 гр.",
    "Приготвено на плоча": "450 гр.",
    "Основни ястия": "450 гр.",
    "От краче до уше": "400 гр.",
    "Бургери": "450 гр.",
    "Десерти": "1 бр."
}
reverse_display = {
    value: key
    for key, value in category_display.items()
}

category_names = [
    category_display.get(
        category[0],
        category[0]
    )
    for category in categories
]

selected_display = st.segmented_control(
    "",
    category_names,
    default=category_names[0],
    key="main_category_selector"
)

selected_category = reverse_display.get(
    selected_display,
    selected_display
)
main_section_grams = category_grams.get(
    selected_category,
    ""
)

if main_section_grams:

    st.markdown(
        f"""
        <div style="
            color:#CFCFCF;
            font-size:16px;
            font-weight:600;
            margin-top:4px;
            margin-bottom:10px;
        ">
            ⚖️ {main_section_grams}
        </div>
        """,
        unsafe_allow_html=True
    )
items = get_items_by_category(
    selected_category
)
# =====================================
# ПОДКАТЕГОРИИ НА ДНЕВНОТО МЕНЮ
# =====================================

if selected_category == "Дневно меню":

    selected_daily_group = st.segmented_control(
        "",
        [
            "🍲 Супи",
            "🍽️ Готови ястия",
            "🍰 Десерт"
        ],
        default="🍲 Супи",
        key="daily_group_selector"
    )

    items = [
        item
        for item in items
        if len(item) > 7
        and item[7] == selected_daily_group
    ]

    st.markdown(
        f"""
        <div style="
            color:#FFD54F;
            font-size:22px;
            font-weight:700;
            margin-top:12px;
            margin-bottom:10px;
        ">
            {selected_daily_group}
        </div>
        """,
        unsafe_allow_html=True
    )
section_title = ""

# =====================================
# ПОДКАТЕГОРИИ НА НАПИТКИТЕ
# =====================================

if selected_category == "Напитки":

    selected_drink_group = st.segmented_control(
        "",
        [
            "☕ Топли напитки",
            "🥤 Безалкохолни",
            "🍺 Бира и сайдер",
            "🍷 Вина",
            "🥃 Алкохол"
        ],
        default="☕ Топли напитки",
        key="drink_group_selector"
    )

    items = [
        item
        for item in items
        if len(item) > 4
        and item[4] == selected_drink_group
    ]

    section_title = selected_drink_group

    # =====================================
    # ПОДКАТЕГОРИИ НА ВИНАТА
    # =====================================

    if selected_drink_group == "🍷 Вина":

        selected_wine_type = st.segmented_control(
            "",
            [
                "🤍 Бели вина",
                "🍷 Червени вина",
                "🌹 Розе",
                "🥂 Просеко"
            ],
            default="🤍 Бели вина",
            key="wine_type_selector"
        )

        items = [
            item
            for item in items
            if len(item) > 5
            and item[5] == selected_wine_type
        ]

        section_title = selected_wine_type

    # =====================================
    # ПОДКАТЕГОРИИ НА АЛКОХОЛА
    # =====================================

    elif selected_drink_group == "🥃 Алкохол":

        selected_alcohol_type = st.segmented_control(
            "",
            [
                "🥃 Уиски",
                "🍸 Водка",
                "🥃 Ракия",
                "🥃 Джин",
                "🌿 Анасонови",
                "🥃 Ром / Коняк",
                "🍷 Дижестив"
            ],
            default="🥃 Уиски",
            key="alcohol_type_selector"
        )

        items = [
            item
            for item in items
            if len(item) > 6
            and item[6] == selected_alcohol_type
        ]

        section_title = selected_alcohol_type

    st.markdown(
        f"""
        <div style="
            color:#FFD54F;
            font-size:22px;
            font-weight:700;
            margin-top:12px;
            margin-bottom:10px;
        ">
            {section_title}
        </div>
        """,
        unsafe_allow_html=True
    )

# =====================================
# СНИМКИ НА БУРГЕРИТЕ
# =====================================

burger_images = {
    "Американски хот-дог": "assets/shared image (15).jpeg",
    "Свински бургер": "assets/shared image (16).jpeg",
    "Телешки бургер": "assets/shared image (4).jpeg",
    "Пилешки бургер": "assets/shared image (6).jpeg",
    "Пържени картофи с пилешко": "assets/shared image (9).jpeg",
    "Пържени картофи със сьомга": "assets/shared image (12).jpeg",
    "Пържени картофи с бекон": "assets/shared image (13).jpeg",
    "Пържени картофи с телешко": "assets/01d65c96-56f8-4703-99ed-a1ac6d9b5065.jpg"
}

# =====================================
# ПОКАЗВАНЕ НА АРТИКУЛИТЕ
# =====================================

if not items:

    st.info(
        "В тази секция все още няма налични артикули."
    )

else:

    for item_index, item in enumerate(items):

        item_id = item[0]
        item_name = item[1]
        price = float(item[2])
        description = item[3] if len(item) > 3 else ""
        item_drink_group = item[4] if len(item) > 4 else ""
        item_wine_type = item[5] if len(item) > 5 else ""
        item_alcohol_type = item[6] if len(item) > 6 else ""

        col1, col2, col3, col4 = st.columns(
            [6, 0.7, 1.3, 1.7]
        )

        # =====================================
        # ИМЕ НА АРТИКУЛА
        # =====================================

        with col1:

            st.markdown(
                f"""
                <div style="
                    background-color:#0F172A;
                    border:1px solid #24324A;
                    border-radius:12px;
                    padding:12px 14px;
                    color:#F5E6C8;
                    font-weight:700;
                    font-size:18px;
                    min-height:52px;
                    display:flex;
                    align-items:center;
                ">
                    {item_name}
                </div>
                """,
                unsafe_allow_html=True
            )
            drink_variants = {

                "Кока-Кола 250ml": [
                    "Coca-Cola",
                    "Coca-Cola Zero"
                ],

                "Фанта 250ml": [
                    "Портокал",
                    "Лимон",
                    "Екзотик"
                ],

                "Натурален сок Cappy": [
                    "Праскова",
                    "Портокал",
                    "Ябълка",
                    "Мултивитамин"
                ],

                "Студен чай Fuzetea": [
                    "Праскова",
                    "Лимон",
                    "Зелен чай"
                ],

                "Schweppes Сода": [
                    "Сода",
                    "Тоник",
                    "Bitter Lemon"
                ]
            }

            selected_variant = ""

            if item_name in drink_variants:
                
                variant_col, _ = st.columns([2, 8])

                with variant_col:
                
                    selected_variant = st.selectbox(
                        "",
                        drink_variants[item_name],
                        key=f"variant_{item_id}_{item_index}"
                    )

        # =====================================
        # ИНФОРМАЦИЯ И КОМЕНТАР
        # =====================================

        with col2:

            with st.popover("ℹ️"):

                st.markdown(
                    f"""
                    <div style="
                        color:#F5E6C8;
                        font-size:28px;
                        font-weight:800;
                        text-align:center;
                        margin-bottom:10px;
                    ">
                        {item_name}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                image_path = burger_images.get(
                    item_name
                )

                if image_path:

                    try:

                        st.image(
                            image_path,
                            use_container_width=True
                        )

                    except Exception:

                        st.caption(
                            "Снимката временно не е налична."
                        )

                if item_drink_group == "🥃 Алкохол":

                    st.markdown(
                        """
                        <div style="
                            background:#1F2937;
                            color:#FFD54F;
                            border:1px solid #D4AF37;
                            border-radius:10px;
                            padding:10px;
                            text-align:center;
                            font-weight:700;
                            margin-bottom:10px;
                        ">
                            🥃 Посочената цена е за 50 мл.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                if description:

                    st.write(
                        description
                    )

                else:

                    st.info(
                        "Няма описание."
                    )

                comment_label = "Коментар"
                
                if selected_category not in (
                    "Напитки",
                ):
                    comment_label = "Коментар към кухнята"
                
                comment = st.text_area(
                    comment_label,
                    placeholder=" коментар",
                    key=f"comment_{item_id}_{item_index}",
                    height=80
                )

                if st.button(
                    "Запази коментар",
                    key=f"save_{item_id}_{item_index}"
                ):

                    st.session_state[
                        f"saved_note_{item_id}_{item_index}"
                    ] = comment

                    st.success(
                        "Коментарът е запазен."
                    )

        # =====================================
        # ЦЕНА
        # =====================================

        with col3:

            st.markdown(
                f"""
                <div style="
                    color:#FFD54F;
                    font-weight:700;
                    font-size:18px;
                    padding-left:15px;
                ">
                    € {price:.2f}
                </div>
                """,
                unsafe_allow_html=True
            )

        # =====================================
        # ДОБАВЯНЕ В КОЛИЧКАТА
        # =====================================
        

        with col4:

            item_is_in_cart = any(
                cart_item["id"] == item_id
                for cart_item in st.session_state.cart
            )

            if item_is_in_cart:

                st.markdown(
                    """
                    <div style="
                        background:#198754;
                        color:white;
                        border-radius:8px;
                        padding:4px 8px;
                        text-align:center;
                        font-size:12px;
                        font-weight:700;
                        margin-bottom:4px;
                    ">
                        ✅ Добавено
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            if st.button(
                "🛒 Добави",
                key=f"add_{item_id}_{item_index}"
            ):

                saved_comment = st.session_state.get(
                    f"saved_note_{item_id}_{item_index}",
                    ""
                )

                final_name = item_name

                if item_name in drink_variants and selected_variant:
                    final_name = (
                        f"{item_name} - {selected_variant}"
                    )

                add_to_cart(
                    item_id=item_id,
                    item_name=final_name,
                    price=price,
                    note=saved_comment
                )

                st.rerun()
# =====================================
# КОЛИЧКА
# =====================================

st.divider()

st.subheader("🛒 Вашата поръчка")

if st.session_state.last_order_id is not None:

    st.success(
        f"✅ Поръчката е изпратена успешно!\n\n"
        f"🧾 Номер на поръчката: {st.session_state.last_order_id}\n\n"
        "👨‍🍳 Кухнята и сервитьорът вече виждат вашата поръчка.\n\n"
        "🔔 Ако имате нужда от нещо допълнително, "
        "използвайте бутона „Извикай сервитьор“ "
        "или просто махнете с 👋."
    )

    st.session_state.last_order_id = None

elif not st.session_state.cart:

    st.info("Няма избрани артикули.")

else:

    grouped = {}

    for item in st.session_state.cart:

        key = (
            item["id"],
            item.get("note", "")
        )

        if key not in grouped:

            grouped[key] = {
                "id": item["id"],
                "name": item["name"],
                "price": item["price"],
                "note": item.get("note", ""),
                "qty": 0
            }

        grouped[key]["qty"] += 1

    total = 0

    for data in grouped.values():

        qty = data["qty"]

        row_total = qty * data["price"]

        c1, c2, c3, c4, c5 = st.columns(
            [5, 1, 1, 1, 1]
        )

        with c1:

            st.write(data["name"])

            if data["note"]:

                st.caption(
                    f"📝 {data['note']}"
                )

        with c2:

            if st.button(
                "➖",
                key=f"minus_{data['id']}_{data['note']}"
            ):

                remove_one_from_cart(
                    data["id"],
                    data["note"]
                )

                st.rerun()

        with c3:

            st.write(
                f"x{qty}"
            )

        with c4:

            if st.button(
                "➕",
                key=f"plus_{data['id']}_{data['note']}"
            ):

                add_to_cart(
                    item_id=data["id"],
                    item_name=data["name"],
                    price=data["price"],
                    note=data["note"]
                )

                st.rerun()

        with c5:

            st.write(
                f"€ {row_total:.2f}"
            )

        total += row_total

    st.success(
        f"Общо: € {total:.2f}"
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "🗑️ Изчисти количката"
        ):

            st.session_state.cart = []

            st.rerun()

    with col2:

        if st.button(
            "✅ Изпрати поръчка"
        ):

            order_id = create_order(
                table_number,
                st.session_state.cart
            )

            st.session_state.cart = []
            st.session_state.last_order_id = order_id

            st.rerun()
            st.markdown("""
<div style="
    position: fixed;
    bottom: 12px;
    right: 18px;
    color: #D4AF37;
    font-family: Arial, sans-serif;
    text-align: right;
    opacity: 0.75;
    z-index: 999;
">
    <div style="
        font-size: 18px;
        font-weight: 800;
        line-height: 1;
    ">HA</div>

    <div style="
        font-size: 11px;
        letter-spacing: 2px;
        font-weight: 600;
    ">HMITSEV</div>
</div>
""", unsafe_allow_html=True)
