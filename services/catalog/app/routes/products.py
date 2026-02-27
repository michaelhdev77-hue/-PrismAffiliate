from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_auth
from app.models import Product

router = APIRouter()


class ProductOut(BaseModel):
    id: str
    marketplace: str
    external_id: str
    title: str
    description: Optional[str]
    category: str
    brand: Optional[str]
    price: float
    currency: str
    original_price: Optional[float]
    discount_pct: Optional[float]
    image_url: str
    product_url: str
    rating: Optional[float]
    review_count: Optional[int]
    in_stock: bool
    commission_rate: float
    commission_type: str
    tags: list
    niche: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[ProductOut])
async def search_products(
    q: Optional[str] = Query(None, description="Full-text search in title"),
    category: Optional[str] = Query(None),
    marketplace: Optional[str] = Query(None, description="Comma-separated list"),
    niche: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_commission: Optional[float] = Query(None),
    min_rating: Optional[float] = Query(None),
    in_stock_only: bool = Query(True),
    sort: str = Query("commission", enum=["commission", "price", "rating", "newest"]),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    filters = [Product.is_active == True]

    if q:
        filters.append(Product.title.ilike(f"%{q}%"))
    if category:
        filters.append(Product.category.ilike(f"%{category}%"))
    if marketplace:
        mkts = [m.strip() for m in marketplace.split(",")]
        filters.append(Product.marketplace.in_(mkts))
    if niche:
        filters.append(Product.niche == niche)
    if min_price is not None:
        filters.append(Product.price >= min_price)
    if max_price is not None:
        filters.append(Product.price <= max_price)
    if min_commission is not None:
        filters.append(Product.commission_rate >= min_commission)
    if min_rating is not None:
        filters.append(Product.rating >= min_rating)
    if in_stock_only:
        filters.append(Product.in_stock == True)

    order_col = {
        "commission": Product.commission_rate.desc(),
        "price": Product.price.asc(),
        "rating": Product.rating.desc(),
        "newest": Product.created_at.desc(),
    }[sort]

    stmt = (
        select(Product)
        .where(and_(*filters))
        .order_by(order_col)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    from sqlalchemy import distinct
    result = await db.execute(
        select(distinct(Product.category)).where(Product.category != "").limit(200)
    )
    return sorted(result.scalars().all())


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    from fastapi import HTTPException
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
