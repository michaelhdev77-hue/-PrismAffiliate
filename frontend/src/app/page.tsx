'use client'
import { useEffect, useState } from 'react'
import AuthGuard from '@/components/AuthGuard'
import MetricCard from '@/components/MetricCard'
import { api, AnalyticsOverview, Account, Feed, StatRow } from '@/lib/api'
import { TrendingUp, Store, RefreshCw, AlertCircle } from 'lucide-react'

const MARKETPLACE_LABELS: Record<string, string> = {
  admitad: 'Admitad', gdeslon: 'GdeSlon', amazon: 'Amazon',
  ebay: 'eBay', aliexpress: 'AliExpress', yandex_market: 'Яндекс.Маркет',
}

function fmt(n: number, currency = false) {
  if (currency) return `${n.toLocaleString('ru-RU', { maximumFractionDigits: 0 })} ₽`
  return n.toLocaleString('ru-RU')
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ok: 'bg-green-100 text-green-700',
    error: 'bg-red-100 text-red-700',
    unknown: 'bg-slate-100 text-slate-600',
    active: 'bg-green-100 text-green-700',
    syncing: 'bg-blue-100 text-blue-700',
    paused: 'bg-yellow-100 text-yellow-700',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${map[status] ?? 'bg-slate-100 text-slate-600'}`}>
      {status}
    </span>
  )
}

export default function DashboardPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null)
  const [accounts, setAccounts] = useState<Account[]>([])
  const [feeds, setFeeds]       = useState<Feed[]>([])
  const [byMkt, setByMkt]       = useState<StatRow[]>([])
  const [period, setPeriod]     = useState(30)
  const [loading, setLoading]   = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.analytics.overview(period).catch(() => null),
      api.accounts.list().catch(() => []),
      api.feeds.list().catch(() => []),
      api.analytics.byMarketplace(period).catch(() => []),
    ]).then(([ov, acc, fd, mkt]) => {
      setOverview(ov)
      setAccounts(acc)
      setFeeds(fd)
      setByMkt(mkt)
      setLoading(false)
    })
  }, [period])

  return (
    <AuthGuard>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Дашборд</h1>
            <p className="text-sm text-slate-500 mt-0.5">Обзор всех affiliate-активностей</p>
          </div>
          <div className="flex gap-2">
            {[7, 30, 90].map(d => (
              <button
                key={d}
                onClick={() => setPeriod(d)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  period === d
                    ? 'bg-brand-600 text-white'
                    : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                {d}д
              </button>
            ))}
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-4 gap-4">
          <MetricCard label="Кликов" value={loading ? '—' : fmt(overview?.total_clicks ?? 0)} color="violet" sub={`За ${period} дней`} />
          <MetricCard label="Конверсий" value={loading ? '—' : fmt(overview?.total_conversions ?? 0)} color="green" />
          <MetricCard label="Выручка" value={loading ? '—' : fmt(overview?.total_revenue ?? 0, true)} color="blue" />
          <MetricCard label="Комиссия" value={loading ? '—' : fmt(overview?.total_commission ?? 0, true)} color="orange" />
        </div>

        <div className="grid grid-cols-3 gap-6">
          {/* By Marketplace */}
          <div className="col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={16} className="text-brand-600" />
              <h2 className="font-semibold text-slate-900 text-sm">По площадкам</h2>
            </div>
            {byMkt.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-sm">
                Данных пока нет — подключите площадки и дождитесь кликов
              </div>
            ) : (
              <div className="space-y-3">
                {byMkt.map(row => {
                  const maxRev = Math.max(...byMkt.map(r => r.revenue), 1)
                  const pct = Math.max(4, (row.revenue / maxRev) * 100)
                  return (
                    <div key={row.dimension}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="font-medium text-slate-700">
                          {MARKETPLACE_LABELS[row.dimension] ?? row.dimension}
                        </span>
                        <span className="text-slate-500 text-xs">{fmt(row.revenue, true)}</span>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-brand-500 rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                      <div className="flex gap-3 mt-1 text-xs text-slate-400">
                        <span>{fmt(row.clicks)} кл.</span>
                        <span>{fmt(row.conversions)} конв.</span>
                        <span className="text-green-600">{fmt(row.commission, true)} ком.</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Right column */}
          <div className="space-y-4">
            {/* Accounts */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-3">
                <Store size={15} className="text-brand-600" />
                <h2 className="font-semibold text-slate-900 text-sm">Площадки</h2>
                <span className="ml-auto text-xs text-slate-400">{accounts.length} шт.</span>
              </div>
              {accounts.length === 0 ? (
                <p className="text-xs text-slate-400">Нет подключённых площадок</p>
              ) : (
                <div className="space-y-2">
                  {accounts.slice(0, 4).map(a => (
                    <div key={a.id} className="flex items-center justify-between">
                      <div>
                        <p className="text-xs font-medium text-slate-700">{a.display_name}</p>
                        <p className="text-xs text-slate-400">{MARKETPLACE_LABELS[a.marketplace] ?? a.marketplace}</p>
                      </div>
                      <StatusBadge status={a.health_status} />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Feeds */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-3">
                <RefreshCw size={15} className="text-brand-600" />
                <h2 className="font-semibold text-slate-900 text-sm">Фиды</h2>
                <span className="ml-auto text-xs text-slate-400">{feeds.length} шт.</span>
              </div>
              {feeds.length === 0 ? (
                <p className="text-xs text-slate-400">Нет фидов</p>
              ) : (
                <div className="space-y-2">
                  {feeds.slice(0, 4).map(f => (
                    <div key={f.id} className="flex items-center justify-between">
                      <div>
                        <p className="text-xs font-medium text-slate-700">{f.name}</p>
                        <p className="text-xs text-slate-400">{f.last_sync_products.toLocaleString('ru-RU')} товаров</p>
                      </div>
                      <StatusBadge status={f.status} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AuthGuard>
  )
}
