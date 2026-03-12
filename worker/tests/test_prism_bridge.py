"""Tests for prism_bridge task — _push_products() async function."""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.tasks.prism_bridge import _push_products, CATALOG_URL, LINKS_URL, PRISM_CONTENT_URL


def _make_response(status_code: int = 200, json_data=None):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or []
    resp.text = ""
    return resp


PROFILES = [
    {
        "id": "profile-1",
        "prism_project_id": "proj-aaa",
        "is_active": True,
        "max_products": 5,
        "categories": ["Electronics"],
        "marketplaces": ["gdeslon"],
        "min_commission_rate": 2.0,
    }
]

PRODUCTS = [
    {
        "id": "prod-1",
        "title": "Test Product 1",
        "marketplace": "gdeslon",
        "image_url": "https://img.example.com/1.jpg",
        "product_url": "https://example.com/1",
    },
    {
        "id": "prod-2",
        "title": "Test Product 2",
        "marketplace": "gdeslon",
        "image_url": "https://img.example.com/2.jpg",
        "product_url": "https://example.com/2",
    },
]

EXISTING_POSTS = [
    {
        "id": "post-existing",
        "product_image_url": "https://img.example.com/1.jpg",  # Duplicate of prod-1
    }
]

GENERATED_LINKS = [
    {"product_id": "prod-2", "affiliate_url": "https://aff.example.com/link-2"},
]

CREATED_POST = {"id": "post-new-1"}


@pytest.mark.asyncio
async def test_push_products_creates_posts():
    """Verify posts are created for non-duplicate products."""
    call_log = []

    async def mock_request(method, url, **kwargs):
        call_log.append((method, url))

        # GET selection profiles
        if method == "GET" and "/internal/selection-profiles" in url:
            return _make_response(200, PROFILES)

        # GET products for project
        if method == "GET" and "/internal/products/for-project/" in url:
            return _make_response(200, PRODUCTS)

        # GET existing posts
        if method == "GET" and "/internal/posts" in url:
            return _make_response(200, EXISTING_POSTS)

        # POST generate links
        if method == "POST" and "/internal/links/generate-for-content" in url:
            return _make_response(200, GENERATED_LINKS)

        # POST create post
        if method == "POST" and url.endswith("/internal/posts"):
            return _make_response(201, CREATED_POST)

        # POST generate image
        if method == "POST" and "/generate-image" in url:
            return _make_response(200, {"status": "ok"})

        return _make_response(404)

    mock_client = AsyncMock(spec=httpx.AsyncClient)

    async def side_effect_get(url, **kwargs):
        return await mock_request("GET", url, **kwargs)

    async def side_effect_post(url, **kwargs):
        return await mock_request("POST", url, **kwargs)

    mock_client.get = AsyncMock(side_effect=side_effect_get)
    mock_client.post = AsyncMock(side_effect=side_effect_post)

    with patch("app.tasks.prism_bridge.httpx.AsyncClient") as MockClientClass:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        MockClientClass.return_value = mock_ctx

        await _push_products(prism_project_id=None, max_products=10)

    # Should have fetched profiles
    get_urls = [url for _, url in call_log if _ == "GET"]
    assert any("/internal/selection-profiles" in u for u in get_urls)

    # Should have fetched products for proj-aaa
    assert any("/internal/products/for-project/proj-aaa" in u for u in get_urls)

    # Should have fetched existing posts
    assert any("/internal/posts" in u for u in get_urls)

    # Should have generated links (only for prod-2, since prod-1 is duplicate)
    post_urls = [url for _, url in call_log if _ == "POST"]
    assert any("/internal/links/generate-for-content" in u for u in post_urls)

    # Should have created a post (only for prod-2)
    post_creation_calls = [u for u in post_urls if u.endswith("/internal/posts")]
    assert len(post_creation_calls) == 1

    # Should have triggered image generation
    assert any("/generate-image" in u for u in post_urls)


@pytest.mark.asyncio
async def test_push_products_skips_duplicates():
    """Products with image_url matching existing posts should be skipped."""
    all_existing = [
        {"id": "post-1", "product_image_url": "https://img.example.com/1.jpg"},
        {"id": "post-2", "product_image_url": "https://img.example.com/2.jpg"},
    ]

    async def mock_request(method, url, **kwargs):
        if method == "GET" and "/internal/selection-profiles" in url:
            return _make_response(200, PROFILES)
        if method == "GET" and "/internal/products/for-project/" in url:
            return _make_response(200, PRODUCTS)
        if method == "GET" and "/internal/posts" in url:
            return _make_response(200, all_existing)
        return _make_response(200, [])

    mock_client = AsyncMock(spec=httpx.AsyncClient)

    async def _get(url, **kw):
        return await mock_request("GET", url, **kw)

    async def _post(url, **kw):
        return await mock_request("POST", url, **kw)

    mock_client.get = AsyncMock(side_effect=_get)
    mock_client.post = AsyncMock(side_effect=_post)

    with patch("app.tasks.prism_bridge.httpx.AsyncClient") as MockClientClass:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        MockClientClass.return_value = mock_ctx

        await _push_products(prism_project_id=None, max_products=10)

    # No post creation should happen since all products are duplicates
    post_calls = [
        call for call in mock_client.post.call_args_list
        if str(call).endswith("/internal/posts')")
        or (len(call.args) > 0 and str(call.args[0]).endswith("/internal/posts"))
    ]
    # The generate-for-content call should NOT have happened because products list is empty after dedup
    link_gen_calls = [
        call for call in mock_client.post.call_args_list
        if len(call.args) > 0 and "/internal/links/generate-for-content" in str(call.args[0])
    ]
    assert len(link_gen_calls) == 0


@pytest.mark.asyncio
async def test_push_products_no_profiles_uses_default():
    """When no profiles exist, _push_default is called."""
    default_products = [
        {
            "id": "prod-default",
            "title": "Default Product",
            "marketplace": "gdeslon",
            "image_url": "https://img.example.com/default.jpg",
            "product_url": "https://example.com/default",
        }
    ]
    default_links = [
        {"product_id": "prod-default", "affiliate_url": "https://aff.example.com/default"},
    ]

    async def mock_request(method, url, **kwargs):
        if method == "GET" and "/internal/selection-profiles" in url:
            return _make_response(200, [])  # No profiles
        if method == "GET" and "/internal/products/for-project/" in url:
            return _make_response(200, default_products)
        if method == "POST" and "/internal/links/generate-for-content" in url:
            return _make_response(200, default_links)
        if method == "POST" and url.endswith("/internal/posts"):
            return _make_response(201, {"id": "post-default"})
        if method == "POST" and "/generate-image" in url:
            return _make_response(200, {"status": "ok"})
        return _make_response(200, [])

    mock_client = AsyncMock(spec=httpx.AsyncClient)

    async def _get(url, **kw):
        return await mock_request("GET", url, **kw)

    async def _post(url, **kw):
        return await mock_request("POST", url, **kw)

    mock_client.get = AsyncMock(side_effect=_get)
    mock_client.post = AsyncMock(side_effect=_post)

    with patch("app.tasks.prism_bridge.httpx.AsyncClient") as MockClientClass:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        MockClientClass.return_value = mock_ctx

        await _push_products(prism_project_id="proj-test", max_products=5)

    # Should have fetched products via default path
    get_calls = [call.args[0] for call in mock_client.get.call_args_list]
    assert any("/internal/products/for-project/" in u for u in get_calls)


@pytest.mark.asyncio
async def test_push_products_inactive_profile_skipped():
    """Inactive profiles should be skipped."""
    inactive_profiles = [
        {
            "id": "profile-inactive",
            "prism_project_id": "proj-bbb",
            "is_active": False,
            "max_products": 5,
        }
    ]

    async def mock_request(method, url, **kwargs):
        if method == "GET" and "/internal/selection-profiles" in url:
            return _make_response(200, inactive_profiles)
        return _make_response(200, [])

    mock_client = AsyncMock(spec=httpx.AsyncClient)

    async def _get(url, **kw):
        return await mock_request("GET", url, **kw)

    async def _post(url, **kw):
        return await mock_request("POST", url, **kw)

    mock_client.get = AsyncMock(side_effect=_get)
    mock_client.post = AsyncMock(side_effect=_post)

    with patch("app.tasks.prism_bridge.httpx.AsyncClient") as MockClientClass:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        MockClientClass.return_value = mock_ctx

        await _push_products(prism_project_id=None, max_products=10)

    # No product fetch should happen for inactive profile
    get_calls = [call.args[0] for call in mock_client.get.call_args_list]
    product_fetches = [u for u in get_calls if "/internal/products/for-project/" in u]
    assert len(product_fetches) == 0
