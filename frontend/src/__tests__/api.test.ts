import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock auth module before importing api
vi.mock('@/lib/auth', () => ({
  getToken: () => 'test-token-123',
}))

import { api } from '@/lib/api'

const CATALOG = 'http://localhost:8011'
const LINKS = 'http://localhost:8012'
const ANALYTICS = 'http://localhost:8014'

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn()
  global.fetch = fetchMock
})

afterEach(() => {
  vi.restoreAllMocks()
})

function mockFetchOk(data: unknown) {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  })
}

function mockFetchError(status: number, body: string) {
  fetchMock.mockResolvedValueOnce({
    ok: false,
    status,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(body),
  })
}

describe('api.products', () => {
  it('search() calls correct URL with params', async () => {
    const data = { items: [], total: 0, page: 1, pages: 0 }
    mockFetchOk(data)

    const result = await api.products.search({ q: 'phone', page: '1' })

    expect(result).toEqual(data)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toContain(`${CATALOG}/api/v1/products/`)
    expect(url).toContain('q=phone')
    expect(url).toContain('page=1')
  })

  it('get() calls correct URL', async () => {
    const product = { id: 'p1', title: 'Phone' }
    mockFetchOk(product)

    await api.products.get('p1')

    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toBe(`${CATALOG}/api/v1/products/p1`)
  })

  it('categories() calls correct URL', async () => {
    mockFetchOk(['Electronics', 'Clothing'])

    await api.products.categories()

    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toBe(`${CATALOG}/api/v1/products/categories`)
  })
})

describe('api.links', () => {
  it('list() calls correct URL without params', async () => {
    mockFetchOk([])

    await api.links.list()

    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toBe(`${LINKS}/api/v1/links/`)
  })

  it('list() calls correct URL with params', async () => {
    mockFetchOk([])

    await api.links.list({ product_id: 'p1' })

    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toContain(`${LINKS}/api/v1/links/`)
    expect(url).toContain('product_id=p1')
  })

  it('generate() POSTs with product_id', async () => {
    const link = { id: 'l1', affiliate_url: 'https://aff.example.com/l1' }
    mockFetchOk(link)

    await api.links.generate('prod-123')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(`${LINKS}/api/v1/links/generate`)
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ product_id: 'prod-123' })
  })

  it('generateBulk() POSTs with product_ids array', async () => {
    const result = { created: 2, failed: 0, links: [] }
    mockFetchOk(result)

    await api.links.generateBulk(['p1', 'p2'])

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(`${LINKS}/api/v1/links/generate-bulk`)
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ product_ids: ['p1', 'p2'] })
  })
})

describe('api.analytics', () => {
  it('overview() calls correct URL with default period', async () => {
    const data = { total_clicks: 100, total_conversions: 10, total_revenue: 1000, total_commission: 100, period_days: 30 }
    mockFetchOk(data)

    await api.analytics.overview()

    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toBe(`${ANALYTICS}/api/v1/analytics/overview?period=30`)
  })

  it('overview() calls with custom period', async () => {
    mockFetchOk({})

    await api.analytics.overview(7)

    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toContain('period=7')
  })

  it('byMarketplace() calls correct URL', async () => {
    mockFetchOk([])

    await api.analytics.byMarketplace(14)

    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toBe(`${ANALYTICS}/api/v1/analytics/by-marketplace?period=14`)
  })

  it('byProduct() calls correct URL', async () => {
    mockFetchOk([])

    await api.analytics.byProduct(7)

    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toBe(`${ANALYTICS}/api/v1/analytics/by-product?period=7`)
  })
})

describe('error handling', () => {
  it('throws on non-200 response', async () => {
    mockFetchError(401, 'Unauthorized')

    await expect(api.products.search({ q: 'test' })).rejects.toThrow('401: Unauthorized')
  })

  it('throws on 500 response', async () => {
    mockFetchError(500, 'Internal Server Error')

    await expect(api.links.list()).rejects.toThrow('500: Internal Server Error')
  })
})

describe('auth header', () => {
  it('includes Bearer token in requests', async () => {
    mockFetchOk([])

    await api.links.list()

    const init = fetchMock.mock.calls[0][1]
    expect(init.headers.Authorization).toBe('Bearer test-token-123')
  })

  it('includes Content-Type json header', async () => {
    mockFetchOk([])

    await api.links.list()

    const init = fetchMock.mock.calls[0][1]
    expect(init.headers['Content-Type']).toBe('application/json')
  })
})
