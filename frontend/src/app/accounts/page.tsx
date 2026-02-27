'use client'
import { useEffect, useState } from 'react'
import AuthGuard from '@/components/AuthGuard'
import { api, Account } from '@/lib/api'
import { Plus, RefreshCw, Trash2, CheckCircle, XCircle, Clock } from 'lucide-react'

const MKT_OPTIONS = [
  'admitad','gdeslon','amazon','ebay','aliexpress',
  'yandex_market','cj_affiliate','awin','walmart','rakuten',
]

const LABELS: Record<string,string> = {
  admitad:'Admitad', gdeslon:'GdeSlon', amazon:'Amazon', ebay:'eBay',
  aliexpress:'AliExpress', yandex_market:'Яндекс.Маркет',
  cj_affiliate:'CJ Affiliate', awin:'Awin', walmart:'Walmart', rakuten:'Rakuten',
}

function HealthIcon({ status }: { status: string }) {
  if (status === 'ok')      return <CheckCircle size={14} className="text-green-500" />
  if (status === 'error')   return <XCircle size={14} className="text-red-500" />
  return <Clock size={14} className="text-slate-400" />
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading]   = useState(true)
  const [modal, setModal]       = useState(false)
  const [checking, setChecking] = useState<string | null>(null)

  const [form, setForm] = useState({
    marketplace: 'admitad', display_name: '',
    client_id: '', client_secret: '', website_id: '', campaign_id: '',
    app_key: '', tracking_id: '', api_key: '', affiliate_id: '',
    partner_tag: '', credential_id: '', credential_secret: '',
  })

  function buildCredentials() {
    const m = form.marketplace
    if (m === 'admitad')  return { client_id: form.client_id, client_secret: form.client_secret, website_id: Number(form.website_id), campaign_id: Number(form.campaign_id) }
    if (m === 'gdeslon')  return { api_key: form.api_key, affiliate_id: form.affiliate_id }
    if (m === 'amazon')   return { credential_id: form.credential_id, credential_secret: form.credential_secret, partner_tag: form.partner_tag, marketplace: 'www.amazon.com' }
    if (m === 'aliexpress') return { app_key: form.app_key, app_secret: form.client_secret, tracking_id: form.tracking_id }
    return { api_key: form.api_key }
  }

  async function load() {
    setLoading(true)
    const data = await api.accounts.list().catch(() => [])
    setAccounts(data)
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
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Название</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Площадка</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Статус</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Проверено</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {accounts.map(a => (
                  <tr key={a.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-slate-900">{a.display_name}</td>
                    <td className="px-5 py-3.5">
                      <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-xs font-medium">
                        {LABELS[a.marketplace] ?? a.marketplace}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-1.5">
                        <HealthIcon status={a.health_status} />
                        <span className="text-xs text-slate-600">{a.health_status}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-400">
                      {a.last_health_check ? new Date(a.last_health_check).toLocaleString('ru-RU') : '—'}
                    </td>
                    <td className="px-5 py-3.5">
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
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Add Modal */}
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

              {/* Admitad fields */}
              {form.marketplace === 'admitad' && <>
                <CredField label="Client ID" value={form.client_id} onChange={v => setForm(f=>({...f,client_id:v}))} />
                <CredField label="Client Secret" value={form.client_secret} onChange={v => setForm(f=>({...f,client_secret:v}))} secret />
                <CredField label="Website ID" value={form.website_id} onChange={v => setForm(f=>({...f,website_id:v}))} placeholder="12345" />
                <CredField label="Campaign ID" value={form.campaign_id} onChange={v => setForm(f=>({...f,campaign_id:v}))} placeholder="67890" />
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

              {/* Generic */}
              {!['admitad','gdeslon','amazon','aliexpress'].includes(form.marketplace) && <>
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
