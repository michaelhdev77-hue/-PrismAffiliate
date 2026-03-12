import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MetricCard from '@/components/MetricCard'

describe('MetricCard', () => {
  it('renders label text', () => {
    render(<MetricCard label="Total Clicks" value={1234} />)
    expect(screen.getByText('Total Clicks')).toBeInTheDocument()
  })

  it('renders numeric value', () => {
    render(<MetricCard label="Revenue" value={5678} />)
    expect(screen.getByText('5678')).toBeInTheDocument()
  })

  it('renders string value', () => {
    render(<MetricCard label="Status" value="Active" />)
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('renders sub text when provided', () => {
    render(<MetricCard label="Clicks" value={100} sub="Last 30 days" />)
    expect(screen.getByText('Last 30 days')).toBeInTheDocument()
  })

  it('does not render sub text when not provided', () => {
    const { container } = render(<MetricCard label="Clicks" value={100} />)
    const subElements = container.querySelectorAll('.text-xs.text-slate-400')
    expect(subElements.length).toBe(0)
  })

  it('applies default violet color class', () => {
    render(<MetricCard label="Test" value={0} />)
    const valueEl = screen.getByText('0')
    expect(valueEl.className).toContain('text-brand-600')
  })

  it('applies green color class', () => {
    render(<MetricCard label="Test" value={42} color="green" />)
    const valueEl = screen.getByText('42')
    expect(valueEl.className).toContain('text-green-600')
  })

  it('applies blue color class', () => {
    render(<MetricCard label="Test" value={99} color="blue" />)
    const valueEl = screen.getByText('99')
    expect(valueEl.className).toContain('text-blue-600')
  })

  it('applies orange color class', () => {
    render(<MetricCard label="Test" value={7} color="orange" />)
    const valueEl = screen.getByText('7')
    expect(valueEl.className).toContain('text-orange-600')
  })

  it('applies slate color class', () => {
    render(<MetricCard label="Test" value={3} color="slate" />)
    const valueEl = screen.getByText('3')
    expect(valueEl.className).toContain('text-slate-700')
  })

  it('applies brand color class', () => {
    render(<MetricCard label="Test" value={1} color="brand" />)
    const valueEl = screen.getByText('1')
    expect(valueEl.className).toContain('text-brand-700')
  })
})
