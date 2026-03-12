from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from celery import Celery
from app.config import settings
from app.deps import require_auth

router = APIRouter()

_celery = Celery(broker=settings.redis_url)


class PushRequest(BaseModel):
    prism_project_id: Optional[str] = None
    max_products: int = 10


@router.post("/push-to-prism")
async def push_to_prism(body: PushRequest, _: dict = Depends(require_auth)):
    """Trigger bridge task to push top products to PRISM."""
    result = _celery.send_task(
        "affiliate.push_products_to_prism",
        kwargs={
            "prism_project_id": body.prism_project_id,
            "max_products": body.max_products,
        },
    )
    return {"status": "queued", "task_id": result.id}
