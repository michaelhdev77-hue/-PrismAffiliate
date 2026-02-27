"""
Product selection scoring algorithm.
Scores products for a given SelectionProfile and returns sorted list.
"""
from __future__ import annotations


def score_product(product: dict, profile: "SelectionProfile") -> float:
    """
    Multi-factor scoring. Higher = better match for content generation.

    Weights:
      30% commission rate   — maximize revenue
      20% rating quality    — 4.5+ preferred
      15% price sweet spot  — mid-range converts better
      15% review volume     — social proof
      10% discount presence — discounted items get more clicks
      10% in_stock          — filter out OOS
    """
    score = 0.0
    max_commission = 30.0

    # Commission rate (normalize to 30% max)
    commission = product.get("commission_rate") or 0.0
    score += 0.30 * min(commission / max_commission, 1.0)

    # Rating (3.0–5.0 range)
    rating = product.get("rating") or 0.0
    if rating:
        score += 0.20 * max(0.0, (rating - 3.0) / 2.0)

    # Price sweet spot
    price = product.get("price") or 0.0
    p_min = profile.price_range_min or 0.0
    p_max = profile.price_range_max or 0.0
    if p_min > 0 and p_max > p_min:
        mid = (p_min + p_max) / 2
        deviation = abs(price - mid) / mid if mid else 1.0
        score += 0.15 * max(0.0, 1.0 - deviation)
    else:
        score += 0.075  # neutral if no range specified

    # Review volume (normalize to 1000 reviews)
    reviews = product.get("review_count") or 0
    score += 0.15 * min(reviews / 1000.0, 1.0)

    # Discount presence
    discount = product.get("discount_pct") or 0.0
    if discount > 0:
        score += 0.10 * min(discount / 50.0, 1.0)

    # In stock
    if product.get("in_stock"):
        score += 0.10

    return round(score, 4)


def select_products(products: list[dict], profile: "SelectionProfile") -> list[dict]:
    """Apply profile filters, score, sort and return top-N products."""
    filtered = []
    for p in products:
        if profile.min_commission_rate and (p.get("commission_rate") or 0) < profile.min_commission_rate:
            continue
        if profile.min_rating and (p.get("rating") or 0) < profile.min_rating:
            continue
        if profile.min_review_count and (p.get("review_count") or 0) < profile.min_review_count:
            continue
        filtered.append(p)

    if profile.sort_by == "commission":
        filtered.sort(key=lambda x: x.get("commission_rate") or 0, reverse=True)
    elif profile.sort_by == "rating":
        filtered.sort(key=lambda x: x.get("rating") or 0, reverse=True)
    elif profile.sort_by == "score":
        filtered.sort(key=lambda x: score_product(x, profile), reverse=True)

    return filtered[:profile.max_products]
