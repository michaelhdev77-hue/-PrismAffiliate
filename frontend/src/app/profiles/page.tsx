'use client'
import { useEffect, useState } from 'react'
import AuthGuard from '@/components/AuthGuard'
import { api, Profile, Campaign } from '@/lib/api'
import { SlidersHorizontal, Plus, Trash2, Play, X } from 'lucide-react'

const MKT_OPTIONS = [
  { value: 'admitad', label: 'Admitad' },
  { value: 'gdeslon', label: 'GdeSlon' },
  { value: 'amazon', label: 'Amazon' },
  { value: 'ebay', label: 'eBay' },
  { value: 'aliexpress', label: 'AliExpress' },
  { value: 'rakuten', label: 'Rakuten' },
  { value: 'cj_affiliate', label: 'CJ Affiliate' },
  { value: 'awin', label: 'Awin' },
]
const SORT_OPTIONS = [
  { value: 'commission', label: 'По комиссии' },
  { value: 'rating', label: 'По рейтингу' },
  { value: 'score', label: 'По скорингу' },
]

interface FormData {
  name: string
  prism_project_id: string
  marketplaces: string[]
  categories: string
  keywords: string
  min_commission_rate: string
  min_rating: string
  max_products: string
  sort_by: string
}

const emptyForm: FormData = {
  name: '', prism_project_id: '', marketplaces: [],
  categories: '', keywords: '', min_commission_rate: '0',
  min_rating: '0', max_products: '5', sort_by: 'commission',
}

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [form, setForm] = useState<FormData>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [running, setRunning] = useState<string | null>(null)
  const [categories, setCategories] = useState<string[]>([])

  async function load() {
    const data = await api.profiles.list().catch(() => [])
    setProfiles(data)
    setLoading(false)
  }

  useEffect(() => {
    load()
    api.products.categories().then(setCategories).catch(() => [])
  }, [])

  function openCreate() {
    setEditId(null)
    setForm(emptyForm)
    setShowForm(true)
  }

  function openEdit(p: Profile) {
    setEditId(p.id)
    setForm({
      name: p.name,
      prism_project_id: p.prism_project_id,
      marketplaces: p.marketplaces,
      categories: p.categories.join(', '),
      keywords: p.keywords.join(', '),
      min_commission_rate: String(p.min_commission_rate),
      min_rating: String(p.min_rating),
      max_products: String(p.max_products),
      sort_by: p.sort_by,
    })
    setShowForm(true)
  }

  async function save() {
    setSaving(true)
    const body = {
      name: form.name,
      prism_project_id: form.prism_project_id,
      marketplaces: form.marketplaces,
      categories: form.categories ? form.categories.split(',').map(s => s.trim()).filter(Boolean) : [],
      keywords: form.keywords ? form.keywords.split(',').map(s => s.trim()).filter(Boolean) : [],
      min_commission_rate: parseFloat(form.min_commission_rate) || 0,
      min_rating: parseFloat(form.min_rating) || 0,
      max_products: parseInt(form.max_products) || 5,
      sort_by: form.sort_by,
    }
    try {
      if (editId) {
        await api.profiles.update(editId, body)
      } else {
        await api.profiles.create(body)
      }
      setShowForm(false)
      await load()
    } catch (e: any) {
      alert(`Ошибка: ${e.message}`)
    }
    setSaving(false)
  }

  async function remove(id: string) {
    if (!confirm('Удалить профиль?')) return
    await api.profiles.delete(id)
    await load()
  }

  async function run(prism_project_id: string) {
    setRunning(prism_project_id)
    try {
      await api.profiles.run(prism_project_id)
      alert('Задача запущена — товары будут подобраны и ссылки сгенерированы')
    } catch (e: any) {
      alert(`Ошибка: ${e.message}`)
    }
    setRunning(null)
  }

  function toggleMkt(mkt: string) {
    setForm(f => ({
      ...f,
      marketplaces: f.marketplaces.includes(mkt)
        ? f.marketplaces.filter(m => m !== mkt)
        : [...f.marketplaces, mkt],
    }))
  }

  return (
    <AuthGuard>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Профили подбора</h1>
            <p className="text-sm text-slate-500 mt-0.5">Правила автоматического подбора товаров для PRISM-проектов</p>
          </div>
          <button
            onClick={openCreate}
            className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={14} /> Создать профиль
          </button>
        </div>

        {/* Profile List */}
        {loading ? (
          <div className="text-center py-20 text-slate-400 text-sm">Загрузка...</div>
        ) : profiles.length === 0 ? (
          <div className="text-center py-20">
            <SlidersHorizontal size={40} className="mx-auto text-slate-200 mb-3" />
            <p className="text-slate-400 text-sm">Нет профилей подбора</p>
            <p className="text-slate-300 text-xs mt-1">Создайте профиль, чтобы автоматически подбирать товары для PRISM</p>
          </div>
        ) : (
          <div className="space-y-4">
            {profiles.map(p => (
              <div key={p.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-base font-semibold text-slate-900">{p.name}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded ${p.is_active ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                        {p.is_active ? 'Активен' : 'Отключён'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-sm">
                      <div className="text-slate-500">PRISM Project: <span className="text-slate-700 font-mono text-xs">{p.prism_project_id}</span></div>
                      <div className="text-slate-500">Макс. товаров: <span className="text-slate-700">{p.max_products}</span></div>
                      <div className="text-slate-500">Площадки: <span className="text-slate-700">{p.marketplaces.length ? p.marketplaces.join(', ') : 'все'}</span></div>
                      <div className="text-slate-500">Мин. комиссия: <span className="text-slate-700">{p.min_commission_rate}%</span></div>
                      <div className="text-slate-500">Категории: <span className="text-slate-700">{p.categories.length ? p.categories.join(', ') : 'все'}</span></div>
                      <div className="text-slate-500">Сортировка: <span className="text-slate-700">{p.sort_by}</span></div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => run(p.prism_project_id)}
                      disabled={running === p.prism_project_id}
                      className="flex items-center gap-1.5 bg-green-50 hover:bg-green-100 text-green-700 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                      title="Запустить подбор и генерацию ссылок"
                    >
                      <Play size={12} />
                      {running === p.prism_project_id ? 'Запуск...' : 'Запустить'}
                    </button>
                    <button
                      onClick={() => openEdit(p)}
                      className="text-slate-400 hover:text-brand-600 transition-colors px-2 py-1.5"
                    >
                      <SlidersHorizontal size={14} />
                    </button>
                    <button
                      onClick={() => remove(p.id)}
                      className="text-slate-400 hover:text-red-500 transition-colors px-2 py-1.5"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create/Edit Modal */}
        {showForm && (
          <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowForm(false)}>
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-5" onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">
                  {editId ? 'Редактировать профиль' : 'Новый профиль'}
                </h2>
                <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-600">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Название</label>
                  <input
                    value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Например: Fashion Products"
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">PRISM Project ID</label>
                  <input
                    value={form.prism_project_id}
                    onChange={e => setForm(f => ({ ...f, prism_project_id: e.target.value }))}
                    placeholder="UUID проекта из PRISM"
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Площадки</label>
                  <div className="flex flex-wrap gap-2">
                    {MKT_OPTIONS.map(m => (
                      <button
                        key={m.value}
                        type="button"
                        onClick={() => toggleMkt(m.value)}
                        className={`text-xs px-2.5 py-1 rounded-lg border transition-colors ${
                          form.marketplaces.includes(m.value)
                            ? 'bg-brand-50 border-brand-300 text-brand-700'
                            : 'border-slate-200 text-slate-500 hover:border-slate-300'
                        }`}
                      >
                        {m.label}
                      </button>
                    ))}
                  </div>
                  <p className="text-xs text-slate-400 mt-1">Не выбрано = все площадки</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Категории</label>
                  <input
                    value={form.categories}
                    onChange={e => setForm(f => ({ ...f, categories: e.target.value }))}
                    placeholder="Через запятую: Dresses, Shoes"
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Мин. комиссия %</label>
                    <input
                      type="number"
                      value={form.min_commission_rate}
                      onChange={e => setForm(f => ({ ...f, min_commission_rate: e.target.value }))}
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Мин. рейтинг</label>
                    <input
                      type="number"
                      step="0.1"
                      value={form.min_rating}
                      onChange={e => setForm(f => ({ ...f, min_rating: e.target.value }))}
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Макс. товаров</label>
                    <input
                      type="number"
                      value={form.max_products}
                      onChange={e => setForm(f => ({ ...f, max_products: e.target.value }))}
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Сортировка</label>
                  <select
                    value={form.sort_by}
                    onChange={e => setForm(f => ({ ...f, sort_by: e.target.value }))}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800 transition-colors"
                >
                  Отмена
                </button>
                <button
                  onClick={save}
                  disabled={saving || !form.name || !form.prism_project_id}
                  className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {saving ? 'Сохранение...' : editId ? 'Сохранить' : 'Создать'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AuthGuard>
  )
}
