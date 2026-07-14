from celery import Celery
from app.core.config import settings

# Instantiating the distributed task orchestration node
celery_app = Celery(
    "enterprise_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Explicit configurations for package modular mapping
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Forces Celery to look for background functions inside app.tasks
    imports=["app.tasks.document_tasks"]
)