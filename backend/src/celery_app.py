import os

from celery import Celery

_redis = f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', 6379)}/0"

celery_app = Celery(
    "rent",
    broker=_redis,
    backend=_redis,
    include=["src.tasks.reminders", "src.tasks.payment_holds"],
)

celery_app.conf.beat_schedule = {
    "pickup-reminders": {
        "task": "src.tasks.reminders.send_pickup_reminders",
        "schedule": 300.0,
    },
    "return-reminders": {
        "task": "src.tasks.reminders.send_return_reminders",
        "schedule": 300.0,
    },
    "payment-hold-reconciliation": {
        "task": "src.tasks.payment_holds.reconcile_expired_holds",
        "schedule": 60.0,
    },
}
celery_app.conf.timezone = "UTC"
