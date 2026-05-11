"""seed initial products and categories

Revision ID: a1b2c3d4e5f6
Revises: 3d1b7f4c2a11
Create Date: 2026-04-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '8f6c2b1d4a9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOW = "NOW()"


def upgrade() -> None:
    bind = op.get_bind()

    # Не вставляем, если категории уже есть
    result = bind.execute(sa.text("SELECT COUNT(*) FROM categories")).scalar()
    if result and result > 0:
        return

    # --- Категории ---
    bind.execute(sa.text("""
        INSERT INTO categories (name) VALUES
        ('Велосипеды'),
        ('Самокаты'),
        ('Лыжи и сноуборды')
    """))

    # --- Продукты ---
    # Велосипеды
    bind.execute(sa.text("""
        INSERT INTO products (category_id, name, description, price, image_url)
        SELECT c.category_id, p.name, p.description, p.price, NULL
        FROM (VALUES
            ('Велосипед городской', 'Удобный городской велосипед для прогулок и поездок по городу', 500),
            ('Велосипед горный', 'Горный велосипед с амортизацией для бездорожья', 700),
            ('Велосипед детский', 'Велосипед для детей 5-10 лет', 300)
        ) AS p(name, description, price)
        CROSS JOIN categories c
        WHERE c.name = 'Велосипеды'
    """))

    # Самокаты
    bind.execute(sa.text("""
        INSERT INTO products (category_id, name, description, price, image_url)
        SELECT c.category_id, p.name, p.description, p.price, NULL
        FROM (VALUES
            ('Самокат электрический', 'Электрический самокат, дальность до 30 км', 600),
            ('Самокат классический', 'Лёгкий самокат для прогулок', 250)
        ) AS p(name, description, price)
        CROSS JOIN categories c
        WHERE c.name = 'Самокаты'
    """))

    # Лыжи и сноуборды
    bind.execute(sa.text("""
        INSERT INTO products (category_id, name, description, price, image_url)
        SELECT c.category_id, p.name, p.description, p.price, NULL
        FROM (VALUES
            ('Лыжи взрослые', 'Горные лыжи для взрослых, включая ботинки и палки', 1000),
            ('Сноуборд', 'Сноуборд с ботинками и крепениями', 1200),
            ('Лыжи детские', 'Лыжный комплект для детей', 600)
        ) AS p(name, description, price)
        CROSS JOIN categories c
        WHERE c.name = 'Лыжи и сноуборды'
    """))

    # --- Конфиги аренды для каждого продукта ---
    # slot_duration_minutes=60 (1 час), min_rental_slots=1, total_quantity=3
    bind.execute(sa.text(f"""
        INSERT INTO product_rentals (
            product_id, total_quantity, slot_duration_minutes,
            min_rental_slots, max_rental_slots,
            buffer_before_minutes, buffer_after_minutes,
            is_enabled, created_at, updated_at
        )
        SELECT
            p.product_id,
            3,    -- total_quantity
            60,   -- slot_duration_minutes (1 час)
            1,    -- min_rental_slots
            NULL, -- max_rental_slots (без ограничения)
            0,    -- buffer_before_minutes
            15,   -- buffer_after_minutes (15 мин на подготовку)
            true,
            {NOW}, {NOW}
        FROM products p
    """))


def downgrade() -> None:
    # Удаляем только seed-данные (если продуктов больше нет, удаляем категории)
    op.execute(sa.text("""
        DELETE FROM categories
        WHERE name IN ('Велосипеды', 'Самокаты', 'Лыжи и сноуборды')
    """))
