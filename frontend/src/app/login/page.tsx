'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { setToken, DEV_TOKEN } from '@/lib/auth'
import { Zap } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [token, setTokenValue] = useState('')
  const [error, setError] = useState('')

  function login() {
    const t = token.trim() || DEV_TOKEN
    if (!t) { setError('Введите токен'); return }
    setToken(t)
    router.push('/')
  }

  function devLogin() {
    setToken(DEV_TOKEN)
    router.push('/')
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-8">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center">
            <Zap size={20} className="text-white" />
          </div>
          <div>
            <p className="font-bold text-slate-900">Prism Affiliate</p>
            <p className="text-xs text-slate-500">Marketplace aggregator</p>
          </div>
        </div>

        <h1 className="text-xl font-semibold text-slate-900 mb-1">Войти</h1>
        <p className="text-sm text-slate-500 mb-6">Введите JWT-токен для доступа к дашборду</p>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">JWT Token</label>
            <textarea
              value={token}
              onChange={e => setTokenValue(e.target.value)}
              placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
              rows={3}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
            />
          </div>

          {error && <p className="text-red-500 text-xs">{error}</p>}

          <button
            onClick={login}
            className="w-full bg-brand-600 hover:bg-brand-700 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
          >
            Войти
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200" /></div>
            <div className="relative flex justify-center text-xs text-slate-400">
              <span className="bg-white px-2">или</span>
            </div>
          </div>

          <button
            onClick={devLogin}
            className="w-full border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium py-2.5 rounded-lg transition-colors text-sm"
          >
            Dev-режим (тестовый токен)
          </button>
        </div>

        <p className="mt-6 text-xs text-slate-400 text-center">
          Токен хранится только в localStorage браузера
        </p>
      </div>
    </div>
  )
}
