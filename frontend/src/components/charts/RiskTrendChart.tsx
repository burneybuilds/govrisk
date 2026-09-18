import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface RiskTrendChartProps {
  data: Array<{ month: string; low: number; medium: number; high: number; critical: number }>;
  title: string;
  description?: string;
  filters?: string[];
  activeFilter?: string;
  onFilterChange?: (filter: string) => void;
}

const lineConfig = [
  { key: 'low', label: 'Low', color: '#22c55e' },
  { key: 'medium', label: 'Medium', color: '#eab308' },
  { key: 'high', label: 'High', color: '#f97316' },
  { key: 'critical', label: 'Critical', color: '#ef4444' },
];

export function RiskTrendChart({
  data,
  title,
  description,
  filters,
  activeFilter,
  onFilterChange,
}: RiskTrendChartProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-navy-900 lg:text-lg">{title}</h3>
          {description && <p className="mt-1 text-xs text-gray-500 lg:text-sm">{description}</p>}
        </div>
        {filters && filters.length > 0 && (
          <div className="flex max-w-full flex-wrap gap-2">
            {filters.map((filter) => (
              <button
                key={filter}
                onClick={() => onFilterChange?.(filter)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors lg:text-sm ${
                  activeFilter === filter
                    ? 'bg-navy-900 text-white'
                    : 'border border-gray-200 bg-white text-gray-600 hover:border-navy-300 hover:text-navy-900'
                }`}
              >
                {filter}
              </button>
            ))}
          </div>
        )}
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12, fill: '#6b7280' }}
            axisLine={{ stroke: '#e5e7eb' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#6b7280' }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{
              borderRadius: 8,
              border: '1px solid #e5e7eb',
              boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
              fontSize: 12,
            }}
          />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          {lineConfig.map((line) => (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              name={line.label}
              stroke={line.color}
              strokeWidth={2.5}
              dot={{ r: 3, strokeWidth: 0, fill: line.color }}
              activeDot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
