import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ReactNode;
  trend?: { value: number; isPositive: boolean };
}

export function KpiCard({ title, value, subtitle, icon, trend }: KpiCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 lg:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-1.5 text-2xl font-bold tracking-tight text-navy-900 lg:text-[26px]">
            {value}
          </p>
          <p className="mt-0.5 truncate text-xs text-gray-400">{subtitle}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <div className="rounded-lg bg-gray-50 p-2.5 ring-1 ring-inset ring-gray-100">{icon}</div>
          {trend && (
            <span
              className={`inline-flex items-center gap-0.5 text-xs font-semibold ${
                trend.isPositive ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {trend.isPositive ? (
                <TrendingUp className="h-3.5 w-3.5" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5" />
              )}
              {trend.value}%
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
