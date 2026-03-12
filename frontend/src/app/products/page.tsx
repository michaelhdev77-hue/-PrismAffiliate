'use client'
import { useEffect, useState } from 'react'
import AuthGuard from '@/components/AuthGuard'
import { api, Product, Campaign } from '@/lib/api'
import { Search, Star, Package, Send, ChevronLeft, ChevronRight, Image, Link2, CheckCheck, ExternalLink } from 'lucide-react'

const MKT_LABELS: Record<string,string> = {
  amazon:'Amazon', ebay:'eBay', rakuten:'Rakuten',
  cj_affiliate:'CJ Affiliate', awin:'Awin',
  admitad:'Admitad', gdeslon:'GdeSlon',
  aliexpress:'AliExpress', yandex_market:'Яндекс.Маркет',
}
const SORT_OPTIONS = [
  { value:'score', label:'По скорингу' },
  { value:'commission', label:'По комиссии' },
  { value:'rating', label:'По рейтингу' },
  { value:'price', label:'По цене' },
  { value:'newest', label:'Новые' },
]

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(false)
  const [pushing, setPushing] = useState(false)
  const [generating, setGenerating] = useState<string|null>(null)
  const [generatedLinks, setGeneratedLinks] = useState<Record<string, string>>({})
  const [bulkGenerating, setBulkGenerating] = useState(false)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    q: '', category: '', marketplace: '', campaign_id: '',
    min_commission: '', min_price: '', max_price: '',
    sort: 'score', has_image: true,
  })

  const campaignMap = Object.fromEntries(campaigns.map(c => [c.external_campaign_id, c.name]))

  async function search(p = 1) {
    setLoading(true)
    const params: Record<string,string> = { sort: filters.sort, per_page: '24', page: String(p) }
    if (filters.q)              params.q = filters.q
    if (filters.category)       params.category = filters.category
    if (filters.marketplace)    params.marketplace = filters.marketplace
    if (filters.campaign_id)    params.campaign_id = filters.campaign_id
    if (filters.min_commission) params.min_commission = filters.min_commission
    if (filters.min_price)      params.min_price = filters.min_price
    if (filters.max_price)      params.max_price = filters.max_price
    if (filters.has_image)      params.has_image = 'true'
    const data = await api.products.search(params).catch(() => ({ items: [], total: 0, page: 1, pages: 1 }))
    setProducts(data.items)
    setTotal(data.total)
    setPage(data.page)
    setTotalPages(data.pages)
    setLoading(false)
  }

  useEffect(() => {
    api.products.categories().then(setCategories).catch(() => [])
    api.campaigns.list().then(setCampaigns).catch(() => [])
    search()
  }, [])

  function fmtPrice(p: number, cur: string) {
    const sym: Record<string,string> = { RUB:'₽', USD:'$', EUR:'€', BRL:'R$' }
    return `${p.toLocaleString('ru-RU', {maximumFractionDigits:0})} ${sym[cur]??cur}`
  }

  return (
    <AuthGuard>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Товары</h1>
            <p className="text-sm text-slate-500 mt-0.5">Поиск по локальному индексу товаров</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={async () => {
                const ids = products.filter(p => !generatedLinks[p.id]).map(p => p.id)
                if (!ids.length) { alert('Ссылки уже созданы для всех товаров на странице'); return }
                setBulkGenerating(true)
                try {
                  const result = await api.links.generateBulk(ids)
                  const newLinks: Record<string, string> = {}
                  result.links.forEach(l => { newLinks[l.product_id] = l.short_code })
                  setGeneratedLinks(prev => ({ ...prev, ...newLinks }))
                  alert(`Создано: ${result.created}, пропущено (уже есть): ${ids.length - result.created - result.failed}, ошибок: ${result.failed}`)
                } catch (e: any) {
                  alert(`Ошибка: ${e.message}`)
                }
                setBulkGenerating(false)
              }}
              disabled={bulkGenerating || products.length === 0}
              className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              <Link2 size={14} />
              {bulkGenerating ? 'Создание...' : `Ссылки для всех (${products.length})`}
            </button>
            <button
              onClick={async () => {
                setPushing(true)
                await api.bridge.pushToPrism().catch(() => null)
                setPushing(false)
                alert('Задача поставлена в очередь')
              }}
              disabled={pushing}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              <Send size={14} />
              {pushing ? 'Отправка...' : 'В PRISM'}
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
          <div className="flex gap-3 flex-wrap">
            <div className="flex-1 min-w-[200px] relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={filters.q}
                onChange={e => setFilters(f=>({...f, q: e.target.value}))}
                onKeyDown={e => e.key === 'Enter' && search()}
                placeholder="Поиск по названию..."
                className="w-full border border-slate-200 rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <select
              value={filters.campaign_id}
              onChange={e => setFilters(f=>({...f, campaign_id: e.target.value}))}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">Все магазины</option>
              {campaigns.map(c => <option key={c.id} value={c.external_campaign_id}>{c.name}</option>)}
            </select>
            <select
              value={filters.category}
              onChange={e => setFilters(f=>({...f, category: e.target.value}))}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">Все категории</option>
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <select
              value={filters.marketplace}
              onChange={e => setFilters(f=>({...f, marketplace: e.target.value}))}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">Все площадки</option>
              {Object.entries(MKT_LABELS).map(([k,v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input
              value={filters.min_commission}
              onChange={e => setFilters(f=>({...f, min_commission: e.target.value}))}
              placeholder="Мин. комиссия %"
              className="w-36 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <select
              value={filters.sort}
              onChange={e => setFilters(f=>({...f, sort: e.target.value}))}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <button
              onClick={() => search()}
              className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5"
            >
              <Search size={14} /> Найти
            </button>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={filters.has_image}
                onChange={e => setFilters(f=>({...f, has_image: e.target.checked}))}
                className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              />
              <Image size={14} className="text-slate-400" />
              Только с картинкой
            </label>
          </div>
        </div>

        {/* Results */}
        {loading ? (
          <div className="text-center py-20 text-slate-400">Поиск...</div>
        ) : products.length === 0 ? (
          <div className="text-center py-20">
            <Package size={40} className="mx-auto text-slate-200 mb-3" />
            <p className="text-slate-400 text-sm">Товаров не найдено</p>
            <p className="text-slate-300 text-xs mt-1">Добавьте фид и запустите синхронизацию</p>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-400">
                {total.toLocaleString('ru-RU')} товаров &middot; стр. {page} из {totalPages}
              </p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              {products.map(p => (
                <div key={p.id} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow">
                  {/* Image */}
                  <div className="h-40 bg-slate-100 flex items-center justify-center overflow-hidden">
                    {p.image_url ? (
                      <img src={p.image_url} alt={p.title} className="w-full h-full object-contain p-2" />
                    ) : (
                      <Package size={32} className="text-slate-200" />
                    )}
                  </div>
                  <div className="p-4">
                    {/* Badges */}
                    <div className="flex items-center gap-1.5 mb-2 flex-wrap">
                      <span className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                        {MKT_LABELS[p.marketplace] ?? p.marketplace}
                      </span>
                      {p.campaign_id && campaignMap[p.campaign_id] && (
                        <span className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
                          {campaignMap[p.campaign_id]}
                        </span>
                      )}
                      {p.commission_rate > 0 && (
                        <span className="text-xs bg-green-50 text-green-700 px-1.5 py-0.5 rounded font-medium">
                          {p.commission_rate}%
                        </span>
                      )}
                      {!p.in_stock && (
                        <span className="text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded">нет</span>
                      )}
                    </div>
                    <p className="text-sm font-medium text-slate-900 line-clamp-2 mb-2">{p.title}</p>
                    <div className="flex items-end justify-between">
                      <div>
                        <p className="text-base font-bold text-slate-900">{fmtPrice(p.price, p.currency)}</p>
                        {p.original_price && p.original_price > p.price && (
                          <p className="text-xs text-slate-400 line-through">{fmtPrice(p.original_price, p.currency)}</p>
                        )}
                      </div>
                      {p.rating && (
                        <div className="flex items-center gap-1 text-xs text-amber-500">
                          <Star size={11} fill="currentColor" />
                          <span>{p.rating.toFixed(1)}</span>
                          {p.review_count && <span className="text-slate-400">({p.review_count})</span>}
                        </div>
                      )}
                    </div>
                    {p.category && (
                      <p className="text-xs text-slate-400 mt-1 truncate">{p.category}</p>
                    )}
                    {/* Generate link / show result */}
                    <div className="mt-3 pt-3 border-t border-slate-100">
                      {generatedLinks[p.id] ? (
                        <div className="flex items-center gap-1.5">
                          <CheckCheck size={12} className="text-green-500 shrink-0" />
                          <code className="text-xs bg-green-50 text-green-700 px-1.5 py-0.5 rounded truncate flex-1">
                            /r/{generatedLinks[p.id]}
                          </code>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(
                                `${window.location.origin.replace('3001','8013')}/r/${generatedLinks[p.id]}`
                              )
                            }}
                            className="text-slate-400 hover:text-brand-600 transition-colors shrink-0"
                            title="Скопировать"
                          >
                            <Link2 size={12} />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={async () => {
                              setGenerating(p.id)
                              try {
                                const link = await api.links.generate(p.id)
                                setGeneratedLinks(prev => ({ ...prev, [p.id]: link.short_code }))
                              } catch (e: any) {
                                alert(`Ошибка: ${e.message}`)
                              }
                              setGenerating(null)
                            }}
                            disabled={generating === p.id}
                            className="flex-1 flex items-center justify-center gap-1.5 bg-brand-50 hover:bg-brand-100 text-brand-700 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                          >
                            <Link2 size={12} />
                            {generating === p.id ? 'Создание...' : 'Создать ссылку'}
                          </button>
                          <a
                            href={p.product_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-slate-400 hover:text-slate-600 transition-colors"
                            title="Открыть на сайте"
                          >
                            <ExternalLink size={14} />
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-2">
                <button
                  onClick={() => search(page - 1)}
                  disabled={page <= 1}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft size={14} /> Назад
                </button>
                <div className="flex items-center gap-1">
                  {generatePageNumbers(page, totalPages).map((p, i) =>
                    p === '...' ? (
                      <span key={`dots-${i}`} className="px-2 text-slate-300 text-sm">...</span>
                    ) : (
                      <button
                        key={p}
                        onClick={() => search(p as number)}
                        className={`w-8 h-8 rounded-lg text-sm transition-colors ${
                          p === page
                            ? 'bg-brand-600 text-white'
                            : 'hover:bg-slate-100 text-slate-600'
                        }`}
                      >
                        {p}
                      </button>
                    )
                  )}
                </div>
                <button
                  onClick={() => search(page + 1)}
                  disabled={page >= totalPages}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Вперёд <ChevronRight size={14} />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </AuthGuard>
  )
}

function generatePageNumbers(current: number, total: number): (number | string)[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages: (number | string)[] = [1]
  if (current > 3) pages.push('...')
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
    pages.push(i)
  }
  if (current < total - 2) pages.push('...')
  pages.push(total)
  return pages
}
