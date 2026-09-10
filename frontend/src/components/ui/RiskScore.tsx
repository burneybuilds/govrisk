import React from 'react';

interface RiskScoreProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
}

const sizeClasses = {
  sm: 'h-11 w-11 text-sm',
  md: 'h-16 w-16 text-lg',
  lg: 'h-24 w-24 text-2xl',
};

function getScoreColor(score: number) {
  if (score <= 30) return 'border-green-500 text-green-700 bg-green-50';
  if (score <= 60) return 'border-yellow-500 text-yellow-700 bg-yellow-50';
  if (score <= 80) return 'border-orange-500 text-orange-700 bg-orange-50';
  return 'border-red-500 text-red-700 bg-red-50';
}

export function RiskScore({ score, size = 'md' }: RiskScoreProps) {
  return (
    <div
      className={`flex items-center justify-center rounded-full border-[3px] font-bold leading-none ${sizeClasses[size]} ${getScoreColor(score)}`}
      title={`Risk score: ${score}`}
    >
      <span>{score}</span>
    </div>
  );
}