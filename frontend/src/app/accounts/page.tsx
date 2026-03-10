'use client'
import { useEffect, useState } from 'react'
import AuthGuard from '@/components/AuthGuard'
import { api, Account, Campaign, DiscoveredProgram } from '@/lib/api'
import { Plus, RefreshCw, Trash2, CheckCircle, XCircle, Clock, ChevronDown, ChevronRight, Download } from 'lucide-react'

const MKT_OPTIONS = [
  'admitad','gdeslon','yandex_market',
  'amazon','ebay','rakuten','cj_affiliate','awin','walmart',
]

const LABELS: Record<string,string> = {
  amazon:'Amazon', ebay:'eBay', rakuten:'Rakuten',
  cj_affiliate:'CJ Affiliate', awin:'Awin',
  admitad:'Admitad', gdeslon:'GdeSlon',
  aliexpress:'AliExpress', yandex_market:'Яндекс.Маркет', walmart:'Walmart',
}

// Marketplace types that support multiple campaigns (affiliate networks)
const NETWORK_TYPES = ['admitad', 'gdeslon', 'cj_affiliate', 'awin']

function HealthIcon({ status }: { status: string }) {
  if (status === 'ok')      return <CheckCircle size={14} className="text-green-500" />
  if (status === 'error')   return <XCircle size={14} className="text-red-500" />
  return <Clock size={14} className="text-slate-400" />
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading]   = useState(true)
  const [modal, setModal]       = useState(false)
  const [campaignModal, setCampaignModal] = useState<string | null>(null)
  const [checking, setChecking] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)

  const [form, setForm] = useState({
    marketplace: 'admitad', display_name: '',
    // Amazon
    credential_id: '', credential_secret: '', partner_tag: '',
    // Admitad
    client_id: '', client_secret: '', website_id: '',
    // GdeSlon / generic API key
    api_key: '', affiliate_id: '',
    // AliExpress
    app_key: '', tracking_id: '',
    // eBay
    ebay_client_id: '', ebay_client_secret: '', ebay_campaign_id: '', marketplace_id: 'EBAY_US',
    // CJ Affiliate
    personal_access_token: '', cj_website_id: '', company_id: '',
    // Awin
    awin_api_token: '', publisher_id: '', datafeed_api_key: '',
    // Rakuten
    rakuten_username: '', rakuten_password: '', sid: '', rakuten_publisher_id: '',
  })

  const [campaignForm, setCampaignForm] = useState({
    name: '', external_campaign_id: '', marketplace_label: '',
  })

  const [discoverModal, setDiscoverModal] = useState<string | null>(null)
  const [discoveredPrograms, setDiscoveredPrograms] = useState<DiscoveredProgram[]>([])
  const [discovering, setDiscovering] = useState(false)
  const [selectedPrograms, setSelectedPrograms] = useState<Set<string>>(new Set())
  const [importing, setImporting] = useState(false)

  function buildCredentials() {
    const m = form.marketplace
    if (m === 'admitad')     return { client_id: form.client_id, client_secret: form.client_secret, website_id: Number(form.website_id) }
    if (m === 'gdeslon')     return { api_key: form.api_key, affiliate_id: form.affiliate_id }
    if (m === 'amazon')      return { credential_id: form.credential_id, credential_secret: form.credential_secret, partner_tag: form.partner_tag, marketplace: 'www.amazon.com' }
    if (m === 'aliexpress')  return { app_key: form.app_key, app_secret: form.client_secret, tracking_id: form.tracking_id }
    if (m === 'ebay')        return { client_id: form.ebay_client_id, client_secret: form.ebay_client_secret, campaign_id: form.ebay_campaign_id, marketplace_id: form.marketplace_id }
    if (m === 'cj_affiliate') return { personal_access_token: form.personal_access_token, website_id: form.cj_website_id, company_id: form.company_id }
    if (m === 'awin')        return { api_token: form.awin_api_token, publisher_id: form.publisher_id, datafeed_api_key: form.datafeed_api_key }
    if (m === 'rakuten')     return { username: form.rakuten_username, password: form.rakuten_password, sid: form.sid, publisher_id: form.rakuten_publisher_id }
    return { api_key: form.api_key }
  }

  async function load() {
    setLoading(true)
    const [a, c] = await Promise.all([
      api.accounts.list().catch(() => []),
      api.campaigns.list().catch(() => []),
    ])
    setAccounts(a)
    setCampaigns(c)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  async function create() {
    if (!form.display_name) return
    await api.accounts.create({
      marketplace: form.marketplace,
      display_name: form.display_name,
      credentials: buildCredentials(),
    })
    setModal(false)
    load()
  }

  async function createCampaign(accountId: string) {
    if (!campaignForm.name || !campaignForm.external_campaign_id) return
    await api.campaigns.create({
      marketplace_account_id: accountId,
      name: campaignForm.name,
      external_campaign_id: campaignForm.external_campaign_id,
      marketplace_label: campaignForm.marketplace_label || null,
    })
    setCampaignModal(null)
    setCampaignForm({ name: '', external_campaign_id: '', marketplace_label: '' })
    load()
  }

  async function removeCampaign(id: string) {
    if (!confirm('Удалить программу?')) return
    await api.campaigns.delete(id)
    load()
  }

  async function healthcheck(id: string) {
    setChecking(id)
    await api.accounts.healthcheck(id).catch(() => null)
    await load()
    setChecking(null)
  }

  async function remove(id: string) {
    if (!confirm('Удалить площадку?')) return
    await api.accounts.delete(id)
    load()
  }

  function accountCampaigns(accountId: string) {
    return campaigns.filter(c => c.marketplace_account_id === accountId)
  }

  async function discoverPrograms(accountId: string) {
    setDiscoverModal(accountId)
    setDiscovering(true)
    setDiscoveredPrograms([])
    setSelectedPrograms(new Set())
    try {
      const programs = await api.accounts.discoverPrograms(accountId)
      // Filter out programs that are already added as campaigns
      const existingIds = new Set(accountCampaigns(accountId).map(c => c.external_campaign_id))
      setDiscoveredPrograms(programs.filter(p => !existingIds.has(p.id)))
    } catch {
      setDiscoveredPrograms([])
    }
    setDiscovering(false)
  }

  function toggleProgram(id: string) {
    setSelectedPrograms(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  function toggleAllPrograms() {
    if (selectedPrograms.size === discoveredPrograms.length) {
      setSelectedPrograms(new Set())
    } else {
      setSelectedPrograms(new Set(discoveredPrograms.map(p => p.id)))
    }
  }

  async function importSelected() {
    if (!discoverModal || selectedPrograms.size === 0) return
    setImporting(true)
    for (const prog of discoveredPrograms.filter(p => selectedPrograms.has(p.id))) {
      const label = prog.name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '')
      await api.campaigns.create({
        marketplace_account_id: discoverModal,
        name: prog.name,
        external_campaign_id: prog.id,
        marketplace_label: label,
      }).catch(() => null)
    }
    setImporting(false)
    setDiscoverModal(null)
    load()
  }

  const isNetwork = (marketplace: string) => NETWORK_TYPES.includes(marketplace)

  return (
    <AuthGuard>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Площадки</h1>
            <p className="text-sm text-slate-500 mt-0.5">Подключённые маркетплейсы и партнёрские сети</p>
          </div>
          <button
            onClick={() => setModal(true)}
            className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={15} /> Добавить
          </button>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="text-center py-12 text-slate-400 text-sm">Загрузка...</div>
          ) : accounts.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-slate-400 text-sm">Нет подключённых площадок</p>
              <p className="text-slate-300 text-xs mt-1">Добавьте первую, чтобы начать собирать товары</p>
            </div>
          ) : (
            <div>
              {/* Header */}
              <div className="grid grid-cols-[1fr_120px_120px_100px_140px_120px] border-b border-slate-100 px-5 py-3">
                {['Название','Площадка','Программы','Статус','Проверено',''].map(h => (
                  <span key={h} className="text-xs font-medium text-slate-500 uppercase tracking-wide">{h}</span>
                ))}
              </div>
              {/* Rows */}
              {accounts.map(a => {
                const acCampaigns = accountCampaigns(a.id)
                const isExp = expanded === a.id
                return (
                  <div key={a.id} className="border-b border-slate-50">
                    <div className="grid grid-cols-[1fr_120px_120px_100px_140px_120px] items-center px-5 py-3.5 hover:bg-slate-50 transition-colors">
                      <div className="font-medium text-slate-900 flex items-center gap-2">
                        {isNetwork(a.marketplace) ? (
                          <button onClick={() => setExpanded(isExp ? null : a.id)} className="text-slate-400 hover:text-slate-600">
                            {isExp ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                          </button>
                        ) : <span className="w-[14px]" />}
                        {a.display_name}
                      </div>
                      <div>
                        <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-xs font-medium">
                          {LABELS[a.marketplace] ?? a.marketplace}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500">
                        {isNetwork(a.marketplace) ? `${acCampaigns.length} прог.` : '—'}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <HealthIcon status={a.health_status} />
                        <span className="text-xs text-slate-600">{a.health_status}</span>
                      </div>
                      <div className="text-xs text-slate-400">
                        {a.last_health_check ? new Date(a.last_health_check).toLocaleString('ru-RU') : '—'}
                      </div>
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => healthcheck(a.id)}
                          disabled={checking === a.id}
                          className="text-xs text-slate-500 hover:text-brand-600 flex items-center gap-1 transition-colors disabled:opacity-50"
                        >
                          <RefreshCw size={12} className={checking === a.id ? 'animate-spin' : ''} />
                          Проверить
                        </button>
                        <button onClick={() => remove(a.id)} className="text-slate-300 hover:text-red-500 transition-colors">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    {/* Campaigns section */}
                    {isExp && isNetwork(a.marketplace) && (
                      <div className="bg-slate-50 border-t border-slate-100 px-8 py-3">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Программы (кампании)</span>
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => discoverPrograms(a.id)}
                              className="flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-700 font-medium"
                            >
                              <Download size={12} /> Импорт из API
                            </button>
                            <button
                              onClick={() => { setCampaignModal(a.id); setCampaignForm({ name: '', external_campaign_id: '', marketplace_label: '' }) }}
                              className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 font-medium"
                            >
                              <Plus size={12} /> Добавить
                            </button>
                          </div>
                        </div>
                        {acCampaigns.length === 0 ? (
                          <p className="text-xs text-slate-400 py-2">Нет программ. Добавьте первую.</p>
                        ) : (
                          <div className="space-y-1">
                            {acCampaigns.map(c => (
                              <div key={c.id} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-slate-200">
                                <div className="flex items-center gap-3">
                                  <span className="text-sm font-medium text-slate-900">{c.name}</span>
                                  <span className="text-xs text-slate-400">ID: {c.external_campaign_id}</span>
                                  {c.marketplace_label && (
                                    <span className="bg-blue-50 text-blue-600 px-2 py-0.5 rounded text-xs">{c.marketplace_label}</span>
                                  )}
                                </div>
                                <button onClick={() => removeCampaign(c.id)} className="text-slate-300 hover:text-red-500 transition-colors">
                                  <Trash2 size={13} />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Add Account Modal */}
      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-100">
              <h2 className="font-semibold text-slate-900">Добавить площадку</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Площадка</label>
                <select
                  value={form.marketplace}
                  onChange={e => setForm(f => ({...f, marketplace: e.target.value}))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  {MKT_OPTIONS.map(m => <option key={m} value={m}>{LABELS[m] ?? m}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Название</label>
                <input
                  value={form.display_name}
                  onChange={e => setForm(f => ({...f, display_name: e.target.value}))}
                  placeholder="Мой Admitad аккаунт"
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>

              {/* Admitad fields — no campaign_id, it's per-campaign now */}
              {form.marketplace === 'admitad' && <>
                <p className="text-xs text-slate-400 bg-slate-50 rounded-lg px-3 py-2">
                  Ключи: <a href="https://store.admitad.com/en/webmaster/settings/api/" target="_blank" className="text-brand-600 underline">Admitad → Settings → API</a>.
                  Website ID: <a href="https://api.admitad.com/websites/" target="_blank" className="text-brand-600 underline">api.admitad.com/websites</a> (нужен токен).
                  Программы (кампании) добавляются после создания аккаунта.
                </p>
                <CredField label="Client ID" value={form.client_id} onChange={v => setForm(f=>({...f,client_id:v}))} placeholder="из Settings → API" />
                <CredField label="Client Secret" value={form.client_secret} onChange={v => setForm(f=>({...f,client_secret:v}))} secret placeholder="из Settings → API" />
                <CredField label="Website ID" value={form.website_id} onChange={v => setForm(f=>({...f,website_id:v}))} placeholder="напр. 2919039" />
              </>}

              {/* GdeSlon fields */}
              {form.marketplace === 'gdeslon' && <>
                <CredField label="API Key" value={form.api_key} onChange={v => setForm(f=>({...f,api_key:v}))} secret />
                <CredField label="Affiliate ID" value={form.affiliate_id} onChange={v => setForm(f=>({...f,affiliate_id:v}))} />
              </>}

              {/* Amazon fields */}
              {form.marketplace === 'amazon' && <>
                <CredField label="Credential ID" value={form.credential_id} onChange={v => setForm(f=>({...f,credential_id:v}))} />
                <CredField label="Credential Secret" value={form.credential_secret} onChange={v => setForm(f=>({...f,credential_secret:v}))} secret />
                <CredField label="Partner Tag" value={form.partner_tag} onChange={v => setForm(f=>({...f,partner_tag:v}))} placeholder="mystore-20" />
              </>}

              {/* AliExpress fields */}
              {form.marketplace === 'aliexpress' && <>
                <CredField label="App Key" value={form.app_key} onChange={v => setForm(f=>({...f,app_key:v}))} />
                <CredField label="App Secret" value={form.client_secret} onChange={v => setForm(f=>({...f,client_secret:v}))} secret />
                <CredField label="Tracking ID" value={form.tracking_id} onChange={v => setForm(f=>({...f,tracking_id:v}))} />
              </>}

              {/* eBay fields */}
              {form.marketplace === 'ebay' && <>
                <CredField label="Client ID" value={form.ebay_client_id} onChange={v => setForm(f=>({...f,ebay_client_id:v}))} placeholder="YourAppI-XXXX-PRD-..." />
                <CredField label="Client Secret" value={form.ebay_client_secret} onChange={v => setForm(f=>({...f,ebay_client_secret:v}))} secret />
                <CredField label="EPN Campaign ID" value={form.ebay_campaign_id} onChange={v => setForm(f=>({...f,ebay_campaign_id:v}))} placeholder="5338XXXXXXXXX" />
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">Marketplace</label>
                  <select value={form.marketplace_id} onChange={e => setForm(f=>({...f,marketplace_id:e.target.value}))}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                    {['EBAY_US','EBAY_GB','EBAY_DE','EBAY_AU','EBAY_CA','EBAY_FR','EBAY_IT','EBAY_ES','EBAY_IN'].map(m =>
                      <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              </>}

              {/* CJ Affiliate fields */}
              {form.marketplace === 'cj_affiliate' && <>
                <CredField label="Personal Access Token" value={form.personal_access_token} onChange={v => setForm(f=>({...f,personal_access_token:v}))} secret />
                <CredField label="Website ID" value={form.cj_website_id} onChange={v => setForm(f=>({...f,cj_website_id:v}))} placeholder="XXXXXXXX" />
                <CredField label="Company ID (CID)" value={form.company_id} onChange={v => setForm(f=>({...f,company_id:v}))} placeholder="XXXXXXXX" />
              </>}

              {/* Awin fields */}
              {form.marketplace === 'awin' && <>
                <CredField label="API Token" value={form.awin_api_token} onChange={v => setForm(f=>({...f,awin_api_token:v}))} secret />
                <CredField label="Publisher ID" value={form.publisher_id} onChange={v => setForm(f=>({...f,publisher_id:v}))} placeholder="123456" />
                <CredField label="Datafeed API Key" value={form.datafeed_api_key} onChange={v => setForm(f=>({...f,datafeed_api_key:v}))} secret />
              </>}

              {/* Rakuten fields */}
              {form.marketplace === 'rakuten' && <>
                <CredField label="Username" value={form.rakuten_username} onChange={v => setForm(f=>({...f,rakuten_username:v}))} />
                <CredField label="Password" value={form.rakuten_password} onChange={v => setForm(f=>({...f,rakuten_password:v}))} secret />
                <CredField label="Site ID (scope)" value={form.sid} onChange={v => setForm(f=>({...f,sid:v}))} placeholder="1234567" />
                <CredField label="Publisher ID (11 chars)" value={form.rakuten_publisher_id} onChange={v => setForm(f=>({...f,rakuten_publisher_id:v}))} placeholder="XXXXXXXXXXX" />
              </>}

              {/* Generic fallback */}
              {!['admitad','gdeslon','amazon','aliexpress','ebay','cj_affiliate','awin','rakuten'].includes(form.marketplace) && <>
                <CredField label="API Key" value={form.api_key} onChange={v => setForm(f=>({...f,api_key:v}))} secret />
              </>}
            </div>
            <div className="p-6 border-t border-slate-100 flex gap-3">
              <button onClick={() => setModal(false)} className="flex-1 border border-slate-200 rounded-lg py-2 text-sm text-slate-600 hover:bg-slate-50">Отмена</button>
              <button onClick={create} className="flex-1 bg-brand-600 hover:bg-brand-700 text-white rounded-lg py-2 text-sm font-medium transition-colors">Добавить</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Campaign Modal */}
      {campaignModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="p-6 border-b border-slate-100">
              <h2 className="font-semibold text-slate-900">Добавить программу</h2>
              <p className="text-xs text-slate-400 mt-1">Программа (кампания) в партнёрской сети</p>
            </div>
            <div className="p-6 space-y-4">
              <CredField
                label="Название"
                value={campaignForm.name}
                onChange={v => setCampaignForm(f => ({...f, name: v}))}
                placeholder="OZON Travel"
              />
              <CredField
                label="Campaign ID (из URL программы)"
                value={campaignForm.external_campaign_id}
                onChange={v => setCampaignForm(f => ({...f, external_campaign_id: v}))}
                placeholder="29169"
              />
              <CredField
                label="Метка (необязательно)"
                value={campaignForm.marketplace_label}
                onChange={v => setCampaignForm(f => ({...f, marketplace_label: v}))}
                placeholder="ozon_travel"
              />
            </div>
            <div className="p-6 border-t border-slate-100 flex gap-3">
              <button onClick={() => setCampaignModal(null)} className="flex-1 border border-slate-200 rounded-lg py-2 text-sm text-slate-600 hover:bg-slate-50">Отмена</button>
              <button onClick={() => createCampaign(campaignModal)} className="flex-1 bg-brand-600 hover:bg-brand-700 text-white rounded-lg py-2 text-sm font-medium transition-colors">Добавить</button>
            </div>
          </div>
        </div>
      )}
      {/* Discover Programs Modal */}
      {discoverModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col">
            <div className="p-6 border-b border-slate-100">
              <h2 className="font-semibold text-slate-900">Импорт программ из API</h2>
              <p className="text-xs text-slate-400 mt-1">Выберите программы для добавления</p>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {discovering ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw size={20} className="animate-spin text-slate-400" />
                  <span className="ml-2 text-sm text-slate-400">Загрузка программ...</span>
                </div>
              ) : discoveredPrograms.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-8">Нет новых программ для импорта (все уже добавлены или нет подключённых программ)</p>
              ) : (
                <div className="space-y-1">
                  <label className="flex items-center gap-2 px-3 py-2 text-xs text-slate-500 cursor-pointer hover:bg-slate-50 rounded-lg">
                    <input
                      type="checkbox"
                      checked={selectedPrograms.size === discoveredPrograms.length}
                      onChange={toggleAllPrograms}
                      className="rounded border-slate-300"
                    />
                    Выбрать все ({discoveredPrograms.length})
                  </label>
                  {discoveredPrograms.map(p => (
                    <label
                      key={p.id}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-colors ${
                        selectedPrograms.has(p.id) ? 'border-brand-300 bg-brand-50' : 'border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedPrograms.has(p.id)}
                        onChange={() => toggleProgram(p.id)}
                        className="rounded border-slate-300"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-slate-900 truncate">{p.name}</div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-slate-400">ID: {p.id}</span>
                          {p.currency && <span className="text-xs text-slate-400">{p.currency}</span>}
                          {p.cr != null && <span className="text-xs text-emerald-600">CR: {p.cr}%</span>}
                          {p.categories.length > 0 && (
                            <span className="text-xs text-slate-400 truncate">{p.categories.slice(0, 2).join(', ')}</span>
                          )}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
            <div className="p-6 border-t border-slate-100 flex gap-3">
              <button onClick={() => setDiscoverModal(null)} className="flex-1 border border-slate-200 rounded-lg py-2 text-sm text-slate-600 hover:bg-slate-50">Отмена</button>
              <button
                onClick={importSelected}
                disabled={selectedPrograms.size === 0 || importing}
                className="flex-1 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium transition-colors"
              >
                {importing ? 'Импорт...' : `Импортировать (${selectedPrograms.size})`}
              </button>
            </div>
          </div>
        </div>
      )}
    </AuthGuard>
  )
}

function CredField({ label, value, onChange, placeholder, secret }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; secret?: boolean
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-700 mb-1.5">{label}</label>
      <input
        type={secret ? 'password' : 'text'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </div>
  )
}
