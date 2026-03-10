from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_auth
from app.models import MarketplaceAccount, MarketplaceType
from app.config import settings
from shared.encryption import encrypt_json, decrypt_json
from shared.adapters import get_adapter

router = APIRouter()


class AccountCreate(BaseModel):
    marketplace: MarketplaceType
    display_name: str
    credentials: dict
    config: dict = {}


class AccountUpdate(BaseModel):
    display_name: Optional[str] = None
    credentials: Optional[dict] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class AccountOut(BaseModel):
    id: str
    marketplace: MarketplaceType
    display_name: str
    config: dict
    is_active: bool
    health_status: str
    last_health_check: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[AccountOut])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    result = await db.execute(select(MarketplaceAccount).order_by(MarketplaceAccount.created_at))
    return result.scalars().all()


@router.post("/", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AccountCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    account = MarketplaceAccount(
        marketplace=body.marketplace,
        display_name=body.display_name,
        credentials_encrypted=encrypt_json(body.credentials, settings.encryption_key),
        config=body.config,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountOut)
async def get_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    account = await db.get(MarketplaceAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.patch("/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: str,
    body: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    account = await db.get(MarketplaceAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if body.display_name is not None:
        account.display_name = body.display_name
    if body.credentials is not None:
        account.credentials_encrypted = encrypt_json(body.credentials, settings.encryption_key)
    if body.config is not None:
        account.config = body.config
    if body.is_active is not None:
        account.is_active = body.is_active
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    account = await db.get(MarketplaceAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()


@router.post("/{account_id}/discover-programs")
async def discover_programs(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    """Fetch connected programs from the affiliate network API."""
    account = await db.get(MarketplaceAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    credentials = decrypt_json(account.credentials_encrypted, settings.encryption_key)
    try:
        adapter = get_adapter(account.marketplace.value)
    except ValueError:
        raise HTTPException(status_code=400, detail="No adapter for this marketplace")

    if not hasattr(adapter, "list_programs"):
        raise HTTPException(status_code=400, detail="This marketplace does not support program discovery")

    website_id = credentials.get("website_id", "")
    if not website_id:
        raise HTTPException(status_code=400, detail="No website_id in credentials")

    try:
        programs = adapter.list_programs(credentials, str(website_id))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch programs: {exc}")

    # Re-encrypt credentials (token may have been refreshed)
    account.credentials_encrypted = encrypt_json(credentials, settings.encryption_key)
    await db.commit()

    return programs


@router.post("/{account_id}/healthcheck")
async def healthcheck_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    account = await db.get(MarketplaceAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    credentials = decrypt_json(account.credentials_encrypted, settings.encryption_key)
    try:
        adapter = get_adapter(account.marketplace.value)
        result = adapter.healthcheck(credentials)
    except ValueError:
        result = {"status": "error", "detail": "No adapter for this marketplace"}

    account.health_status = result.get("status", "error")
    account.last_health_check = datetime.utcnow()
    if result.get("status") == "ok":
        account.credentials_encrypted = encrypt_json(credentials, settings.encryption_key)
    await db.commit()
    return result
