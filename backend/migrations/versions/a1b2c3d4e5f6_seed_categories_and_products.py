"""seed categories and products

Revision ID: a1b2c3d4e5f6
Revises: 8f6c2b1d4a9e
Create Date: 2026-06-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column, String, Integer, Boolean, text


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '8f6c2b1d4a9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIES = [
    "Палатки",
    "Мебель",
    "Сон и комфорт",
    "Треккинг",
    "Кухня и готовка",
    "Свет и энергия",
    "Посуда",
]

# (name, price, category_name, description)
PRODUCTS = [
    ("Палатка 8-мест",           250, "Палатки",         "Вместительная палатка на 8 человек"),
    ("Палатка 5-мест",           150, "Палатки",         "Палатка на 5 человек"),
    ("Палатка 4-места",          120, "Палатки",         "Палатка на 4 человека"),
    ("Комплект: 4 стула + 1 стол", 140, "Мебель",        "Набор кемпинговой мебели"),
    ("Стол JEEP 1.20 м",          40, "Мебель",          "Складной стол JEEP 1.20 м"),
    ("Стул Camel",                25, "Мебель",          "Складной стул Camel"),
    ("Спальный мешок",            40, "Сон и комфорт",   "Спальный мешок"),
    ("Каремат",                   30, "Сон и комфорт",   "Туристический каремат"),
    ("Рюкзак 60 L",               50, "Треккинг",        "Рюкзак объёмом 60 литров"),
    ("Трекинговые палки",         30, "Треккинг",        "Палки для треккинга"),
    ("Газовая горелка 1L",        40, "Кухня и готовка", "Газовая горелка 1L (без баллона)"),
    ("Комфорка (мини-плита)",     40, "Кухня и готовка", "Мини-плита для кемпинга"),
    ("Баллон",                    40, "Кухня и готовка", "Газовый баллон"),
    ("Power Bank 20 000 mAh",     40, "Свет и энергия",  "Портативный аккумулятор 20 000 mAh"),
    ("Фонарь налобный",           20, "Свет и энергия",  "Налобный фонарь"),
    ("Фонарь ручной",             30, "Свет и энергия",  "Ручной фонарь"),
    ("Ночник",                    15, "Свет и энергия",  "Кемпинговый ночник"),
    ("Сковорода",                 15, "Посуда",          "Туристическая сковорода"),
    ("Чайник 1.6 L",              15, "Посуда",          "Чайник объёмом 1.6 литра"),
    ("Кастрюля 3.6 L",            15, "Посуда",          "Кастрюля объёмом 3.6 литра"),
    ("Стенки от ветра",           20, "Посуда",          "Ветрозащитные стенки"),
]

IMAGE_URL = "1.jpg"


def upgrade() -> None:
    conn = op.get_bind()

    # Insert categories
    for cat_name in CATEGORIES:
        conn.execute(
            text("INSERT INTO categories (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"),
            {"name": cat_name},
        )

    # Build category name -> id map
    result = conn.execute(text("SELECT category_id, name FROM categories"))
    cat_map = {row[1]: row[0] for row in result}

    # Insert products + rental config
    for name, price, cat_name, description in PRODUCTS:
        existing = conn.execute(
            text("SELECT product_id FROM products WHERE name = :name"),
            {"name": name},
        ).fetchone()

        if existing:
            continue

        row = conn.execute(
            text("""
                INSERT INTO products (category_id, name, description, price, image_url)
                VALUES (:cat_id, :name, :desc, :price, :img)
                RETURNING product_id
            """),
            {
                "cat_id": cat_map[cat_name],
                "name": name,
                "desc": description,
                "price": price,
                "img": IMAGE_URL,
            },
        ).fetchone()

        product_id = row[0]

        conn.execute(
            text("""
                INSERT INTO product_rentals
                    (product_id, total_quantity, slot_duration_minutes,
                     min_rental_slots, max_rental_slots,
                     buffer_before_minutes, buffer_after_minutes,
                     is_enabled, created_at, updated_at)
                VALUES
                    (:pid, 1, 1440, 1, NULL, 0, 0, TRUE, now(), now())
            """),
            {"pid": product_id},
        )


def downgrade() -> None:
    conn = op.get_bind()

    names = [p[0] for p in PRODUCTS]
    for name in names:
        conn.execute(text("DELETE FROM products WHERE name = :name"), {"name": name})

    for cat_name in CATEGORIES:
        conn.execute(
            text("DELETE FROM categories WHERE name = :name AND NOT EXISTS (SELECT 1 FROM products WHERE category_id = (SELECT category_id FROM categories WHERE name = :name2))"),
            {"name": cat_name, "name2": cat_name},
        )
