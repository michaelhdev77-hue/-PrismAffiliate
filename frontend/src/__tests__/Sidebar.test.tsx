import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}))

// Mock next/navigation
vi.mock('next/navigation', () => ({
  usePathname: () => '/',
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}))

// Mock @/lib/auth
vi.mock('@/lib/auth', () => ({
  clearToken: vi.fn(),
}))

import Sidebar from '@/components/Sidebar'

const NAV_ITEMS = [
  { label: 'Дашборд', href: '/' },
  { label: 'Площадки', href: '/accounts' },
  { label: 'Фиды', href: '/feeds' },
  { label: 'Товары', href: '/products' },
  { label: 'Профили', href: '/profiles' },
  { label: 'Ссылки', href: '/links' },
  { label: 'Аналитика', href: '/analytics' },
]

describe('Sidebar', () => {
  it('renders all navigation items', () => {
    render(<Sidebar />)
    for (const item of NAV_ITEMS) {
      expect(screen.getByText(item.label)).toBeInTheDocument()
    }
  })

  it('renders correct number of nav links', () => {
    const { container } = render(<Sidebar />)
    // 7 nav links + each has an icon
    const links = container.querySelectorAll('nav a')
    expect(links.length).toBe(NAV_ITEMS.length)
  })

  it('renders correct href for each nav item', () => {
    const { container } = render(<Sidebar />)
    const links = container.querySelectorAll('nav a')
    const hrefs = Array.from(links).map(a => a.getAttribute('href'))
    for (const item of NAV_ITEMS) {
      expect(hrefs).toContain(item.href)
    }
  })

  it('renders the logo text', () => {
    render(<Sidebar />)
    expect(screen.getByText('Prism Affiliate')).toBeInTheDocument()
  })

  it('renders logout button', () => {
    render(<Sidebar />)
    expect(screen.getByText('Выйти')).toBeInTheDocument()
  })

  it('each nav item has an icon (svg element)', () => {
    const { container } = render(<Sidebar />)
    const navLinks = container.querySelectorAll('nav a')
    for (const link of Array.from(navLinks)) {
      const svg = link.querySelector('svg')
      expect(svg).toBeTruthy()
    }
  })

  it('active item (dashboard at /) has active class', () => {
    render(<Sidebar />)
    const dashboardLink = screen.getByText('Дашборд').closest('a')
    expect(dashboardLink?.className).toContain('bg-brand-600')
    expect(dashboardLink?.className).toContain('text-white')
  })

  it('non-active items have inactive class', () => {
    render(<Sidebar />)
    const accountsLink = screen.getByText('Площадки').closest('a')
    expect(accountsLink?.className).toContain('text-slate-400')
  })
})
