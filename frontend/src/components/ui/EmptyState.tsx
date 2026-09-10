import React from 'react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
}

export function EmptyState({ title, description, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center py-12">
      {icon && <div className="mb-4 text-gray-300">{icon}</div>}
      <p className="text-lg font-medium text-gray-500">{title}</p>
      <p className="text-sm text-gray-400">{description}</p>
    </div>
  );
}
