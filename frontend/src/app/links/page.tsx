'use client'
import { useEffect, useState } from 'react'
import AuthGuard from '@/components/AuthGuard'
import { api, Link as AffLink } from '@/lib/api'
import { Link2, Copy, CheckCheck } from 'lucide-react'

export default function LinksPage() {
  const [links, setLinks] = useState<AffLink[]>([])
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState<string|null>(null)

  useEffect(() => {
    api.links.list().then(setLinks).catch(()=>[]).finally(()=>setLoading(false))
  }, [])

  function copy(code: string) {
    const url = `${window.location.origin.replace('3001','8013')}/r/${code}`
    navigator.clipboard.writeText(url)
    setCopied(code)
    setTimeout(() => setCopied(null), 2000)
  }

  const MKT: Record<string,string> = {
    amazon:'Amazon', ebay:'eBay', rakuten:'Rakuten',
    cj_affiliate:'CJ Affiliate', awin:'Awin',
    admitad:'Admitad', gdeslon:'GdeSlon', aliexpress:'AliExpress',
  }

  return (
    <AuthGuard>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Ссылки</h1>
          <p className="text-sm text-slate-500 mt-0.5">Сгенерированные реферальные ссылки</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="text-center py-12 text-slate-400 text-sm">Загрузка...</div>
          ) : links.length === 0 ? (
            <div className="text-center py-16">
              <Link2 size={36} className="mx-auto text-slate-200 mb-3" />
              <p className="text-slate-400 text-sm">Нет сгенерированных ссылок</p>
              <p className="text-slate-300 text-xs mt-1">Ссылки создаются автоматически при публикации контента через PRISM</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {['Короткий код','Площадка','Товар','Проект PRISM','Создана',''].map(h=>(
                    <th key={h} className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {links.map(l => (
                  <tr key={l.id} className="hover:bg-slate-50">
                    <td className="px-5 py-3.5">
                      <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">/r/{l.short_code}</code>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs">{MKT[l.marketplace]??l.marketplace}</span>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-500 max-w-[200px] truncate">{l.product_id.slice(0,12)}…</td>
                    <td className="px-5 py-3.5 text-xs text-slate-400">{l.prism_project_id ? l.prism_project_id.slice(0,12)+'…' : '—'}</td>
                    <td className="px-5 py-3.5 text-xs text-slate-400">{new Date(l.created_at).toLocaleDateString('ru-RU')}</td>
                    <td className="px-5 py-3.5">
                      <button
                        onClick={() => copy(l.short_code)}
                        className="text-slate-400 hover:text-brand-600 transition-colors"
                        title="Скопировать ссылку"
                      >
                        {copied === l.short_code ? <CheckCheck size={14} className="text-green-500" /> : <Copy size={14} />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AuthGuard>
  )
}
