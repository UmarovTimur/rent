from os import getenv
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.admin.models.basket_admin import BasketAdmin, BasketItemAdmin
from src.admin.models.category_admin import CategoryAdmin
from src.admin.models.order_admin import OrderAdmin, OrderItemAdmin
from src.admin.models.product_admin import ProductAdmin
from src.admin.models.rental_admin import ProductRentalAdmin, ProductRentalSlotAdmin
from src.admin.models.user_admin import UserAdmin
from starlette.middleware.cors import CORSMiddleware
from sqladmin import Admin

from src.container import DependencyContainer, container
from src.server.handle_erros import patch_exception_handlers
from src.server.routers.v1.routers import api_v1_router

LOCAL_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

LOCAL_DEV_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


class CustomFastAPI(FastAPI):
    container: DependencyContainer


def is_local_cors_enabled() -> bool:
    return getenv("SERVER_CORS_INCLUDE_LOCAL_DEV", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_cors_origins() -> list[str]:
    raw_origins = getenv("SERVER_CORS_ORIGINS")
    configured = []
    if raw_origins:
        configured = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    if is_local_cors_enabled():
        # Keep local development working even when explicit SERVER_CORS_ORIGINS is set.
        configured.extend(LOCAL_DEV_ORIGINS)

    if configured:
        # Preserve order while removing duplicates.
        return list(dict.fromkeys(configured))

    return LOCAL_DEV_ORIGINS


def get_cors_origin_regex() -> Optional[str]:
    raw_regex = getenv("SERVER_CORS_ORIGIN_REGEX")
    if raw_regex:
        return raw_regex

    # In local development frontend port can vary (Vite may switch 5173 -> 5174+).
    if is_local_cors_enabled():
        return LOCAL_DEV_ORIGIN_REGEX
    return None


def create_application() -> CustomFastAPI:
    server = CustomFastAPI(title="tg-mini-app")
    server.container = DependencyContainer()
    server.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_origin_regex=get_cors_origin_regex(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    admin = Admin(server, engine=container.database().engine)
    admin.add_view(UserAdmin)
    admin.add_view(OrderAdmin)
    admin.add_view(OrderItemAdmin)
    admin.add_view(ProductAdmin)
    admin.add_view(ProductRentalAdmin)
    admin.add_view(ProductRentalSlotAdmin)
    admin.add_view(CategoryAdmin)
    admin.add_view(BasketAdmin)
    admin.add_view(BasketItemAdmin)

    patch_exception_handlers(app=server)
    server.mount("/media", StaticFiles(directory="/media"), name="media")
    server.include_router(api_v1_router)
    return server
