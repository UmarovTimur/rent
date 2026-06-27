from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from src.settings.auth import AuthSettings

_settings = AuthSettings()


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=_settings.expire_days)
    return jwt.encode({"sub": str(user_id), "exp": expire}, _settings.secret, algorithm=_settings.algorithm)


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, _settings.secret, algorithms=[_settings.algorithm])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError) as e:
        raise ValueError("Invalid token") from e
