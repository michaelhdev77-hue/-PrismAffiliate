import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Prism Affiliate',
  description: 'Affiliate marketplace aggregator',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  )
}
