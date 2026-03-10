from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import json
import redis
from app.config import settings
from app.deps import require_auth

router = APIRouter()


class PushRequest(BaseModel):
    prism_project_id: Optional[str] = None
    max_products: int = 10


@router.post("/push-to-prism")
async def push_to_prism(body: PushRequest, _: dict = Depends(require_auth)):
    """Trigger bridge task to push top products to PRISM."""
    r = redis.Redis.from_url(settings.redis_url)
    task_body = json.dumps({
        "id": f"bridge-{body.prism_project_id or 'all'}",
        "task": "affiliate.push_products_to_prism",
        "kwargs": {
            "prism_project_id": body.prism_project_id,
            "max_products": body.max_products,
        },
    })
    r.lpush("celery", task_body)
    r.close()
    return {"status": "queued"}
