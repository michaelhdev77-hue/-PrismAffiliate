"""Tests for feed ingestion task — _parse_feed() function."""
import pytest

from app.tasks.feed_ingestion import _parse_feed


SAMPLE_YML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog>
  <shop>
    <currencies>
      <currency id="RUB" rate="1"/>
    </currencies>
    <categories>
      <category id="1">Electronics</category>
      <category id="2">Clothing</category>
    </categories>
    <offers>
      <offer id="123" available="true">
        <name>Test Product</name>
        <price>999</price>
        <currencyId>RUB</currencyId>
        <picture>https://example.com/img.jpg</picture>
        <url>https://example.com/product/123</url>
        <categoryId>1</categoryId>
        <vendor>TestBrand</vendor>
        <description>A great test product</description>
      </offer>
      <offer id="456">
        <name>None</name>
        <price>100</price>
        <currencyId>RUB</currencyId>
        <url>https://example.com/product/456</url>
        <categoryId>2</categoryId>
      </offer>
      <offer id="789">
        <price>200</price>
        <currencyId>RUB</currencyId>
        <picture>https://example.com/img789.jpg</picture>
        <url>https://example.com/product/789</url>
        <categoryId>1</categoryId>
      </offer>
      <offer id="999">
        <name>Good Product</name>
        <price>500</price>
        <currencyId>RUB</currencyId>
        <url>https://example.com/product/999</url>
        <categoryId>2</categoryId>
      </offer>
    </offers>
  </shop>
</yml_catalog>
"""

# Offer 789 has no <name>, so _clean_title falls back to category name "Electronics".
# In _parse_feed, title == category is filtered out.
# Offer 999 has a real name but NO image — filtered out.

SAMPLE_YML_NO_TITLE_NO_IMAGE = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog>
  <shop>
    <currencies>
      <currency id="RUB" rate="1"/>
    </currencies>
    <categories>
      <category id="1">Phones</category>
    </categories>
    <offers>
      <offer id="100">
        <price>100</price>
        <currencyId>RUB</currencyId>
        <url>https://example.com/product/100</url>
        <categoryId>1</categoryId>
      </offer>
    </offers>
  </shop>
</yml_catalog>
"""


class TestParseFeedBasic:
    """Test _parse_feed with valid YML data."""

    def test_valid_product_included(self):
        """Product 123 has both title and image — should be included."""
        results = _parse_feed(SAMPLE_YML, "yml", {}, {})
        ids = [r["external_id"] for r in results]
        assert "123" in ids

    def test_none_title_filtered(self):
        """Product 456 has title='None' — should be filtered out."""
        results = _parse_feed(SAMPLE_YML, "yml", {}, {})
        ids = [r["external_id"] for r in results]
        assert "456" not in ids

    def test_title_equals_category_filtered(self):
        """Product 789 has no name, falls back to category 'Electronics' which == category — filtered."""
        results = _parse_feed(SAMPLE_YML, "yml", {}, {})
        ids = [r["external_id"] for r in results]
        assert "789" not in ids

    def test_no_image_filtered(self):
        """Product 999 has a real name but no image — should be filtered out."""
        results = _parse_feed(SAMPLE_YML, "yml", {}, {})
        ids = [r["external_id"] for r in results]
        assert "999" not in ids

    def test_only_one_product_passes(self):
        """Only product 123 should pass all filters."""
        results = _parse_feed(SAMPLE_YML, "yml", {}, {})
        assert len(results) == 1
        assert results[0]["external_id"] == "123"

    def test_product_fields_correct(self):
        """Verify all fields of the parsed product."""
        results = _parse_feed(SAMPLE_YML, "yml", {}, {})
        product = results[0]
        assert product["title"] == "Test Product"
        assert product["price"] == 999.0
        assert product["currency"] == "RUB"
        assert product["image_url"] == "https://example.com/img.jpg"
        assert product["product_url"] == "https://example.com/product/123"
        assert product["brand"] == "TestBrand"
        assert product["category"] == "Electronics"
        assert product["description"] == "A great test product"

    def test_all_filtered_returns_empty(self):
        """Feed where all products lack title/image returns empty list."""
        results = _parse_feed(SAMPLE_YML_NO_TITLE_NO_IMAGE, "yml", {}, {})
        assert results == []


class TestParseFeedMappings:
    """Test _parse_feed with niche_mapping and category_mapping."""

    def test_niche_mapping_applied(self):
        """niche_mapping maps original category to a niche value."""
        niche_map = {"Electronics": "tech"}
        results = _parse_feed(SAMPLE_YML, "yml", niche_map, {})
        assert len(results) == 1
        assert results[0]["niche"] == "tech"

    def test_niche_mapping_missing_key(self):
        """If category not in niche_mapping, niche is None."""
        niche_map = {"Clothing": "fashion"}
        results = _parse_feed(SAMPLE_YML, "yml", niche_map, {})
        assert results[0]["niche"] is None

    def test_category_mapping_applied(self):
        """category_mapping renames the category."""
        cat_map = {"Electronics": "Gadgets"}
        results = _parse_feed(SAMPLE_YML, "yml", {}, cat_map)
        assert results[0]["category"] == "Gadgets"

    def test_category_mapping_missing_key(self):
        """If category not in category_mapping, original category is kept."""
        cat_map = {"Clothing": "Apparel"}
        results = _parse_feed(SAMPLE_YML, "yml", {}, cat_map)
        assert results[0]["category"] == "Electronics"

    def test_both_mappings_combined(self):
        """Both niche and category mappings applied together."""
        niche_map = {"Electronics": "tech"}
        cat_map = {"Electronics": "Gadgets"}
        results = _parse_feed(SAMPLE_YML, "yml", niche_map, cat_map)
        assert results[0]["niche"] == "tech"
        assert results[0]["category"] == "Gadgets"


class TestParseFeedFormat:
    """Test _parse_feed with different format arguments."""

    def test_xml_format_works(self):
        """fmt='xml' should work the same as 'yml'."""
        results = _parse_feed(SAMPLE_YML, "xml", {}, {})
        assert len(results) == 1
        assert results[0]["external_id"] == "123"

    def test_unsupported_format_raises(self):
        """Unsupported format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported feed format"):
            _parse_feed(SAMPLE_YML, "csv", {}, {})

    def test_invalid_xml_returns_empty(self):
        """Invalid XML bytes should return an empty list (no crash)."""
        results = _parse_feed(b"not xml at all", "yml", {}, {})
        assert results == []

    def test_empty_feed_returns_empty(self):
        """Empty offers section returns empty list."""
        empty_feed = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog>
  <shop>
    <categories/>
    <offers/>
  </shop>
</yml_catalog>
"""
        results = _parse_feed(empty_feed, "yml", {}, {})
        assert results == []
