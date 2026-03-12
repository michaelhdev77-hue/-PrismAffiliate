import { getToken } from './auth'

const CATALOG  = process.env.NEXT_PUBLIC_CATALOG_URL  || 'http://localhost:8011'
const LINKS    = process.env.NEXT_PUBLIC_LINKS_URL    || 'http://localhost:8012'
const ANALYTICS = process.env.NEXT_PUBLIC_ANALYTICS_URL || 'http://localhost:8014'

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 30000)
  try {
    const token = getToken()
    const res = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...init?.headers,
      },
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(`${res.status}: ${text}`)
    }
    return res.json()
  } finally {
    clearTimeout(timeout)
  }
}

// ── Catalog ────────────────────────────────────────────────────────────
export const api = {
  accounts: {
    list: () => req<Account[]>(`${CATALOG}/api/v1/marketplace-accounts/`),
    create: (body: object) => req<Account>(`${CATALOG}/api/v1/marketplace-accounts/`, { method: 'POST', body: JSON.stringify(body) }),
    healthcheck: (id: string) => req<object>(`${CATALOG}/api/v1/marketplace-accounts/${id}/healthcheck`, { method: 'POST' }),
    discoverPrograms: (id: string) => req<DiscoveredProgram[]>(`${CATALOG}/api/v1/marketplace-accounts/${id}/discover-programs`, { method: 'POST' }),
    delete: (id: string) => fetch(`${CATALOG}/api/v1/marketplace-accounts/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    }),
  },
  campaigns: {
    list: (accountId?: string) => {
      const qs = accountId ? `?marketplace_account_id=${accountId}` : ''
      return req<Campaign[]>(`${CATALOG}/api/v1/campaigns/${qs}`)
    },
    create: (body: object) => req<Campaign>(`${CATALOG}/api/v1/campaigns/`, { method: 'POST', body: JSON.stringify(body) }),
    delete: (id: string) => fetch(`${CATALOG}/api/v1/campaigns/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    }),
  },
  feeds: {
    list: () => req<Feed[]>(`${CATALOG}/api/v1/feeds/`),
    create: (body: object) => req<Feed>(`${CATALOG}/api/v1/feeds/`, { method: 'POST', body: JSON.stringify(body) }),
    sync: (id: string) => req<object>(`${CATALOG}/api/v1/feeds/${id}/sync`, { method: 'POST' }),
    delete: (id: string) => fetch(`${CATALOG}/api/v1/feeds/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    }),
    autoDiscover: (marketplace_account_id: string) =>
      req<Array<{name: string, xml_link: string, csv_link: string, campaign_name: string, campaign_id: string}>>(
        `${CATALOG}/api/v1/feeds/auto-discover`,
        { method: 'POST', body: JSON.stringify({ marketplace_account_id }) }
      ),
  },
  products: {
    search: (params: Record<string, string>) => {
      const qs = new URLSearchParams(params).toString()
      return req<PaginatedProducts>(`${CATALOG}/api/v1/products/?${qs}`)
    },
    get: (id: string) => req<Product>(`${CATALOG}/api/v1/products/${id}`),
    categories: () => req<string[]>(`${CATALOG}/api/v1/products/categories`),
  },
  bridge: {
    pushToPrism: (prism_project_id?: string) =>
      req<{status: string}>(`${CATALOG}/api/v1/bridge/push-to-prism`, {
        method: 'POST',
        body: JSON.stringify({ prism_project_id }),
      }),
  },

  // ── Links ──────────────────────────────────────────────────────────────
  profiles: {
    list: () => req<Profile[]>(`${LINKS}/api/v1/selection-profiles/`),
    create: (body: object) => req<Profile>(`${LINKS}/api/v1/selection-profiles/`, { method: 'POST', body: JSON.stringify(body) }),
    update: (id: string, body: object) => req<Profile>(`${LINKS}/api/v1/selection-profiles/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    delete: (id: string) => fetch(`${LINKS}/api/v1/selection-profiles/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    }),
    run: (prism_project_id: string) =>
      req<{status: string}>(`${CATALOG}/api/v1/bridge/push-to-prism`, {
        method: 'POST',
        body: JSON.stringify({ prism_project_id }),
      }),
  },
  links: {
    list: (params?: Record<string, string>) => {
      const qs = params ? '?' + new URLSearchParams(params).toString() : ''
      return req<Link[]>(`${LINKS}/api/v1/links/${qs}`)
    },
    generate: (product_id: string) =>
      req<Link>(`${LINKS}/api/v1/links/generate`, {
        method: 'POST',
        body: JSON.stringify({ product_id }),
      }),
    generateBulk: (product_ids: string[]) =>
      req<{ created: number, failed: number, links: Link[] }>(`${LINKS}/api/v1/links/generate-bulk`, {
        method: 'POST',
        body: JSON.stringify({ product_ids }),
      }),
  },

  // ── Analytics ─────────────────────────────────────────────────────────
  analytics: {
    overview: (period = 30) => req<AnalyticsOverview>(`${ANALYTICS}/api/v1/analytics/overview?period=${period}`),
    byMarketplace: (period = 30) => req<StatRow[]>(`${ANALYTICS}/api/v1/analytics/by-marketplace?period=${period}`),
    byProduct: (period = 30) => req<StatRow[]>(`${ANALYTICS}/api/v1/analytics/by-product?period=${period}`),
  },
}

// ── Types ──────────────────────────────────────────────────────────────
export interface Account {
  id: string
  marketplace: string
  display_name: string
  is_active: boolean
  health_status: string
  last_health_check: string | null
  created_at: string
}

export interface Campaign {
  id: string
  marketplace_account_id: string
  name: string
  external_campaign_id: string
  marketplace_label: string | null
  config: object
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Feed {
  id: string
  marketplace_account_id: string
  campaign_id: string | null
  name: string
  feed_format: string
  feed_url: string | null
  status: string
  last_sync_at: string | null
  last_sync_products: number
  schedule_cron: string
  last_error: string | null
}

export interface Product {
  id: string
  marketplace: string
  title: string
  category: string
  brand: string | null
  price: number
  currency: string
  original_price: number | null
  discount_pct: number | null
  image_url: string
  product_url: string
  rating: number | null
  review_count: number | null
  in_stock: boolean
  commission_rate: number
  campaign_id: string | null
}

export interface PaginatedProducts {
  items: Product[]
  total: number
  page: number
  pages: number
}

export interface Profile {
  id: string
  prism_project_id: string
  name: string
  marketplaces: string[]
  categories: string[]
  keywords: string[]
  min_commission_rate: number
  min_rating: number
  min_review_count: number
  price_range_min: number
  price_range_max: number
  sort_by: string
  max_products: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Link {
  id: string
  product_id: string
  marketplace: string
  affiliate_url: string
  short_code: string
  prism_project_id: string | null
  expires_at: string | null
  is_active: boolean
  created_at: string
}

export interface AnalyticsOverview {
  total_clicks: number
  total_conversions: number
  total_revenue: number
  total_commission: number
  period_days: number
}

export interface DiscoveredProgram {
  id: string
  name: string
  status: string
  currency: string
  categories: string[]
  avg_money_transfer_time: number | null
  cr: number | null
  ecpc: number | null
}

export interface StatRow {
  dimension: string
  clicks: number
  conversions: number
  revenue: number
  commission: number
}
