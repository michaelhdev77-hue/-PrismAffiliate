from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "prism_affiliate_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.feed_ingestion",
        "app.tasks.stats_aggregation",
        "app.tasks.link_refresh",
        "app.tasks.healthcheck",
        "app.tasks.prism_bridge",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

celery_app.conf.beat_schedule = {
    # Dispatch feed syncs every 15 minutes (checks cron per feed)
    "dispatch-feed-syncs": {
        "task": "affiliate.dispatch_feed_syncs",
        "schedule": crontab(minute="*/15"),
    },
    # Aggregate daily stats at 02:00 MSK
    "aggregate-daily-stats": {
        "task": "affiliate.aggregate_daily_stats",
        "schedule": crontab(hour=2, minute=0),
    },
    # Refresh expiring affiliate links every 30 min
    "refresh-expiring-links": {
        "task": "affiliate.refresh_expiring_links",
        "schedule": crontab(minute="*/30"),
    },
    # Healthcheck marketplace accounts every 6 hours
    "healthcheck-accounts": {
        "task": "affiliate.healthcheck_accounts",
        "schedule": crontab(hour="*/6", minute=5),
    },
    # Push top affiliate products to PRISM as Pinterest pin drafts daily at 08:00 MSK
    "push-products-to-prism": {
        "task": "affiliate.push_products_to_prism",
        "schedule": crontab(hour=8, minute=0),
    },
}
