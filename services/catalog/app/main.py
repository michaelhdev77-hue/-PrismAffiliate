from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import engine, Base
from app.routes import marketplace_accounts, campaigns, feeds, products, internal
from app.routes.bridge import router as bridge_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Prism Affiliate — Catalog",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(marketplace_accounts.router, prefix="/api/v1/marketplace-accounts", tags=["marketplace-accounts"])
app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(feeds.router, prefix="/api/v1/feeds", tags=["feeds"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(internal.router, prefix="/internal", tags=["internal"])
app.include_router(bridge_router, prefix="/api/v1/bridge", tags=["bridge"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "catalog"}
