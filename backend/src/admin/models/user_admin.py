from sqladmin import ModelView
from src.clients.database.models.user import User


class UserAdmin(ModelView, model=User):
    column_list = [
        User.user_id,
        User.first_name,
        User.last_name,
        User.username,
        User.language_code,
        User.coins,
        User.is_banned,
    ]
    column_searchable_list = [User.user_id, User.username, User.first_name, User.phone_number]
    name_plural = "Users"