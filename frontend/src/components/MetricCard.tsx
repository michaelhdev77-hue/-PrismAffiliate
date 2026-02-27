interface Props {
  label: string
  value: string | number
  sub?: string
  color?: 'violet' | 'green' | 'blue' | 'orange'
}

const colors = {
  violet: 'bg-brand-50 text-brand-600',
  green:  'bg-green-50 text-green-600',
  blue:   'bg-blue-50 text-blue-600',
  orange: 'bg-orange-50 text-orange-600',
}

export default function MetricCard({ label, value, sub, color = 'violet' }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${colors[color].split(' ')[1]}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  )
}
