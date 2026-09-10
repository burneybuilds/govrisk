import { useState, useEffect } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from 'recharts';
import { getAnalytics } from '../services/api';
import { LoadingState } from '../components/ui/LoadingState';

function getBarColor(value: number): string {
  if (value > 75) return '#ef4444';
  if (value > 60) return '#f97316';
  if (value > 50) return '#eab308';
  return '#22c55e';
}

function getRiskColor(score: number): string {
  if (score >= 75) return 'text-red-600';
  if (score >= 60) return 'text-orange-600';
  if (score >= 50) return 'text-yellow-600';
  return 'text-green-600';
}

const tooltipStyle = {
  borderRadius: 8,
  border: '1px solid #e5e7eb',
  boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
  fontSize: 12,
};

export default function Analytics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sectorPerformance, setSectorPerformance] = useState<any[]>([]);
  const [correlationData, setCorrelationData] = useState<any[]>([]);
  const [ministryRankings, setMinistryRankings] = useState<any[]>([]);

  useEffect(() => {
    getAnalytics()
      .then((data) => {
        setSectorPerformance(data.sectorAnalytics ?? []);
        setCorrelationData(data.scatterData ?? []);
        setMinistryRankings(data.ministryRankings ?? []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const sortedMinistries = [...ministryRankings].sort((a, b) => b.avgRisk - a.avgRisk);

  if (loading) return <LoadingState />;
  if (error) return <div className="p-6 text-center text-red-600">Error: {error}</div>;

  return (
    <div className="min-w-0">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">Analytics</h1>
        <p className="mt-1 text-sm text-gray-500 lg:text-base">
          Portfolio performance analytics and insights
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
          <h3 className="text-base font-semibold text-navy-900 lg:text-lg">Sector Risk Comparison</h3>
          <p className="mt-1 text-xs text-gray-500 lg:text-sm">
            Average risk score across monitored infrastructure sectors.
          </p>
          <div className="mt-4">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={sectorPerformance} margin={{ top: 10, right: 12, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                <XAxis
                  dataKey="sector"
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  axisLine={{ stroke: '#e5e7eb' }}
                  tickLine={false}
                  interval={0}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  axisLine={false}
                  tickLine={false}
                  width={40}
                  domain={[0, 100]}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(value) => [`${value}`, 'Avg Risk Score']}
                  cursor={{ fill: '#f8fafc' }}
                />
                <Bar dataKey="avgRisk" radius={[4, 4, 0, 0]} maxBarSize={48}>
                  {sectorPerformance.map((entry, index) => (
                    <Cell key={index} fill={getBarColor(entry.avgRisk)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
          <h3 className="text-base font-semibold text-navy-900 lg:text-lg">Cost Overrun Analysis</h3>
          <p className="mt-1 text-xs text-gray-500 lg:text-sm">
            Cost overrun percentage vs progress gap across projects.
          </p>
          <div className="mt-4">
            <ResponsiveContainer width="100%" height={320}>
              <ScatterChart margin={{ top: 10, right: 16, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="progressGap"
                  name="Progress Gap"
                  type="number"
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  axisLine={{ stroke: '#e5e7eb' }}
                  tickLine={false}
                  label={{ value: 'Progress Gap (%)', position: 'bottom', offset: 2, fontSize: 12, fill: '#6b7280' }}
                />
                <YAxis
                  dataKey="costOverrun"
                  name="Cost Overrun"
                  type="number"
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  axisLine={{ stroke: '#e5e7eb' }}
                  tickLine={false}
                  label={{ value: 'Cost Overrun (%)', angle: -90, position: 'insideLeft', fontSize: 12, fill: '#6b7280' }}
                />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  contentStyle={tooltipStyle}
                  content={({ payload }) => {
                    if (!payload || payload.length === 0) return null;
                    const data = payload[0].payload;
                    return (
                      <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm shadow-sm">
                        <div className="font-semibold text-navy-900">{data.name}</div>
                        <div className="mt-1 text-gray-600">Progress Gap: {data.progressGap}%</div>
                        <div className="text-gray-600">Cost Overrun: {data.costOverrun}%</div>
                        <div className="text-gray-600">Risk Score: {data.riskScore}</div>
                      </div>
                    );
                  }}
                />
                <Scatter data={correlationData} fill="#3b82f6" fillOpacity={0.7} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
          <h3 className="text-base font-semibold text-navy-900 lg:text-lg">Schedule Delay by Sector</h3>
          <p className="mt-1 text-xs text-gray-500 lg:text-sm">
            Average schedule delay in months per sector.
          </p>
          <div className="mt-4">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={sectorPerformance} layout="vertical" margin={{ top: 0, right: 24, left: 20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  axisLine={{ stroke: '#e5e7eb' }}
                  tickLine={false}
                />
                <YAxis
                  dataKey="sector"
                  type="category"
                  tick={{ fontSize: 12, fill: '#374151' }}
                  axisLine={false}
                  tickLine={false}
                  width={150}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(value) => [`${value} months`, 'Avg Delay']}
                  cursor={{ fill: '#f8fafc' }}
                />
                <Bar dataKey="avgDelay" fill="#3b82f6" radius={[0, 4, 4, 0]} maxBarSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <div className="border-b border-gray-100 px-5 py-4 lg:px-6">
            <h3 className="text-base font-semibold text-navy-900 lg:text-lg">Ministry Risk Ranking</h3>
            <p className="mt-1 text-xs text-gray-500 lg:text-sm">
              Ministries ranked by average risk score of their projects.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
                  <th className="px-4 py-3 font-semibold lg:px-6">Rank</th>
                  <th className="px-4 py-3 font-semibold">Ministry</th>
                  <th className="px-4 py-3 font-semibold">Projects</th>
                  <th className="px-4 py-3 font-semibold">Average Risk</th>
                  <th className="px-4 py-3 font-semibold">High Risk Projects</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {sortedMinistries.map((ministry, index) => (
                  <tr key={ministry.ministry} className="transition-colors hover:bg-gray-50">
                    <td className="px-4 py-3 font-semibold text-navy-900 lg:px-6">
                      {index < 3 ? (
                        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-navy-900 text-xs font-bold text-white">
                          {index + 1}
                        </span>
                      ) : (
                        index + 1
                      )}
                    </td>
                    <td className="px-4 py-3 font-medium text-navy-900">{ministry.ministry}</td>
                    <td className="px-4 py-3 text-gray-600">{ministry.projectCount}</td>
                    <td className="px-4 py-3">
                      <span className={`font-semibold ${getRiskColor(ministry.avgRisk)}`}>
                        {ministry.avgRisk}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{ministry.highRiskCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
