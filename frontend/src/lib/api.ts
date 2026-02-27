import { getToken } from './auth'

const CATALOG  = process.env.NEXT_PUBLIC_CATALOG_URL  || 'http://localhost:8011'
const LINKS    = process.env.NEXT_PUBLIC_LINKS_URL    || 'http://localhost:8012'
const ANALYTICS = process.env.NEXT_PUBLIC_ANALYTICS_URL || 'http://localhost:8014'

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const res = await fetch(url, {
    ...init,
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
}

// ── Catalog ────────────────────────────────────────────────────────────
export const api = {
  accounts: {
    list: () => req<Account[]>(`${CATALOG}/api/v1/marketplace-accounts/`),
    create: (body: object) => req<Account>(`${CATALOG}/api/v1/marketplace-accounts/`, { method: 'POST', body: JSON.stringify(body) }),
    healthcheck: (id: string) => req<object>(`${CATALOG}/api/v1/marketplace-accounts/${id}/healthcheck`, { method: 'POST' }),
    delete: (id: string) => fetch(`${CATALOG}/api/v1/marketplace-accounts/${id}`, {
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
  },
  products: {
    search: (params: Record<string, string>) => {
      const qs = new URLSearchParams(params).toString()
      return req<Product[]>(`${CATALOG}/api/v1/products/?${qs}`)
    },
    categories: () => req<string[]>(`${CATALOG}/api/v1/products/categories`),
  },

  // ── Links ──────────────────────────────────────────────────────────────
  profiles: {
    list: () => req<Profile[]>(`${LINKS}/api/v1/selection-profiles/`),
    create: (body: object) => req<Profile>(`${LINKS}/api/v1/selection-profiles/`, { method: 'POST', body: JSON.stringify(body) }),
  },
  links: {
    list: (params?: Record<string, string>) => {
      const qs = params ? '?' + new URLSearchParams(params).toString() : ''
      return req<Link[]>(`${LINKS}/api/v1/links/${qs}`)
    },
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

export interface Feed {
  id: string
  marketplace_account_id: string
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
  rating: number | null
  review_count: number | null
  in_stock: boolean
  commission_rate: number
}

export interface Profile {
  id: string
  prism_project_id: string
  name: string
  marketplaces: string[]
  categories: string[]
  min_commission_rate: number
  max_products: number
  is_active: boolean
}

export interface Link {
  id: string
  product_id: string
  marketplace: string
  affiliate_url: string
  short_code: string
  prism_project_id: string | null
  created_at: string
}

export interface AnalyticsOverview {
  total_clicks: number
  total_conversions: number
  total_revenue: number
  total_commission: number
  period_days: number
}

export interface StatRow {
  dimension: string
  clicks: number
  conversions: number
  revenue: number
  commission: number
}
