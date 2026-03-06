from sqladmin import ModelView

from src.clients.database.models.product import Product


class ProductAdmin(ModelView, model=Product):
    column_list = [
        Product.product_id,
        Product.category_id,
        Product.name,
        Product.description,
        Product.price,
        Product.image_url,
    ]
    form_widget_args = {
        "price": {"step": 1, "min": 0},
    }
    name_plural = "Products"
