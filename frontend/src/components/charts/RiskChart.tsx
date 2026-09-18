import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

interface RiskChartProps {
  data: { name: string; value: number; color: string }[];
  title: string;
  description?: string;
}

export function RiskChart({ data, title, description }: RiskChartProps) {
  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
      <h3 className="text-base font-semibold text-navy-900 lg:text-lg">{title}</h3>
      {description && <p className="mt-1 text-xs text-gray-500 lg:text-sm">{description}</p>}
      <div className="relative mx-auto mt-2 h-[260px] w-full sm:h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius="62%"
              outerRadius="88%"
              paddingAngle={2}
              strokeWidth={0}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name) => [`${value} projects`, name]}
              contentStyle={{
                borderRadius: 8,
                border: '1px solid #e5e7eb',
                boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                fontSize: 12,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className="text-2xl font-bold text-navy-900 lg:text-3xl">
              {total.toLocaleString('en-IN')}
            </div>
            <div className="text-xs text-gray-500">Total Projects</div>
          </div>
        </div>
      </div>

      <div className="mx-auto grid max-w-xs grid-cols-2 gap-x-6 gap-y-2 px-2 pt-4 sm:max-w-none">
        {data.map((item) => {
          const pct = total > 0 ? Math.round((item.value / total) * 100) : 0;
          return (
            <div key={item.name} className="flex items-center justify-between gap-2 text-sm">
              <span className="flex items-center gap-2 text-gray-600">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                {item.name}
              </span>
              <span className="font-semibold text-navy-900">{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
