import { useState } from 'react';
import { mockAlerts } from '../data/alerts';
import { AlertCard } from '../components/alerts/AlertCard';
import { EmptyState } from '../components/ui/EmptyState';
import { BellOff } from 'lucide-react';

const tabs = ['All', 'Critical', 'High', 'Medium', 'Resolved'] as const;

type Tab = (typeof tabs)[number];

const tabCounts: Record<Tab, number> = {
  All: mockAlerts.length,
  Critical: mockAlerts.filter((a) => a.severity === 'CRITICAL').length,
  High: mockAlerts.filter((a) => a.severity === 'HIGH').length,
  Medium: mockAlerts.filter((a) => a.severity === 'MEDIUM').length,
  Resolved: mockAlerts.filter((a) => a.severity === 'RESOLVED').length,
};

export default function Alerts() {
  const [activeTab, setActiveTab] = useState<Tab>('All');

  const filteredAlerts =
    activeTab === 'All'
      ? mockAlerts
      : mockAlerts.filter((alert) => alert.severity === activeTab.toUpperCase());

  return (
    <div className="mx-auto min-w-0 max-w-[1100px]">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">
          Early Warning Center
        </h1>
        <p className="mt-1 text-sm text-gray-500 lg:text-base">
          Potential project risks detected by GovRisk
        </p>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-navy-900 text-white'
                : 'border border-gray-200 bg-white text-gray-600 hover:border-navy-300 hover:text-navy-900'
            }`}
          >
            {tab}
            <span className={`ml-2 rounded-full px-1.5 text-xs ${activeTab === tab ? 'bg-white/20' : 'bg-gray-100 text-gray-500'}`}>
              {tabCounts[tab]}
            </span>
          </button>
        ))}
      </div>

      <p className="mb-4 text-sm text-gray-500">Showing {filteredAlerts.length} alerts</p>

      {filteredAlerts.length === 0 ? (
        <EmptyState
          title="No alerts in this category"
          description="There are currently no alerts matching this filter."
          icon={<BellOff size={40} />}
        />
      ) : (
        <div className="space-y-4">
          {filteredAlerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}