import React from 'react';

interface FilterBarProps {
  children: React.ReactNode;
}

export function FilterBar({ children }: FilterBarProps) {
  return <div className="flex flex-wrap items-center gap-3">{children}</div>;
}

interface FilterSelectProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}

export function FilterSelect({ label, value, onChange, options }: FilterSelectProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-gray-500">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-w-[150px] rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-navy-900 outline-none transition-colors focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
