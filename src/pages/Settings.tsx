import { useState } from 'react';
import { Bell, Monitor, User } from 'lucide-react';

export default function Settings() {
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [dailySummary, setDailySummary] = useState(true);
  const [weeklyReport, setWeeklyReport] = useState(false);
  const [defaultView, setDefaultView] = useState('grid');
  const [perPage, setPerPage] = useState('10');

  return (
    <div className="mx-auto min-w-0 max-w-[800px]">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">Settings</h1>
        <p className="mt-1 text-sm text-gray-500 lg:text-base">Application preferences and configuration</p>
      </div>

      <div className="space-y-6">
        <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
          <div className="mb-4 flex items-center gap-3 border-b border-gray-100 pb-4">
            <span className="rounded-lg bg-blue-50 p-2">
              <Bell className="h-5 w-5 text-blue-600" />
            </span>
            <h2 className="text-base font-semibold text-navy-900 lg:text-lg">Notification Preferences</h2>
          </div>
          <div className="space-y-4">
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-700">Email alerts for critical risks</span>
              <input
                type="checkbox"
                checked={emailAlerts}
                onChange={(e) => setEmailAlerts(e.target.checked)}
                className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-700">Daily portfolio summary</span>
              <input
                type="checkbox"
                checked={dailySummary}
                onChange={(e) => setDailySummary(e.target.checked)}
                className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-700">Weekly report generation</span>
              <input
                type="checkbox"
                checked={weeklyReport}
                onChange={(e) => setWeeklyReport(e.target.checked)}
                className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </label>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
          <div className="mb-4 flex items-center gap-3 border-b border-gray-100 pb-4">
            <span className="rounded-lg bg-blue-50 p-2">
              <Monitor className="h-5 w-5 text-blue-600" />
            </span>
            <h2 className="text-base font-semibold text-navy-900 lg:text-lg">Display Settings</h2>
          </div>
          <div className="space-y-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Default risk view</label>
              <select
                value={defaultView}
                onChange={(e) => setDefaultView(e.target.value)}
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="grid">Grid</option>
                <option value="table">Table</option>
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Projects per page</label>
              <select
                value={perPage}
                onChange={(e) => setPerPage(e.target.value)}
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
              </select>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
          <div className="mb-4 flex items-center gap-3 border-b border-gray-100 pb-4">
            <span className="rounded-lg bg-blue-50 p-2">
              <User className="h-5 w-5 text-blue-600" />
            </span>
            <h2 className="text-base font-semibold text-navy-900 lg:text-lg">Profile</h2>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Name</span>
              <span className="text-sm font-medium text-navy-900">Admin User</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Role</span>
              <span className="text-sm font-medium text-navy-900">System Administrator</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Email</span>
              <span className="text-sm font-medium text-navy-900">admin@govrisk.gov.in</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
