'use client'
import { useEffect, useState, useCallback } from 'react'
import AuthGuard from '@/components/AuthGuard'
import { api, Product } from '@/lib/api'
import { Search, Filter, Star, Package, Send } from 'lucide-react'

const MKT_LABELS: Record<string,string> = {
  amazon:'Amazon', ebay:'eBay', rakuten:'Rakuten',
  cj_affiliate:'CJ Affiliate', awin:'Awin',
  admitad:'Admitad', gdeslon:'GdeSlon',
  aliexpress:'AliExpress', yandex_market:'Яндекс.Маркет',
}
const SORT_OPTIONS = [
  { value:'commission', label:'По комиссии' },
  { value:'rating', label:'По рейтингу' },
  { value:'price', label:'По цене' },
  { value:'newest', label:'Новые' },
]

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [pushing, setPushing] = useState(false)
  const [filters, setFilters] = useState({
    q: '', category: '', marketplace: '', min_commission: '',
    min_price: '', max_price: '', sort: 'commission',
  })

  async function search() {
    setLoading(true)
    const params: Record<string,string> = { sort: filters.sort, per_page: '24' }
    if (filters.q)             params.q = filters.q
    if (filters.category)      params.category = filters.category
    if (filters.marketplace)   params.marketplace = filters.marketplace
    if (filters.min_commission) params.min_commission = filters.min_commission
    if (filters.min_price)     params.min_price = filters.min_price
    if (filters.max_price)     params.max_price = filters.max_price
    const data = await api.products.search(params).catch(() => [])
    setProducts(data)
    setLoading(false)
  }

  useEffect(() => {
    api.products.categories().then(setCategories).catch(() => [])
    search()
  }, [])

  function fmtPrice(p: number, cur: string) {
    const sym: Record<string,string> = { RUB:'₽', USD:'$', EUR:'€' }
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
            {pushing ? 'Отправка...' : 'Отправить в PRISM'}
          </button>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
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
              onClick={search}
              className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5"
            >
              <Search size={14} /> Найти
            </button>
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
            <p className="text-xs text-slate-400">{products.length} товаров</p>
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
                    <div className="flex items-center gap-1.5 mb-2">
                      <span className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                        {MKT_LABELS[p.marketplace] ?? p.marketplace}
                      </span>
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
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </AuthGuard>
  )
}
