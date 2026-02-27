'use client'
import { useEffect, useState } from 'react'
import AuthGuard from '@/components/AuthGuard'
import MetricCard from '@/components/MetricCard'
import { api, AnalyticsOverview, StatRow } from '@/lib/api'
import { BarChart3 } from 'lucide-react'

const MKT: Record<string,string> = {
  admitad:'Admitad', gdeslon:'GdeSlon', amazon:'Amazon',
  ebay:'eBay', aliexpress:'AliExpress', yandex_market:'Яндекс.Маркет',
}

function fmt(n: number, currency = false) {
  if (currency) return `${n.toLocaleString('ru-RU', {maximumFractionDigits:0})} ₽`
  return n.toLocaleString('ru-RU')
}

function Bar({ rows, field, label }: { rows: StatRow[], field: keyof StatRow, label: string }) {
  if (rows.length === 0) return <p className="text-slate-400 text-sm text-center py-8">Нет данных</p>
  const max = Math.max(...rows.map(r => r[field] as number), 1)
  return (
    <div className="space-y-3">
      {rows.map(r => {
        const val = r[field] as number
        const pct = Math.max(3, (val / max) * 100)
        const isCurrency = field === 'revenue' || field === 'commission'
        return (
          <div key={r.dimension}>
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium text-slate-700">{MKT[r.dimension] ?? r.dimension}</span>
              <span className="text-slate-500 text-xs">{isCurrency ? fmt(val, true) : fmt(val)}</span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full bg-brand-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<AnalyticsOverview|null>(null)
  const [byMkt, setByMkt]       = useState<StatRow[]>([])
  const [byProd, setByProd]     = useState<StatRow[]>([])
  const [period, setPeriod]     = useState(30)
  const [tab, setTab]           = useState<'marketplace'|'product'>('marketplace')
  const [loading, setLoading]   = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.analytics.overview(period).catch(() => null),
      api.analytics.byMarketplace(period).catch(() => []),
      api.analytics.byProduct(period).catch(() => []),
    ]).then(([ov, mkt, prod]) => {
      setOverview(ov); setByMkt(mkt); setByProd(prod)
      setLoading(false)
    })
  }, [period])

  return (
    <AuthGuard>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Аналитика</h1>
            <p className="text-sm text-slate-500 mt-0.5">Клики, конверсии и выручка</p>
          </div>
          <div className="flex gap-2">
            {[7,30,90].map(d => (
              <button
                key={d}
                onClick={() => setPeriod(d)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  period === d ? 'bg-brand-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >{d}д</button>
            ))}
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-4 gap-4">
          <MetricCard label="Кликов"     value={loading?'—':fmt(overview?.total_clicks??0)}     color="violet" />
          <MetricCard label="Конверсий"  value={loading?'—':fmt(overview?.total_conversions??0)} color="green" />
          <MetricCard label="Выручка"    value={loading?'—':fmt(overview?.total_revenue??0,true)} color="blue" />
          <MetricCard label="Комиссия"   value={loading?'—':fmt(overview?.total_commission??0,true)} color="orange" />
        </div>

        {/* Conversion rate */}
        {overview && overview.total_clicks > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Конверсия</p>
            <div className="flex items-end gap-4">
              <p className="text-3xl font-bold text-brand-600">
                {((overview.total_conversions / overview.total_clicks) * 100).toFixed(2)}%
              </p>
              <p className="text-sm text-slate-400 mb-1">
                {fmt(overview.total_conversions)} конверсий из {fmt(overview.total_clicks)} кликов
              </p>
            </div>
          </div>
        )}

        {/* Charts */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <div className="flex items-center gap-2 mb-5">
            <BarChart3 size={16} className="text-brand-600" />
            <h2 className="font-semibold text-slate-900 text-sm">Детализация</h2>
            <div className="ml-auto flex gap-1">
              {['marketplace','product'].map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t as any)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    tab === t ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {t === 'marketplace' ? 'По площадкам' : 'По товарам'}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8">
            {(['clicks','revenue'] as const).map(field => (
              <div key={field}>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-3">
                  {field === 'clicks' ? 'Клики' : 'Выручка'}
                </p>
                <Bar
                  rows={tab === 'marketplace' ? byMkt : byProd}
                  field={field}
                  label={field === 'clicks' ? 'Клики' : 'Выручка'}
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </AuthGuard>
  )
}
