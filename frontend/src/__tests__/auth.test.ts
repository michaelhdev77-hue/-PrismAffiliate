import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
    get length() { return Object.keys(store).length },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  }
})()

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

import { getToken, setToken, clearToken, isLoggedIn } from '@/lib/auth'

beforeEach(() => {
  localStorageMock.clear()
  vi.clearAllMocks()
})

describe('getToken', () => {
  it('returns empty string when no token set', () => {
    expect(getToken()).toBe('')
  })

  it('returns stored token', () => {
    localStorageMock.setItem('affiliate_token', 'my-jwt-token')
    expect(getToken()).toBe('my-jwt-token')
  })

  it('calls localStorage.getItem with correct key', () => {
    getToken()
    expect(localStorageMock.getItem).toHaveBeenCalledWith('affiliate_token')
  })
})

describe('setToken', () => {
  it('stores token in localStorage', () => {
    setToken('new-token')
    expect(localStorageMock.setItem).toHaveBeenCalledWith('affiliate_token', 'new-token')
  })

  it('stored token is retrievable via getToken', () => {
    setToken('stored-token')
    expect(getToken()).toBe('stored-token')
  })
})

describe('clearToken', () => {
  it('removes token from localStorage', () => {
    setToken('token-to-clear')
    clearToken()
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('affiliate_token')
  })

  it('getToken returns empty after clear', () => {
    setToken('temp-token')
    clearToken()
    expect(getToken()).toBe('')
  })
})

describe('isLoggedIn', () => {
  it('returns false when no token', () => {
    expect(isLoggedIn()).toBe(false)
  })

  it('returns true when token exists', () => {
    setToken('valid-token')
    expect(isLoggedIn()).toBe(true)
  })

  it('returns false after clearToken', () => {
    setToken('temp')
    clearToken()
    expect(isLoggedIn()).toBe(false)
  })
})
