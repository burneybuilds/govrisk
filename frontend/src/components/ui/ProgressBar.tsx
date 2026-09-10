import React from 'react';

interface ProgressBarProps {
  value: number;
  max?: number;
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'gray';
  size?: 'sm' | 'md';
  showLabel?: boolean;
  label?: string;
}

const colorMap = {
  blue: 'bg-blue-600',
  green: 'bg-green-600',
  yellow: 'bg-yellow-500',
  red: 'bg-red-600',
  gray: 'bg-gray-500',
};

const sizeMap = {
  sm: 'h-2',
  md: 'h-3',
};

export function ProgressBar({
  value,
  max = 100,
  color = 'blue',
  size = 'sm',
  showLabel = false,
  label,
}: ProgressBarProps) {
  const percentage = Math.min(Math.round((value / max) * 100), 100);

  return (
    <div className="flex items-center gap-3">
      <div className={`w-full overflow-hidden rounded-full bg-gray-200 ${sizeMap[size]}`}>
        <div
          className={`transition-all duration-500 ${colorMap[color]} ${sizeMap[size]} rounded-full`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-sm font-medium text-gray-700 whitespace-nowrap">
          {label ? `${label} ${percentage}%` : `${percentage}%`}
        </span>
      )}
    </div>
  );
}
