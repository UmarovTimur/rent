from typing import Any

from sqladmin import ModelView
from starlette.requests import Request

from src.clients.database.models.admin_user import AdminUser
from src.services.admin_auth import hash_password, is_hashed


class AdminUserAdmin(ModelView, model=AdminUser):
    name = "Admin"
    name_plural = "Admins"
    icon = "fa-solid fa-user-shield"

    column_list = [AdminUser.id, AdminUser.username, AdminUser.is_active, AdminUser.created_at]
    column_details_exclude_list = [AdminUser.password_hash]
    form_columns = [AdminUser.username, AdminUser.password_hash, AdminUser.is_active]
    # The password field carries a plaintext password on submit; it is hashed in
    # on_model_change. On edit the field is prefilled with the existing hash, so an
    # unchanged value stays a hash and is left as-is.
    column_labels = {AdminUser.password_hash: "Password"}

    async def on_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Request) -> None:
        password = data.get("password_hash")
        if password and not is_hashed(password):
            data["password_hash"] = hash_password(password)
