# Prism Affiliate — Инструкции для Claude Code

## Проект

Standalone платформа агрегации affiliate-товаров с маркетплейсов. Парсит фиды, генерирует партнёрские ссылки, трекает клики/конверсии. Интегрируется с PRISM для вставки ссылок в видео-описания.

**Путь**: `e:/!PrismAffiliate`
**Связанный проект**: `e:/!Prism` (PRISM — основная видео-платформа)

---

## Архитектура

Микросервисы на Python/FastAPI. Отдельный docker-compose, отдельные БД.

| Сервис | Порт | Роль | БД |
|--------|------|------|----|
| catalog | 8011 | Товары, фиды, аккаунты маркетплейсов | catalog_db (5434) |
| links | 8012 | Генерация affiliate ссылок, профили подбора | links_db (5435) |
| tracker | 8013 | Click tracking `/r/{code}`, вебхуки конверсий | tracker_db (5436) |
| analytics | 8014 | Агрегация статистики, дашборды | analytics_db (5437) |
| worker | — | Celery worker (фиды, агрегация, refresh ссылок) | — |
| scheduler | — | Celery Beat (запускается из worker-контейнера) | — |
| frontend | 3001 | Next.js | — |

**Инфраструктура**: 4 PostgreSQL 16, Redis 7 (порт 6380).

---

## Ключевые пути

```
services/
  catalog/app/
    models/         # MarketplaceAccount, Product, ProductFeed
    routes/         # marketplace_accounts, feeds, products, internal
    feeds/parsers/  # yml.py — Yandex Market Language парсер
    config.py / db.py / deps.py / main.py

  links/app/
    models/         # AffiliateLink, SelectionProfile
    routes/         # links, profiles, internal
    services/       # link_generator.py, product_selector.py
    config.py / db.py / deps.py / main.py

  tracker/app/
    models/         # ClickEvent, ConversionEvent
    routes/         # redirect.py (/r/{code}), webhooks.py
    config.py / db.py / main.py

  analytics/app/
    models/         # AffiliateStats
    routes/         # analytics.py
    config.py / db.py / deps.py / main.py

shared/shared/
  adapters/         # Адаптеры маркетплейсов (8 штук)
    base.py         # BaseMarketplaceAdapter (ABC)
    amazon.py / ebay.py / aliexpress.py / rakuten.py
    cj_affiliate.py / awin.py / admitad.py / gdeslon.py
  encryption.py     # Fernet-шифрование credentials
  http_client.py    # Общий async HTTP клиент

worker/app/
  tasks/
    feed_ingestion.py   # Синк фидов с маркетплейсов
    link_refresh.py     # Refresh истекающих ссылок
    stats_aggregation.py # Агрегация суточной статистики
    healthcheck.py      # Проверка аккаунтов маркетплейсов
    _*_models.py        # ORM-импорты для каждой БД
  celery_app.py         # Celery + Beat schedule
  config.py             # URL всех БД и сервисов

frontend/src/
  app/                  # Страницы (accounts, feeds, products, links, analytics)
  components/           # AuthGuard, Sidebar, MetricCard
  lib/api.ts            # Все HTTP-запросы к сервисам
  lib/auth.ts           # JWT управление
```

---

## Базы данных

| БД | Владелец | Что хранит |
|----|----------|------------|
| catalog_db | catalog | MarketplaceAccount, Product, ProductFeed |
| links_db | links | AffiliateLink, SelectionProfile |
| tracker_db | tracker | ClickEvent, ConversionEvent |
| analytics_db | analytics | AffiliateStats |

**Важно**: каждый сервис работает только со своей БД. Worker импортирует модели из всех четырёх БД через отдельные async-сессии. Межсервисное взаимодействие — только через HTTP API или через worker-задачи.

---

## Адаптеры маркетплейсов (shared/adapters/)

Все адаптеры наследуют `BaseMarketplaceAdapter`:

```python
search_products(query, credentials, filters) → ProductSearchResult[]
generate_affiliate_link(product_url, credentials) → AffiliateLinkResult
fetch_feed(feed_url, credentials) → bytes
healthcheck(credentials) → dict
```

| Адаптер | Маркетплейс | Метод |
|---------|-------------|-------|
| AmazonAdapter | Amazon | API, OAuth2 |
| eBayAdapter | eBay | Browse API, OAuth2 |
| AliExpressAdapter | AliExpress | Open Platform |
| RakutenAdapter | Rakuten | Product Search |
| CJAffiliateAdapter | Commission Junction | GraphQL |
| AwinAdapter | Awin | Link Builder API |
| AdmitadAdapter | Ozon, Мегамаркет, AliExpress RU | deeplink API + YML фиды |
| GdeSlonAdapter | ~400 РФ магазинов | `/api/search.xml` |

**При добавлении нового адаптера**: создай файл в `shared/shared/adapters/`, унаследуй `BaseMarketplaceAdapter`, зарегистрируй в catalog-сервисе, добавь в worker/tasks/healthcheck.py.

---

## Шедулер (Celery Beat в worker/app/celery_app.py)

| Расписание | Задача | Файл |
|------------|--------|------|
| каждые 15 мин | `dispatch_feed_syncs` | feed_ingestion.py |
| каждые 30 мин | `refresh_expiring_links` | link_refresh.py |
| 02:00 | `aggregate_daily_stats` | stats_aggregation.py |
| каждые 6 ч | `healthcheck_accounts` | healthcheck.py |

Scheduler не запускается отдельным контейнером — он запускается командой `celery beat` внутри worker-контейнера.

---

## Интеграция с PRISM

Два хука в PRISM-пайплайне (`e:/!Prism`):

1. **После генерации идеи**: `GET /internal/products/for-project/{prism_project_id}` → данные о товарах передаются в скрипт
2. **Перед публикацией**: `POST /internal/links/generate-for-content` → affiliate ссылки вставляются в описание видео

**Что затрагивается в PRISM при изменении internal API:**
- `e:/!Prism/backend/app/core/` — добавить/обновить affiliate_client.py
- `e:/!Prism/backend/app/worker/tasks.py` — шаги пайплайна
- `e:/!Prism/backend/app/core/config.py` — `AFFILIATE_SERVICE_URL`

**Общий JWT**: `SECRET_KEY` должен совпадать с PRISM (`.env` обоих проектов).

---

## Межсервисные зависимости

| Что меняешь | Что затрагивается |
|-------------|-------------------|
| Модель Product (catalog) | Worker-задачи `_catalog_models.py`, links/services/product_selector.py, фронтенд |
| Модель AffiliateLink (links) | Worker-задачи `_links_models.py`, tracker (redirect lookup), analytics |
| BaseMarketplaceAdapter (shared) | Все 8 адаптеров, catalog/routes/internal.py, worker/tasks/feed_ingestion.py |
| Internal API endpoint | Клиент в PRISM backend (affiliate_client.py), worker/tasks.py в PRISM |
| Схема ответа сервиса | `frontend/src/lib/api.ts`, TypeScript-типы компонентов |
| Celery-задача | celery_app.py beat schedule, config.py (DB URLs) |
| ENV-переменная | `.env.example`, `docker-compose.yml`, `config.py` нужного сервиса |
| encryption.py (shared) | Все сервисы, использующие `credentials_encrypted` |

---

## Паттерны и соглашения

**Python-сервисы (идентично PRISM):**
- Конфиг через `config.py` + Pydantic Settings (из ENV)
- SQLAlchemy 2.0 async через `db.py` + `deps.py`
- Pydantic v2 для схем
- Async HTTP через `shared/http_client.py`
- Публичные роуты: `/api/v1/*`, внутренние: `/internal/*`, health: `/health`

**Шифрование credentials:**
- `credentials_encrypted` — Fernet-зашифрованный JSON через `shared/encryption.py`
- `ENCRYPTION_KEY` из ENV, должен совпадать во всех сервисах
- Расшифровывается только в момент вызова адаптера

**Shared-пакет:**
- Устанавливается через `pip install -e ./shared` в каждом сервисе
- Изменение `shared/` затрагивает все сервисы — пересобирай все образы

**Фронтенд (идентично PRISM):**
- Все API-вызовы только через `lib/api.ts`
- Tailwind CSS, Next.js 14 app directory
- `AuthGuard.tsx` оборачивает все защищённые страницы

---

## Обязательные проверки при задачах

### Добавление поля в модель
- [ ] SQLAlchemy-модель в сервисе
- [ ] Pydantic-схема (request/response)
- [ ] Alembic-миграция
- [ ] Worker-импорт `_*_models.py` если задача читает эту модель
- [ ] `lib/api.ts` и TypeScript-типы на фронтенде

### Добавление нового адаптера маркетплейса
- [ ] `shared/shared/adapters/{name}.py` — наследовать BaseMarketplaceAdapter
- [ ] Регистрация в catalog-сервисе
- [ ] `worker/tasks/healthcheck.py`
- [ ] `worker/tasks/feed_ingestion.py` если поддерживает фиды
- [ ] ENV-переменные в `.env.example` и `docker-compose.yml`

### Добавление новой Celery-задачи
- [ ] Файл в `worker/app/tasks/`
- [ ] Запись в `worker/app/celery_app.py` beat schedule если schedulable
- [ ] Нужные DB URL в `worker/app/config.py`

### Изменение internal API (для интеграции с PRISM)
- [ ] Route в нужном сервисе (`routes/internal.py`)
- [ ] Клиент в `e:/!Prism/backend/app/core/`
- [ ] Использование клиента в `e:/!Prism/backend/app/worker/tasks.py`

### Изменение shared-пакета
- [ ] Обновить `shared/shared/adapters/base.py` или другой файл
- [ ] Проверить все адаптеры на совместимость с изменённым интерфейсом
- [ ] Пересборка всех Docker-образов (`docker-compose build`)

### Изменение ENV-переменной
- [ ] `.env.example`
- [ ] `docker-compose.yml` — environment нужного сервиса
- [ ] `config.py` сервиса

---

## Entry Points для разработки

- **Frontend**: http://localhost:3001
- **Catalog API docs**: http://localhost:8011/docs
- **Links API docs**: http://localhost:8012/docs
- **Tracker API docs**: http://localhost:8013/docs
- **Analytics API docs**: http://localhost:8014/docs
