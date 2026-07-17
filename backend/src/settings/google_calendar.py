from pydantic_settings import BaseSettings, SettingsConfigDict


class GoogleCalendarSettings(BaseSettings):
    """Service-account sync of confirmed orders into a shared Google Calendar.

    Empty by default — calendar_sync.py treats that as "feature off" and no-ops
    silently, so an unconfigured deploy is unaffected.
    """

    id: str = ""                     # the shared calendar's id (…@group.calendar.google.com)
    service_account_json: str = ""   # full service-account JSON key, as one string

    model_config = SettingsConfigDict(env_prefix="google_calendar_")
