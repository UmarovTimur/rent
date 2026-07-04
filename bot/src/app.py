# src/app.py
import logging
import sys

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import bot
from src.handlers.admin_callbacks import router as admin_router
from src.handlers.message_handlers import router as message_router
from src.handlers.registration import router as registration_router


async def start_polling() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    # Registration first: its state-filtered handlers must win over the
    # generic F.photo / text handlers while a user is mid-registration.
    dp.include_router(registration_router)
    dp.include_router(message_router)
    dp.include_router(admin_router)
    await dp.start_polling(bot)