from unittest.mock import patch, MagicMock

import pytest
import httpx

from shared.adapters import (
    get_adapter,
    BaseMarketplaceAdapter,
    ProductSearchResult,
)
from shared.adapters.gdeslon import GdeSlonAdapter
from shared.adapters.admitad import AdmitadAdapter
from shared.adapters.amazon import AmazonAdapter
from shared.adapters.ebay import EbayAdapter
from shared.adapters.cj_affiliate import CJAffiliateAdapter
from shared.adapters.awin import AwinAdapter
from shared.adapters.rakuten import RakutenAdapter
from shared.adapters.aliexpress import AliExpressAdapter


# ---------------------------------------------------------------------------
# get_adapter() registry tests
# ---------------------------------------------------------------------------

class TestGetAdapter:
    def test_returns_admitad_adapter(self):
        adapter = get_adapter("admitad")
        assert isinstance(adapter, AdmitadAdapter)

    def test_returns_gdeslon_adapter(self):
        adapter = get_adapter("gdeslon")
        assert isinstance(adapter, GdeSlonAdapter)

    def test_returns_amazon_adapter(self):
        adapter = get_adapter("amazon")
        assert isinstance(adapter, AmazonAdapter)

    def test_returns_ebay_adapter(self):
        adapter = get_adapter("ebay")
        assert isinstance(adapter, EbayAdapter)

    def test_returns_cj_affiliate_adapter(self):
        adapter = get_adapter("cj_affiliate")
        assert isinstance(adapter, CJAffiliateAdapter)

    def test_returns_awin_adapter(self):
        adapter = get_adapter("awin")
        assert isinstance(adapter, AwinAdapter)

    def test_returns_rakuten_adapter(self):
        adapter = get_adapter("rakuten")
        assert isinstance(adapter, RakutenAdapter)

    def test_returns_aliexpress_adapter(self):
        adapter = get_adapter("aliexpress")
        assert isinstance(adapter, AliExpressAdapter)

    def test_all_adapters_are_base_instances(self):
        for name in ["admitad", "gdeslon", "amazon", "ebay", "cj_affiliate", "awin", "rakuten", "aliexpress"]:
            adapter = get_adapter(name)
            assert isinstance(adapter, BaseMarketplaceAdapter)

    def test_unknown_marketplace_raises(self):
        with pytest.raises(ValueError, match="No adapter registered"):
            get_adapter("unknown_marketplace")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="No adapter registered"):
            get_adapter("")


# ---------------------------------------------------------------------------
# GdeSlonAdapter._parse_yml_response()
# ---------------------------------------------------------------------------

SAMPLE_YML = b"""<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog date="2024-01-01">
  <shop>
    <name>TestShop</name>
    <currencies>
      <currency id="RUB" rate="1"/>
      <currency id="USD" rate="90"/>
    </currencies>
    <categories>
      <category id="1">Electronics</category>
      <category id="2">Clothing</category>
    </categories>
    <offers>
      <offer id="1001" available="true">
        <name>Smartphone XYZ</name>
        <url>https://shop.example.com/1001</url>
        <price>29990</price>
        <currencyId>RUB</currencyId>
        <categoryId>1</categoryId>
        <picture>https://img.example.com/1001.jpg</picture>
        <description>Great smartphone with 128GB</description>
        <vendor>BrandX</vendor>
        <sales_notes>5</sales_notes>
        <param name="Color">Black</param>
        <param name="Size">6.5 inch</param>
      </offer>
      <offer id="1002" available="false">
        <name>Winter Jacket</name>
        <url>https://shop.example.com/1002</url>
        <price>5990</price>
        <currencyId>RUB</currencyId>
        <categoryId>2</categoryId>
        <picture>https://img.example.com/1002.jpg</picture>
        <description>Warm winter jacket</description>
      </offer>
      <offer id="1003" available="true">
        <model>Headphones Pro</model>
        <url>https://shop.example.com/1003</url>
        <price>7990</price>
        <currencyId>USD</currencyId>
        <categoryId>1</categoryId>
      </offer>
    </offers>
  </shop>
</yml_catalog>"""


class TestGdeSlonParseYml:
    def setup_method(self):
        self.adapter = GdeSlonAdapter()

    def test_parses_offers(self):
        results = self.adapter._parse_yml_response(SAMPLE_YML)
        assert len(results) == 3

    def test_first_offer_fields(self):
        results = self.adapter._parse_yml_response(SAMPLE_YML)
        r = results[0]
        assert isinstance(r, ProductSearchResult)
        assert r.external_id == "1001"
        assert r.title == "Smartphone XYZ"
        assert r.description == "Great smartphone with 128GB"
        assert r.category == "Electronics"
        assert r.price == 29990.0
        assert r.currency == "RUB"
        assert r.image_url == "https://img.example.com/1001.jpg"
        assert r.product_url == "https://shop.example.com/1001"
        assert r.in_stock is True
        assert r.commission_rate == 5.0
        assert r.commission_type == "percentage"
        assert r.brand == "BrandX"
        assert "Black" in r.tags
        assert "6.5 inch" in r.tags
        assert r.raw_data == {"yml_offer_id": "1001"}

    def test_out_of_stock_offer(self):
        results = self.adapter._parse_yml_response(SAMPLE_YML)
        r = results[1]
        assert r.external_id == "1002"
        assert r.in_stock is False
        assert r.category == "Clothing"

    def test_offer_with_model_tag(self):
        """When <name> is absent, <model> is used as title."""
        results = self.adapter._parse_yml_response(SAMPLE_YML)
        r = results[2]
        assert r.title == "Headphones Pro"
        assert r.currency == "USD"

    def test_missing_fields_handled_gracefully(self):
        """Offer with minimal fields should still parse."""
        yml = b"""<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog>
  <shop>
    <currencies/>
    <categories/>
    <offers>
      <offer id="9999">
        <price>100</price>
        <url>https://example.com</url>
      </offer>
    </offers>
  </shop>
</yml_catalog>"""
        results = self.adapter._parse_yml_response(yml)
        assert len(results) == 1
        r = results[0]
        assert r.external_id == "9999"
        assert r.price == 100.0
        assert r.title == ""  # no name/model/typePrefix
        assert r.image_url == ""
        assert r.description == ""
        assert r.brand is None
        assert r.tags == []

    def test_empty_xml(self):
        results = self.adapter._parse_yml_response(b"")
        assert results == []

    def test_invalid_xml(self):
        results = self.adapter._parse_yml_response(b"not xml at all")
        assert results == []

    def test_no_shop_element(self):
        yml = b"""<?xml version="1.0"?><yml_catalog><other/></yml_catalog>"""
        results = self.adapter._parse_yml_response(yml)
        assert results == []

    def test_no_offers(self):
        yml = b"""<?xml version="1.0"?>
<yml_catalog>
  <shop>
    <currencies/>
    <categories/>
    <offers/>
  </shop>
</yml_catalog>"""
        results = self.adapter._parse_yml_response(yml)
        assert results == []

    def test_offer_with_bad_price_is_skipped(self):
        yml = b"""<?xml version="1.0"?>
<yml_catalog>
  <shop>
    <currencies/>
    <categories/>
    <offers>
      <offer id="bad">
        <price>not_a_number</price>
      </offer>
      <offer id="good">
        <price>100</price>
      </offer>
    </offers>
  </shop>
</yml_catalog>"""
        results = self.adapter._parse_yml_response(yml)
        assert len(results) == 1
        assert results[0].external_id == "good"


# ---------------------------------------------------------------------------
# AdmitadAdapter
# ---------------------------------------------------------------------------

class TestAdmitadAdapter:
    def setup_method(self):
        self.adapter = AdmitadAdapter()
        self.credentials = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "website_id": 12345,
            "campaign_id": 67890,
            "access_token": "test-token-123",
            "token_expires_at": "9999999999",  # far future
        }

    def test_search_products_raises(self):
        with pytest.raises(NotImplementedError, match="Admitad does not provide product search"):
            self.adapter.search_products("test", self.credentials)

    @patch("shared.adapters.admitad.httpx.get")
    def test_generate_affiliate_link(self, mock_get):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"link": "https://ad.admitad.com/g/abc123/"}]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = self.adapter.generate_affiliate_link(
            "https://shop.example.com/product/1",
            self.credentials,
            sub_id="my-sub-id",
        )

        assert result.affiliate_url == "https://ad.admitad.com/g/abc123/"
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["params"]["ulp"] == "https://shop.example.com/product/1"
        assert call_kwargs.kwargs["params"]["subid"] == "my-sub-id"
        assert "Bearer test-token-123" in call_kwargs.kwargs["headers"]["Authorization"]

    @patch("shared.adapters.admitad.httpx.get")
    def test_generate_affiliate_link_without_subid(self, mock_get):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"link": "https://ad.admitad.com/g/def456/"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = self.adapter.generate_affiliate_link(
            "https://shop.example.com/product/2",
            self.credentials,
        )

        assert result.affiliate_url == "https://ad.admitad.com/g/def456/"
        call_kwargs = mock_get.call_args
        assert "subid" not in call_kwargs.kwargs["params"]

    @patch("shared.adapters.admitad.httpx.post")
    def test_token_refresh(self, mock_post):
        """When token is expired, _get_token calls _refresh_token."""
        credentials = {
            "client_id": "test-id",
            "client_secret": "test-secret",
            "website_id": 12345,
            "campaign_id": 67890,
            "access_token": "old-token",
            "token_expires_at": "0",  # expired
        }

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "new-refreshed-token",
            "expires_in": 3600,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        token = self.adapter._get_token(credentials)

        assert token == "new-refreshed-token"
        assert credentials["access_token"] == "new-refreshed-token"
        mock_post.assert_called_once_with(
            "https://api.admitad.com/token/",
            data={
                "grant_type": "client_credentials",
                "client_id": "test-id",
                "client_secret": "test-secret",
                "scope": "deeplink_generator public_data websites advcampaigns advcampaigns_for_website",
            },
            timeout=15,
        )

    def test_get_token_uses_cached_when_valid(self):
        """When token_expires_at is in the future, cached token is returned."""
        token = self.adapter._get_token(self.credentials)
        assert token == "test-token-123"

    @patch("shared.adapters.admitad.httpx.get")
    def test_healthcheck_ok(self, mock_get):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"name": "My Website", "id": 12345}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = self.adapter.healthcheck(self.credentials)

        assert result["status"] == "ok"
        assert result["website"] == "My Website"
        assert result["website_id"] == 12345

    @patch("shared.adapters.admitad.httpx.get")
    def test_healthcheck_error(self, mock_get):
        mock_get.side_effect = httpx.ConnectTimeout("Connection timed out")

        result = self.adapter.healthcheck(self.credentials)

        assert result["status"] == "error"
        assert "timed out" in result["detail"].lower()


# ---------------------------------------------------------------------------
# GdeSlonAdapter — generate_affiliate_link
# ---------------------------------------------------------------------------

class TestGdeSlonGenerateLink:
    def setup_method(self):
        self.adapter = GdeSlonAdapter()

    def test_with_affiliate_id(self):
        credentials = {"api_key": "abc", "affiliate_id": "my-aff-id"}
        result = self.adapter.generate_affiliate_link(
            "https://shop.example.com/product/1", credentials
        )
        assert "my-aff-id" in result.affiliate_url
        assert "_gs_at=my-aff-id" in result.affiliate_url

    def test_with_affiliate_id_url_has_query(self):
        credentials = {"api_key": "abc", "affiliate_id": "aff123"}
        result = self.adapter.generate_affiliate_link(
            "https://shop.example.com/product/1?ref=test", credentials
        )
        assert "&_gs_at=aff123" in result.affiliate_url

    def test_without_affiliate_id(self):
        credentials = {"api_key": "abc"}
        result = self.adapter.generate_affiliate_link(
            "https://shop.example.com/product/1", credentials
        )
        assert result.affiliate_url == "https://shop.example.com/product/1"


# ---------------------------------------------------------------------------
# GdeSlonAdapter — healthcheck
# ---------------------------------------------------------------------------

class TestGdeSlonHealthcheck:
    def setup_method(self):
        self.adapter = GdeSlonAdapter()

    @patch("shared.adapters.gdeslon.httpx.get")
    def test_healthcheck_ok(self, mock_get):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = self.adapter.healthcheck({"api_key": "test-key"})
        assert result["status"] == "ok"

    @patch("shared.adapters.gdeslon.httpx.get")
    def test_healthcheck_error(self, mock_get):
        mock_get.side_effect = httpx.ConnectTimeout("timeout")

        result = self.adapter.healthcheck({"api_key": "test-key"})
        assert result["status"] == "error"
        assert "timeout" in result["detail"].lower()
