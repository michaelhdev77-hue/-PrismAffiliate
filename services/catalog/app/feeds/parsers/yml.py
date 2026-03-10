"""
Yandex Market Language (YML) parser.
Used by Admitad and GdeSlon product feeds.
"""
from __future__ import annotations

from xml.etree import ElementTree as ET
from typing import Optional


def parse_yml_feed(raw: bytes, niche_mapping: dict = None, category_mapping: dict = None) -> list[dict]:
    """
    Parse a YML (Yandex Market Language) feed and return a list of normalized product dicts.
    Each dict maps to the Product model fields.
    """
    niche_mapping = niche_mapping or {}
    category_mapping = category_mapping or {}
    results = []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return results

    shop = root.find("shop")
    if shop is None:
        return results

    currencies: dict[str, float] = {}
    for cur in shop.findall("currencies/currency"):
        cid = cur.get("id", "")
        rate = cur.get("rate", "1")
        try:
            currencies[cid] = float(rate)
        except ValueError:
            currencies[cid] = 1.0

    categories: dict[str, str] = {}
    for cat in shop.findall("categories/category"):
        categories[cat.get("id", "")] = cat.text or ""

    for offer in shop.findall("offers/offer"):
        try:
            external_id = offer.get("id", "")
            raw_name = offer.findtext("name") or ""
            # Some feeds (e.g. Shopee) put literal "None" as name
            if raw_name.lower() in ("none", ""):
                raw_name = ""
            title = (
                raw_name
                or offer.findtext("model")
                or offer.findtext("typePrefix")
                or offer.findtext("category_name")
                or ""
            )
            price = float(offer.findtext("price") or 0)
            currency_id = offer.findtext("currencyId") or "RUB"
            cat_id = offer.findtext("categoryId") or ""
            cat_name = category_mapping.get(cat_id) or categories.get(cat_id, cat_id)

            picture = offer.findtext("picture") or ""
            url = offer.findtext("url") or ""
            available = offer.get("available", "true").lower() != "false"
            vendor = offer.findtext("vendor")
            description = offer.findtext("description") or ""

            # Try to extract commission from sales_notes or custom params
            commission_rate = 0.0
            sales_notes = offer.findtext("sales_notes") or ""
            for param in offer.findall("param"):
                if param.get("name", "").lower() in ("комиссия", "commission", "cashback"):
                    try:
                        commission_rate = float((param.text or "0").replace("%", "").strip())
                    except ValueError:
                        pass

            tags = [p.text for p in offer.findall("param") if p.text]
            niche = niche_mapping.get(cat_id) or niche_mapping.get(cat_name)

            # Original price
            original_price = None
            discount_pct = None
            old_price = offer.findtext("oldprice")
            if old_price:
                try:
                    original_price = float(old_price)
                    if original_price > price:
                        discount_pct = round((original_price - price) / original_price * 100, 1)
                except ValueError:
                    pass

            # Rating
            rating = None
            rating_text = offer.findtext("rating")
            if rating_text:
                try:
                    rating = float(rating_text)
                except ValueError:
                    pass

            results.append({
                "external_id": external_id,
                "title": title,
                "description": description[:2000] if description else None,
                "category": cat_name,
                "brand": vendor,
                "price": price,
                "currency": currency_id,
                "original_price": original_price,
                "discount_pct": discount_pct,
                "image_url": picture,
                "product_url": url,
                "rating": rating,
                "review_count": None,
                "in_stock": available,
                "commission_rate": commission_rate,
                "commission_type": "percentage",
                "tags": tags,
                "niche": niche,
            })
        except (ValueError, TypeError, AttributeError):
            continue

    return results
