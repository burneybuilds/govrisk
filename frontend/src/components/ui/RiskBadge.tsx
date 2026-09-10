import React from 'react';

interface RiskBadgeProps {
  level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  size?: 'sm' | 'md';
}

const colorMap = {
  LOW: 'bg-green-50 text-green-700',
  MEDIUM: 'bg-yellow-50 text-yellow-700',
  HIGH: 'bg-orange-50 text-orange-700',
  CRITICAL: 'bg-red-50 text-red-700',
};

const sizeMap = {
  sm: 'px-2.5 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
};

export function RiskBadge({ level, size = 'md' }: RiskBadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full font-medium ${colorMap[level]} ${sizeMap[size]}`}>
      {level}
    </span>
  );
}
