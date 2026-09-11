import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  AlertTriangle,
  Clock,
  DollarSign,
  FolderOpen,
  TrendingUp,
  ArrowRight,
} from 'lucide-react';
import { getDashboard, getProjects, getAnalytics } from '../services/api';
import { KpiCard } from '../components/ui/KpiCard';
import { RiskBadge } from '../components/ui/RiskBadge';
import { RiskScore } from '../components/ui/RiskScore';
import { ProgressBar } from '../components/ui/ProgressBar';
import { RiskChart } from '../components/charts/RiskChart';
import { RiskTrendChart } from '../components/charts/RiskTrendChart';
import { LoadingState } from '../components/ui/LoadingState';

const sectorFilters = ['All Sectors', 'Transport', 'Energy', 'Water', 'Communication', 'Social Infrastructure'];

function getCostOverrunColor(overrun: number) {
  if (overrun > 15) return 'text-red-600';
  if (overrun > 10) return 'text-orange-600';
  return 'text-gray-600';
}

function getDelayColor(probability: number) {
  if (probability >= 85) return 'text-red-600';
  if (probability >= 70) return 'text-orange-600';
  return 'text-gray-600';
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [activeSector, setActiveSector] = useState('All Sectors');
  const [dashboard, setDashboard] = useState<any>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [dash, proj, an] = await Promise.all([getDashboard(), getProjects(), getAnalytics()]);
        setDashboard(dash);
        setProjects(proj);
        setAnalytics(an);
      } catch (err: any) {
        setError(err.message || 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="min-w-0">
        <div className="mb-6 inline-block rounded-xl bg-white px-6 py-3 shadow-md">
          <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">
            Infrastructure Risk Overview
          </h1>
          <p className="mt-1 text-sm text-gray-600 lg:text-base">
            Predictive intelligence for India's infrastructure project portfolio
          </p>
        </div>
        <LoadingState text="Loading dashboard..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-w-0">
        <div className="mb-6 inline-block rounded-xl bg-white px-6 py-3 shadow-md">
          <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">
            Infrastructure Risk Overview
          </h1>
          <p className="mt-1 text-sm text-gray-600 lg:text-base">
            Predictive intelligence for India's infrastructure project portfolio
          </p>
        </div>
        <div className="flex flex-col items-center py-12">
          <AlertTriangle className="h-10 w-10 text-red-500" />
          <p className="mt-3 text-sm font-medium text-red-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 rounded-lg bg-navy-900 px-4 py-2 text-sm font-medium text-white hover:bg-navy-800"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const highRiskProjects = dashboard.highRiskTable || [];

  const riskDistribution = [
    { name: 'Low', value: dashboard.riskDistribution?.low ?? 0, color: '#22c55e' },
    { name: 'Medium', value: dashboard.riskDistribution?.medium ?? 0, color: '#eab308' },
    { name: 'High', value: dashboard.riskDistribution?.high ?? 0, color: '#f97316' },
    { name: 'Critical', value: dashboard.riskDistribution?.critical ?? 0, color: '#ef4444' },
  ];

  const formatCurrency = (value: number) => {
    if (value >= 100) {
      return `₹${(value / 100).toFixed(1)} Lakh Cr`;
    }
    return `₹${value.toFixed(1)} Cr`;
  };

  const secondaryKpis = [
    { title: 'Portfolio Value', value: formatCurrency(dashboard.portfolioValue ?? 0), subtitle: 'Original approved cost', icon: <TrendingUp className="h-5 w-5 text-blue-600" /> },
    { title: 'Revised Value', value: formatCurrency(dashboard.revisedValue ?? 0), subtitle: 'Current revised cost', icon: <BarChart3 className="h-5 w-5 text-blue-600" /> },
  ];

  return (
    <div className="min-w-0">
<div className="mb-6 inline-block rounded-xl bg-white px-6 py-3 shadow-md">
        <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">
          Infrastructure Risk Overview
        </h1>
        <p className="mt-1 text-sm text-gray-600 lg:text-base">
          Predictive intelligence for India's infrastructure project portfolio
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          title="Total Projects"
          value={String(dashboard.totalProjects ?? 0)}
          subtitle="Currently monitored"
          icon={<FolderOpen className="h-5 w-5 text-blue-600" />}
        />
        <KpiCard
          title="High Risk Projects"
          value={String(dashboard.highRiskProjects ?? 0)}
          subtitle="Require attention"
          icon={<AlertTriangle className="h-5 w-5 text-red-600" />}
          trend={{ value: 4.2, isPositive: false }}
        />
        <KpiCard
          title="Schedule Risk"
          value={String(dashboard.scheduleRiskCount ?? 0)}
          subtitle="Projects showing delay signals"
          icon={<Clock className="h-5 w-5 text-orange-600" />}
        />
        <KpiCard
          title="Cost Risk"
          value={String(dashboard.costRiskCount ?? 0)}
          subtitle="Projects showing escalation signals"
          icon={<DollarSign className="h-5 w-5 text-yellow-600" />}
        />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:max-w-2xl">
        {secondaryKpis.map((kpi) => (
          <div
            key={kpi.title}
            className="flex items-center justify-between rounded-xl border border-gray-200 bg-gradient-to-r from-navy-50 to-white px-5 py-4"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-500">{kpi.title}</p>
              <p className="mt-1 text-lg font-bold tracking-tight text-navy-900 lg:text-xl">{kpi.value}</p>
              <p className="mt-0.5 text-xs text-gray-400">{kpi.subtitle}</p>
            </div>
            <div className="shrink-0 rounded-lg bg-white p-2.5 ring-1 ring-inset ring-navy-100">
              {kpi.icon}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-4 lg:px-6">
          <div>
            <h3 className="text-base font-semibold text-navy-900 lg:text-lg">
              Projects Requiring Immediate Attention
            </h3>
            <p className="mt-0.5 text-xs text-gray-500 lg:text-sm">
              Projects with elevated probability of cost escalation, schedule delay, or implementation risk.
            </p>
          </div>
          <button
            onClick={() => navigate('/projects')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3.5 py-2 text-sm font-medium text-navy-900 transition-colors hover:bg-gray-50 hover:text-blue-700"
          >
            View all projects
            <ArrowRight size={14} />
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
                <th className="px-4 py-3 font-semibold lg:px-6">Project</th>
                <th className="px-4 py-3 font-semibold">Ministry</th>
                <th className="px-4 py-3 font-semibold">Sector</th>
                <th className="px-4 py-3 font-semibold">State</th>
                <th className="px-4 py-3 font-semibold">Progress</th>
                <th className="px-4 py-3 font-semibold">Cost Overrun</th>
                <th className="px-4 py-3 font-semibold">Delay Probability</th>
                <th className="px-4 py-3 font-semibold">Risk Score</th>
                <th className="px-4 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {highRiskProjects.map((project: any) => {
                const costOverrun = ((project.currentCost - project.originalCost) / project.originalCost) * 100;
                return (
                  <tr
                    key={project.id}
                    className="cursor-pointer transition-colors hover:bg-blue-50/40"
                    onClick={() => navigate(`/projects/${project.id}`)}
                  >
                    <td className="max-w-[240px] px-4 py-3 lg:px-6">
                      <div className="truncate font-medium text-navy-900" title={project.name}>
                        {project.name}
                      </div>
                      <div className="text-xs text-gray-400">{project.id}</div>
                    </td>
                    <td className="max-w-[180px] truncate px-4 py-3 text-gray-600" title={project.ministry}>
                      {project.ministry}
                    </td>
                    <td className="px-4 py-3 text-gray-700">{project.sector}</td>
                    <td className="px-4 py-3 text-gray-700">{project.state}</td>
                    <td className="min-w-[110px] px-4 py-3">
                      <ProgressBar value={project.physicalProgress} showLabel />
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-sm font-semibold ${getCostOverrunColor(costOverrun)}`}>
                        {costOverrun.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-sm font-semibold ${getDelayColor(project.delayProbability)}`}>
                        {project.delayProbability}%
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <RiskScore score={project.riskScore} size="sm" />
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge level={project.riskLevel} size="sm" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RiskChart
          title="Portfolio Risk Distribution"
          description="Share of monitored projects by current risk level."
          data={riskDistribution}
        />
        <RiskTrendChart
          title="Portfolio Risk Trend"
          description="Monthly risk classification over the last six months."
          data={analytics?.riskTrends ?? []}
          filters={sectorFilters}
          activeFilter={activeSector}
          onFilterChange={setActiveSector}
        />
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-white px-6 py-3 shadow-md">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-navy-900">Dive deeper into portfolio analytics</p>
          <p className="mt-0.5 text-xs text-gray-600 lg:text-sm">
            Sector comparisons, cost overrun drivers, delay analysis, and ministry-wise risk rankings.
          </p>
        </div>
        <button
          onClick={() => navigate('/analytics')}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-navy-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-navy-800"
        >
          Open Analytics
          <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}
