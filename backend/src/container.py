from typing import TYPE_CHECKING

from dependency_injector import containers
from dependency_injector.providers import Factory, Resource, Singleton

from src.clients.database.engine import Database, async_engine
from src.services.basket.service import BasketService
from src.services.category.service import CategoryService
from src.services.order.service import OrderService
from src.services.product.service import ProductService
from src.services.rental.service import RentalService
from src.services.user.service import UserService
from src.settings.database import DatabaseSettings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

    from src.services.basket.interface import BasketServiceI
    from src.services.category.interface import CategoryServiceI
    from src.services.order.interface import OrderServiceI
    from src.services.product.interface import ProductServiceI
    from src.services.rental.interface import RentalServiceI
    from src.services.user.interface import UserServiceI


class DependencyContainer(containers.DeclarativeContainer):
    database_settings: Singleton["DatabaseSettings"] = Singleton(DatabaseSettings)
    async_engine: Singleton["AsyncEngine"] = Singleton(
        async_engine,
        database_settings=database_settings.provided,
    )
    database: Factory["Database"] = Factory(Database, engine=async_engine.provided)
    database_session: Resource["AsyncGenerator[AsyncSession, None]"] = Resource(database.provided.get_session)

    user_service: Factory["UserServiceI"] = Factory(UserService, session=database_session)
    category_service: Factory["CategoryServiceI"] = Factory(CategoryService, session=database_session)
    product_service: Factory["ProductServiceI"] = Factory(ProductService, session=database_session)
    rental_service: Factory["RentalServiceI"] = Factory(RentalService, session=database_session)
    basket_service: Factory["BasketServiceI"] = Factory(BasketService, session=database_session)
    order_service: Factory["OrderServiceI"] = Factory(
        OrderService, session=database_session, basket_service=basket_service, rental_service=rental_service
    )


container = DependencyContainer()
