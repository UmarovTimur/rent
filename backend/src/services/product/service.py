from collections.abc import Callable

from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.clients.database.models.category import Category
from src.clients.database.models.product import Product, ProductAddonLink
from src.services.base import BaseService
from src.services.errors import CategoryNotFoundError, ProductNotFoundError
from src.services.product.interface import ProductServiceI
from src.services.product.schemas import (
    AddonResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from src.services.schemas import Image
from src.services.static import products_path
from src.services.utils import delete_image, save_image, try_commit


class ProductService(BaseService, ProductServiceI):
    async def create(self, product_data: ProductCreate, image: Image) -> ProductResponse:
        async with self.session() as session:
            category = await session.get(Category, product_data.category_id)
            if not category:
                raise CategoryNotFoundError
            image_url = await save_image(image, products_path) if image.filename else None

            new_product = Product(
                name=product_data.name,
                description=product_data.description,
                category_id=product_data.category_id,
                price=product_data.price,
                image_url=image_url,
                is_addon=product_data.is_addon,
                price_mode=product_data.price_mode,
            )
            session.add(new_product)
            await try_commit(session, new_product.name, delete_image, products_path)
            query = (
                select(Product)
                .where(Product.product_id == new_product.product_id)
                .options(selectinload(Product.category))
            )
            result = await session.execute(query)
            product_response = result.scalars().first()
            type_adapter = TypeAdapter(ProductResponse)
            return type_adapter.validate_python(product_response)

    async def get_all(self) -> list[ProductResponse]:
        async with self.session() as session:
            # Add-ons are hidden from the main catalog — offered only as options.
            query = (
                select(Product)
                .where(Product.is_addon.is_(False))
                .options(selectinload(Product.category))
            )
            result = await session.execute(query)
            products = result.scalars().all()

            kit_sums = await self._kit_price_sums(session, [p.product_id for p in products])

            responses = []
            for p in products:
                response = ProductResponse.model_validate(p)
                response.display_price = p.price + kit_sums.get(p.product_id, 0)
                responses.append(response)
            return responses

    @staticmethod
    async def _kit_price_sums(session, product_ids: list[int]) -> dict[int, int]:
        """Sum of (child price × default_quantity) per parent, for pre-included
        kit components only (default_quantity > 0). Optional add-ons don't count."""
        if not product_ids:
            return {}
        result = await session.execute(
            select(
                ProductAddonLink.parent_product_id,
                func.sum(ProductAddonLink.default_quantity * Product.price),
            )
            .join(Product, Product.product_id == ProductAddonLink.addon_product_id)
            .where(
                ProductAddonLink.parent_product_id.in_(product_ids),
                ProductAddonLink.default_quantity > 0,
            )
            .group_by(ProductAddonLink.parent_product_id)
        )
        return {parent_id: int(total) for parent_id, total in result.all()}

    async def get_addons_for(self, product_id: int) -> list[AddonResponse]:
        async with self.session() as session:
            if not await session.get(Product, product_id):
                raise ProductNotFoundError
            result = await session.execute(
                select(ProductAddonLink)
                .where(ProductAddonLink.parent_product_id == product_id)
                .order_by(ProductAddonLink.sort_order)
                .options(selectinload(ProductAddonLink.addon))
            )
            links = result.scalars().all()
            return [
                AddonResponse(
                    product_id=link.addon.product_id,
                    name=link.addon.name,
                    price=link.addon.price,
                    price_mode=link.addon.price_mode,
                    image_url=link.addon.image_url,
                    default_quantity=link.default_quantity,
                )
                for link in links
            ]

    async def get_by_name(self, product_name: str) -> ProductResponse:
        async with self.session() as session:
            query = (
                select(Product)
                .options(selectinload(Product.category))
                .where(Product.name == product_name)
            )
            result = await session.execute(query)
            product = result.scalar()
            if not product:
                raise ProductNotFoundError
            type_adapter = TypeAdapter(ProductResponse)
            return type_adapter.validate_python(product)

    async def update(self, product_id: int, product_data: ProductUpdate, image: Image) -> None:
        image_url = await save_image(image, products_path) if image.filename else None
        async with self.session() as session:
            product = await session.get(Product, product_id)
            if product:
                if product_data.name:
                    product.name = product_data.name
                if product_data.description:
                    product.description = product_data.description
                if product_data.category_id:
                    product.category_id = product_data.category_id
                if product_data.price is not None:
                    product.price = product_data.price
                if product_data.is_addon is not None:
                    product.is_addon = product_data.is_addon
                if product_data.price_mode is not None:
                    product.price_mode = product_data.price_mode
                if image_url:
                    if filename := product.image_url:
                        await delete_image(str(filename), products_path)
                    product.image_url = image_url
                await try_commit(session, product_data.name, delete_image, products_path)
            else:
                raise ProductNotFoundError

    async def delete(self, product_id: int) -> None:
        async with self.session() as session:
            product = await session.get(Product, product_id)
            if not product:
                raise ProductNotFoundError
            if filename := product.image_url:
                await delete_image(str(filename), products_path)
            await session.delete(product)
            await session.commit()
