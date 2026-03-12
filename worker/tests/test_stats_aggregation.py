"""Tests for stats_aggregation task — _aggregate_daily_stats() async function."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import date, timedelta
from collections import namedtuple


ClickRow = namedtuple("ClickRow", ["product_id", "marketplace", "prism_project_id", "prism_content_id", "clicks"])
ConvRow = namedtuple("ConvRow", ["product_id", "marketplace", "prism_project_id", "prism_content_id", "conversions", "revenue", "commission"])


def _make_mock_session(click_rows, conv_rows):
    """Create a mock async DB session that returns given rows for sequential queries."""
    session = AsyncMock()
    call_count = {"n": 0}

    async def mock_execute(stmt):
        result = MagicMock()
        if call_count["n"] == 0:
            result.all.return_value = click_rows
        else:
            result.all.return_value = conv_rows
        call_count["n"] += 1
        return result

    session.execute = AsyncMock(side_effect=mock_execute)
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.mark.asyncio
async def test_aggregate_combines_clicks_and_conversions():
    """Stats should combine click and conversion data for the same key."""
    click_rows = [
        ClickRow("prod-1", "gdeslon", "proj-1", "content-1", 50),
        ClickRow("prod-2", "admitad", "proj-1", "content-2", 30),
    ]
    conv_rows = [
        ConvRow("prod-1", "gdeslon", "proj-1", "content-1", 5, 1000.0, 100.0),
    ]

    tracker_session = _make_mock_session(click_rows, conv_rows)
    analytics_session = _make_mock_session([], [])  # analytics session for upsert

    call_index = {"n": 0}

    def make_session_factory(session):
        def factory():
            return session
        return factory

    with patch("app.tasks.stats_aggregation._make_tracker_session", return_value=tracker_session), \
         patch("app.tasks.stats_aggregation._make_analytics_session", return_value=analytics_session):

        from app.tasks.stats_aggregation import _aggregate_daily_stats
        await _aggregate_daily_stats()

    # Analytics session should have received execute calls for upserts
    assert analytics_session.execute.call_count >= 2  # 2 stat rows
    assert analytics_session.commit.call_count == 1


@pytest.mark.asyncio
async def test_aggregate_conversions_without_clicks():
    """Conversions without matching clicks should still create stat rows."""
    click_rows = []
    conv_rows = [
        ConvRow("prod-3", "amazon", "proj-2", "content-3", 3, 500.0, 50.0),
    ]

    tracker_session = _make_mock_session(click_rows, conv_rows)
    analytics_session = _make_mock_session([], [])

    with patch("app.tasks.stats_aggregation._make_tracker_session", return_value=tracker_session), \
         patch("app.tasks.stats_aggregation._make_analytics_session", return_value=analytics_session):

        from app.tasks.stats_aggregation import _aggregate_daily_stats
        await _aggregate_daily_stats()

    # Should upsert 1 stat row (conversions only)
    assert analytics_session.execute.call_count >= 1
    assert analytics_session.commit.call_count == 1


@pytest.mark.asyncio
async def test_aggregate_no_data():
    """When there are no clicks or conversions, no upserts should happen."""
    tracker_session = _make_mock_session([], [])
    analytics_session = _make_mock_session([], [])

    with patch("app.tasks.stats_aggregation._make_tracker_session", return_value=tracker_session), \
         patch("app.tasks.stats_aggregation._make_analytics_session", return_value=analytics_session):

        from app.tasks.stats_aggregation import _aggregate_daily_stats
        await _aggregate_daily_stats()

    # No upserts, but commit should still be called
    assert analytics_session.commit.call_count == 1


@pytest.mark.asyncio
async def test_aggregate_multiple_products():
    """Multiple products with clicks and conversions should all be aggregated."""
    click_rows = [
        ClickRow("prod-a", "gdeslon", "proj-1", "c1", 10),
        ClickRow("prod-b", "gdeslon", "proj-1", "c2", 20),
        ClickRow("prod-c", "admitad", "proj-2", "c3", 30),
    ]
    conv_rows = [
        ConvRow("prod-a", "gdeslon", "proj-1", "c1", 1, 100.0, 10.0),
        ConvRow("prod-c", "admitad", "proj-2", "c3", 3, 300.0, 30.0),
    ]

    tracker_session = _make_mock_session(click_rows, conv_rows)
    analytics_session = _make_mock_session([], [])

    with patch("app.tasks.stats_aggregation._make_tracker_session", return_value=tracker_session), \
         patch("app.tasks.stats_aggregation._make_analytics_session", return_value=analytics_session):

        from app.tasks.stats_aggregation import _aggregate_daily_stats
        await _aggregate_daily_stats()

    # 3 stat rows should be upserted (prod-a, prod-b, prod-c)
    assert analytics_session.execute.call_count >= 3
    assert analytics_session.commit.call_count == 1
