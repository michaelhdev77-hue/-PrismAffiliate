"""
Worker test configuration.
Override env vars BEFORE any app modules are imported.
"""
import os

os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["CATALOG_DB_URL"] = "sqlite+aiosqlite:///test_worker_catalog.db"
os.environ["LINKS_DB_URL"] = "sqlite+aiosqlite:///test_worker_links.db"
os.environ["TRACKER_DB_URL"] = "sqlite+aiosqlite:///test_worker_tracker.db"
os.environ["ANALYTICS_DB_URL"] = "sqlite+aiosqlite:///test_worker_analytics.db"
os.environ["CATALOG_SERVICE_URL"] = "http://mock-catalog:8011"
os.environ["LINKS_SERVICE_URL"] = "http://mock-links:8012"
os.environ["PRISM_CONTENT_URL"] = "http://mock-content:8007"
os.environ["ENCRYPTION_KEY"] = "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXRlcw=="

import pytest
