from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class BillingSettings(BaseSettings):
    """Rental billing rules (half-day-step hybrid).

    MUST stay in sync with the frontend mirror: frontend/src/utils/rental.ts (BILLING const).
    The owner's reference table lives in backend/tests/test_rental_pricing.py and
    frontend/src/utils/rental.test.ts — any drift fails a test on the diverged side.
    """

    timezone: str = "Asia/Tashkent"
    evening_pickup_hour: int = 17  # pickup at/after this local hour → grace
    day_start_hour: int = 9  # billing starts here the next day after grace
    return_leniency_minutes: int = 120  # subtracted from duration before rounding
    rounding_step_minutes: int = 720  # 12h = 0.5-day step, rounded UP
    min_half_days: int = 2  # minimum charge = 1 day
    total_floor_step: int = 100  # floor final order/basket total to nearest 100 sum

    model_config = SettingsConfigDict(env_prefix="billing_")
