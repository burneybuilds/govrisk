import React from 'react';

interface LoadingStateProps {
  text?: string;
}

export function LoadingState({ text }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center py-12">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-blue-600" />
      {text && <p className="mt-3 text-sm text-gray-500">{text}</p>}
    </div>
  );
}
