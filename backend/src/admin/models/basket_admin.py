from sqladmin import ModelView

from src.clients.database.models.basket import Basket, BasketItem


class BasketAdmin(ModelView, model=Basket):
    column_list = [
        Basket.basket_id,
        Basket.user_id,
    ]
    name_plural = "Baskets"

class BasketItemAdmin(ModelView, model=BasketItem):
    column_list = [
        BasketItem.basket_item_id,
        BasketItem.basket_id,
        BasketItem.product_id,
        BasketItem.quantity,
        BasketItem.rental_start,
        BasketItem.rental_end,
    ]
    name_plural = "Basket Items"
