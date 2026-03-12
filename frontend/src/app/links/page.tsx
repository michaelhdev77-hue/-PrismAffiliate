'use client'
import { useEffect, useState, useCallback } from 'react'
import AuthGuard from '@/components/AuthGuard'
import { api, Link as AffLink, Product } from '@/lib/api'
import { Link2, Copy, CheckCheck, ExternalLink, Image as ImageIcon, ChevronLeft, ChevronRight } from 'lucide-react'

const TRACKER_BASE = typeof window !== 'undefined'
  ? window.location.origin.replace('3001', '8013')
  : 'http://localhost:8013'

const PER_PAGE = 20

const MKT: Record<string, string> = {
  amazon: 'Amazon', ebay: 'eBay', rakuten: 'Rakuten',
  cj_affiliate: 'CJ Affiliate', awin: 'Awin',
  admitad: 'Admitad', gdeslon: 'GdeSlon', aliexpress: 'AliExpress',
}

export default function LinksPage() {
  const [links, setLinks] = useState<AffLink[]>([])
  const [products, setProducts] = useState<Record<string, Product>>({})
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)

  const load = useCallback(async (p: number) => {
    setLoading(true)
    try {
      const data = await api.links.list({ page: String(p), per_page: String(PER_PAGE) })
      setLinks(data)
      setPage(p)
      setHasMore(data.length === PER_PAGE)

      // Fetch product details for unique product_ids
      const ids = [...new Set(data.map(l => l.product_id))]
      const results = await Promise.allSettled(ids.map(id => api.products.get(id)))
      const map: Record<string, Product> = {}
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') map[ids[i]] = r.value
      })
      setProducts(prev => ({ ...prev, ...map }))
    } catch {
      setLinks([])
    }
    setLoading(false)
  }, [])

  useEffect(() => { load(1) }, [load])

  function copy(text: string, code: string) {
    navigator.clipboard.writeText(text)
    setCopied(code)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <AuthGuard>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Ссылки</h1>
          <p className="text-sm text-slate-500 mt-0.5">Сгенерированные реферальные ссылки</p>
        </div>

        {loading && links.length === 0 ? (
          <div className="text-center py-12 text-slate-400 text-sm">Загрузка...</div>
        ) : links.length === 0 ? (
          <div className="text-center py-16">
            <Link2 size={36} className="mx-auto text-slate-200 mb-3" />
            <p className="text-slate-400 text-sm">Нет сгенерированных ссылок</p>
            <p className="text-slate-300 text-xs mt-1">Создайте ссылку на странице «Товары» или через профили подбора</p>
          </div>
        ) : (
          <>
            <p className="text-xs text-slate-400">Страница {page}</p>
            <div className="space-y-3">
              {links.map(l => {
                const product = products[l.product_id]
                const trackerUrl = `${TRACKER_BASE}/r/${l.short_code}`
                return (
                  <div key={l.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex items-center gap-4">
                    {/* Product image */}
                    <div className="w-16 h-16 rounded-lg bg-slate-100 flex-shrink-0 overflow-hidden">
                      {product?.image_url ? (
                        <img src={product.image_url} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <ImageIcon size={20} className="text-slate-300" />
                        </div>
                      )}
                    </div>

                    {/* Product info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-medium text-slate-900 truncate">
                          {product?.title || l.product_id.slice(0, 12) + '...'}
                        </h3>
                        <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs flex-shrink-0">
                          {MKT[l.marketplace] ?? l.marketplace}
                        </span>
                        {(() => {
                          const expired = l.expires_at && new Date(l.expires_at) < new Date()
                          if (!l.is_active || expired) {
                            return <span className="bg-red-50 text-red-600 px-1.5 py-0.5 rounded text-xs flex-shrink-0">
                              {expired ? 'Истекла' : 'Неактивна'}
                            </span>
                          }
                          return <span className="bg-green-50 text-green-600 px-1.5 py-0.5 rounded text-xs flex-shrink-0">Активна</span>
                        })()}
                      </div>

                      {/* Tracker URL */}
                      <div className="flex items-center gap-2 mb-1">
                        <code className="text-xs bg-brand-50 text-brand-700 px-2 py-0.5 rounded font-mono truncate">
                          {trackerUrl}
                        </code>
                        <button
                          onClick={() => copy(trackerUrl, l.short_code)}
                          className="text-slate-400 hover:text-brand-600 transition-colors flex-shrink-0"
                          title="Скопировать ссылку"
                        >
                          {copied === l.short_code ? <CheckCheck size={13} className="text-green-500" /> : <Copy size={13} />}
                        </button>
                        <a
                          href={trackerUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-slate-400 hover:text-brand-600 transition-colors flex-shrink-0"
                          title="Открыть ссылку"
                        >
                          <ExternalLink size={13} />
                        </a>
                      </div>

                      {/* Meta info */}
                      <div className="flex items-center gap-4 text-xs text-slate-400">
                        {product?.price != null && (
                          <span>{product.price.toLocaleString('ru-RU')} {product.currency}</span>
                        )}
                        {product?.commission_rate != null && product.commission_rate > 0 && (
                          <span className="text-green-600">{product.commission_rate}% комиссия</span>
                        )}
                        <span>{new Date(l.created_at).toLocaleDateString('ru-RU')}</span>
                        {l.prism_project_id && (
                          <span className="text-slate-300">PRISM: {l.prism_project_id.slice(0, 8)}...</span>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Pagination */}
            {(page > 1 || hasMore) && (
              <div className="flex items-center justify-center gap-3 pt-2">
                <button
                  onClick={() => load(page - 1)}
                  disabled={page <= 1 || loading}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft size={14} /> Назад
                </button>
                <span className="text-sm text-slate-500">Стр. {page}</span>
                <button
                  onClick={() => load(page + 1)}
                  disabled={!hasMore || loading}
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
