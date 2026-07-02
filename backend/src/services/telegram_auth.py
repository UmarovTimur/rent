import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> dict:
    """Validate Telegram WebApp initData per Telegram's documented algorithm.

    Returns the parsed initData fields (with "user" decoded from JSON) on success.
    Raises ValueError on any validation failure.
    """
    if not init_data or not bot_token:
        raise ValueError("Missing initData or bot token")

    pairs = parse_qsl(init_data, strict_parsing=True)
    data = dict(pairs)

    received_hash = data.pop("hash", None)
    if not received_hash:
        raise ValueError("initData is missing 'hash'")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("initData signature is invalid")

    auth_date = data.get("auth_date")
    if not auth_date or not auth_date.isdigit():
        raise ValueError("initData is missing a valid 'auth_date'")

    age = time.time() - int(auth_date)
    if age > max_age_seconds:
        raise ValueError("initData has expired")

    if "user" in data:
        try:
            data["user"] = json.loads(data["user"])
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("initData 'user' field is not valid JSON") from exc

    return data
