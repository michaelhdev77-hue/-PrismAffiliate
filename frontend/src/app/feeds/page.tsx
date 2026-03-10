'use client'
import { useEffect, useState } from 'react'
import AuthGuard from '@/components/AuthGuard'
import { api, Feed, Account, Campaign } from '@/lib/api'
import { Plus, RefreshCw, Trash2, Play, X, Radar } from 'lucide-react'

const FORMAT_LABELS: Record<string,string> = { yml:'YML', xml:'XML', csv:'CSV', json:'JSON', api:'API' }
const STATUS_COLORS: Record<string,string> = {
  active:'bg-green-100 text-green-700',
  syncing:'bg-blue-100 text-blue-700',
  paused:'bg-yellow-100 text-yellow-700',
  error:'bg-red-100 text-red-700',
}

export default function FeedsPage() {
  const [feeds, setFeeds]       = useState<Feed[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading]   = useState(true)
  const [syncing, setSyncing]   = useState<string|null>(null)
  const [modal, setModal]       = useState(false)
  const [discoverModal, setDiscoverModal] = useState(false)
  const [discovering, setDiscovering] = useState(false)
  const [discoveredFeeds, setDiscoveredFeeds] = useState<Array<{name: string, xml_link: string, csv_link: string, campaign_name: string, campaign_id: string, account_id: string, account_name: string}>>([])
  const [selectedDiscovered, setSelectedDiscovered] = useState<Set<string>>(new Set())
  const [addingFeeds, setAddingFeeds] = useState(false)
  const [form, setForm]         = useState({
    marketplace_account_id: '', campaign_id: '', name: '', feed_format: 'yml',
    feed_url: '', schedule_cron: '0 */6 * * *',
  })

  async function load() {
    setLoading(true)
    const [f, a, c] = await Promise.all([api.feeds.list().catch(()=>[]), api.accounts.list().catch(()=>[]), api.campaigns.list().catch(()=>[])])
    setFeeds(f); setAccounts(a); setCampaigns(c)
    setLoading(false)
  }
  useEffect(() => { load() }, [])

  async function sync(id: string) {
    setSyncing(id)
    await api.feeds.sync(id).catch(()=>null)
    await load()
    setSyncing(null)
  }

  async function create() {
    if (!form.marketplace_account_id || !form.name) return
    await api.feeds.create({
      marketplace_account_id: form.marketplace_account_id,
      campaign_id: form.campaign_id || null,
      name: form.name,
      feed_format: form.feed_format,
      feed_url: form.feed_url || null,
      schedule_cron: form.schedule_cron,
      category_mapping: {}, niche_mapping: {},
    })
    setModal(false); load()
  }

  async function discoverAllFeeds() {
    setDiscoverModal(true)
    setDiscovering(true)
    setDiscoveredFeeds([])
    setSelectedDiscovered(new Set())

    const allFeeds: typeof discoveredFeeds = []
    const existingUrls = new Set(feeds.map(f => f.feed_url).filter(Boolean))

    await Promise.all(accounts.map(async (a) => {
      try {
        const res = await api.feeds.autoDiscover(a.id)
        for (const df of res) {
          const url = df.xml_link || df.csv_link
          if (url && !existingUrls.has(url)) {
            allFeeds.push({ ...df, account_id: a.id, account_name: a.display_name })
          }
        }
      } catch { /* skip accounts without feed support */ }
    }))

    setDiscoveredFeeds(allFeeds)
    if (allFeeds.length > 0) {
      setSelectedDiscovered(new Set(allFeeds.map(df => df.xml_link || df.csv_link)))
    }
    setDiscovering(false)
  }

  async function addSelectedFeeds() {
    setAddingFeeds(true)
    for (const df of discoveredFeeds.filter(d => selectedDiscovered.has(d.xml_link || d.csv_link))) {
      await api.feeds.create({
        marketplace_account_id: df.account_id,
        campaign_id: df.campaign_id || null,
        name: df.name,
        feed_format: 'xml',
        feed_url: df.xml_link || df.csv_link,
        schedule_cron: '0 */6 * * *',
        category_mapping: {},
        niche_mapping: {},
      }).catch(() => null)
    }
    setAddingFeeds(false)
    setDiscoverModal(false)
    load()
  }

  function toggleDiscoveredFeed(url: string) {
    setSelectedDiscovered(prev => {
      const next = new Set(prev)
      if (next.has(url)) next.delete(url); else next.add(url)
      return next
    })
  }

  function accountName(id: string) {
    return accounts.find(a => a.id === id)?.display_name ?? id.slice(0,8)
  }

  return (
    <AuthGuard>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Фиды товаров</h1>
            <p className="text-sm text-slate-500 mt-0.5">Источники товарных данных для индексации</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={discoverAllFeeds}
              className="flex items-center gap-2 border border-brand-200 text-brand-700 hover:bg-brand-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              <Radar size={15} /> Авто-поиск
            </button>
            <button
              onClick={() => setModal(true)}
              className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              <Plus size={15} /> Добавить фид
            </button>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="text-center py-12 text-slate-400 text-sm">Загрузка...</div>
          ) : feeds.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-slate-400 text-sm">Нет фидов</p>
              <p className="text-slate-300 text-xs mt-1">Добавьте YML/XML фид чтобы начать индексацию товаров</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {['Название','Площадка','Формат','Статус','Товаров','Синхр.',''].map(h => (
                    <th key={h} className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {feeds.map(f => (
                  <tr key={f.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-slate-900">{f.name}</td>
                    <td className="px-5 py-3.5 text-xs text-slate-500">{accountName(f.marketplace_account_id)}</td>
                    <td className="px-5 py-3.5">
                      <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs">{FORMAT_LABELS[f.feed_format] ?? f.feed_format}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[f.status] ?? 'bg-slate-100 text-slate-600'}`}>
                        {f.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-700 font-medium">{f.last_sync_products.toLocaleString('ru-RU')}</td>
                    <td className="px-5 py-3.5 text-xs text-slate-400">
                      {f.last_sync_at ? new Date(f.last_sync_at).toLocaleString('ru-RU') : '—'}
                      {f.last_error && <p className="text-red-400 truncate max-w-[160px]" title={f.last_error}>{f.last_error}</p>}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => sync(f.id)}
                          disabled={syncing === f.id}
                          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-brand-600 transition-colors disabled:opacity-50"
                        >
                          {syncing === f.id
                            ? <RefreshCw size={12} className="animate-spin" />
                            : <Play size={12} />
                          }
                          Синхр.
                        </button>
                        <button
                          onClick={async () => {
                            if (!confirm('Удалить фид?')) return
                            await api.feeds.delete(f.id)
                            load()
                          }}
                          className="text-slate-300 hover:text-red-500 transition-colors"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="p-6 border-b border-slate-100">
              <h2 className="font-semibold text-slate-900">Добавить фид</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Площадка</label>
                <select
                  value={form.marketplace_account_id}
                  onChange={e => setForm(f=>({...f, marketplace_account_id: e.target.value}))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <option value="">Выберите площадку...</option>
                  {accounts.map(a => <option key={a.id} value={a.id}>{a.display_name}</option>)}
                </select>
              </div>
              {form.marketplace_account_id && campaigns.filter(c => c.marketplace_account_id === form.marketplace_account_id).length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">Программа (кампания)</label>
                  <select
                    value={form.campaign_id}
                    onChange={e => setForm(f=>({...f, campaign_id: e.target.value}))}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    <option value="">Без привязки к программе</option>
                    {campaigns.filter(c => c.marketplace_account_id === form.marketplace_account_id).map(c =>
                      <option key={c.id} value={c.id}>{c.name} (ID: {c.external_campaign_id})</option>
                    )}
                  </select>
                </div>
              )}
              {[
                { label:'Название', key:'name', placeholder:'Admitad Electronics Feed' },
                { label:'URL фида', key:'feed_url', placeholder:'https://feeds.admitad.com/...' },
                { label:'Расписание (cron)', key:'schedule_cron', placeholder:'0 */6 * * *' },
              ].map(({ label, key, placeholder }) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">{label}</label>
                  <input
                    value={(form as any)[key]}
                    onChange={e => setForm(f=>({...f,[key]:e.target.value}))}
                    placeholder={placeholder}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Формат</label>
                <select
                  value={form.feed_format}
                  onChange={e => setForm(f=>({...f, feed_format: e.target.value}))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  {Object.entries(FORMAT_LABELS).map(([k,v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
            </div>
            <div className="p-6 border-t border-slate-100 flex gap-3">
              <button onClick={() => setModal(false)} className="flex-1 border border-slate-200 rounded-lg py-2 text-sm text-slate-600 hover:bg-slate-50">Отмена</button>
              <button onClick={create} className="flex-1 bg-brand-600 hover:bg-brand-700 text-white rounded-lg py-2 text-sm font-medium transition-colors">Добавить</button>
            </div>
          </div>
        </div>
      )}
      {discoverModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h2 className="font-semibold text-slate-900">Авто-поиск фидов</h2>
                <p className="text-xs text-slate-400 mt-1">Сканирование всех подключённых площадок</p>
              </div>
              <button onClick={() => setDiscoverModal(false)} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {discovering ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw size={20} className="animate-spin text-slate-400" />
                  <span className="ml-2 text-sm text-slate-400">Сканирование площадок...</span>
                </div>
              ) : discoveredFeeds.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-8">Нет доступных фидов для импорта (все уже добавлены или площадки не поддерживают фиды)</p>
              ) : (
                <div className="space-y-1">
                  <label className="flex items-center gap-2 px-3 py-2 text-xs text-slate-500 cursor-pointer hover:bg-slate-50 rounded-lg">
                    <input
                      type="checkbox"
                      checked={selectedDiscovered.size === discoveredFeeds.length}
                      onChange={() => {
                        if (selectedDiscovered.size === discoveredFeeds.length) {
                          setSelectedDiscovered(new Set())
                        } else {
                          setSelectedDiscovered(new Set(discoveredFeeds.map(d => d.xml_link || d.csv_link)))
                        }
                      }}
                      className="rounded border-slate-300"
                    />
                    Выбрать все ({discoveredFeeds.length})
                  </label>
                  {discoveredFeeds.map((df, i) => {
                    const url = df.xml_link || df.csv_link
                    return (
                      <label
                        key={i}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-colors ${
                          selectedDiscovered.has(url) ? 'border-brand-300 bg-brand-50' : 'border-slate-200 hover:bg-slate-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedDiscovered.has(url)}
                          onChange={() => toggleDiscoveredFeed(url)}
                          className="rounded border-slate-300"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-slate-900 truncate">{df.name}</div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs text-slate-400">{df.campaign_name}</span>
                            <span className="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">{df.account_name}</span>
                          </div>
                        </div>
                      </label>
                    )
                  })}
                </div>
              )}
            </div>
            <div className="p-6 border-t border-slate-100 flex gap-3">
              <button onClick={() => setDiscoverModal(false)} className="flex-1 border border-slate-200 rounded-lg py-2 text-sm text-slate-600 hover:bg-slate-50">Отмена</button>
              <button
                onClick={addSelectedFeeds}
                disabled={selectedDiscovered.size === 0 || addingFeeds}
                className="flex-1 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors"
              >
                {addingFeeds ? 'Добавление...' : `Добавить (${selectedDiscovered.size})`}
              </button>
            </div>
          </div>
        </div>
      )}
    </AuthGuard>
  )
}
