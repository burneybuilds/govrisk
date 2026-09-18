export function formatCurrency(amount: number): string {
  const formatted = amount.toLocaleString('en-IN');
  return `₹${formatted} Cr`;
}

export function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function getRiskColor(level: string): string {
  switch (level) {
    case 'LOW':
      return 'text-green-600';
    case 'MEDIUM':
      return 'text-yellow-600';
    case 'HIGH':
      return 'text-orange-600';
    case 'CRITICAL':
      return 'text-red-600';
    default:
      return 'text-gray-600';
  }
}

export function getRiskBgColor(level: string): string {
  switch (level) {
    case 'LOW':
      return 'bg-green-100';
    case 'MEDIUM':
      return 'bg-yellow-100';
    case 'HIGH':
      return 'bg-orange-100';
    case 'CRITICAL':
      return 'bg-red-100';
    default:
      return 'bg-gray-100';
  }
}

export function getRiskBorderColor(level: string): string {
  switch (level) {
    case 'LOW':
      return 'border-green-300';
    case 'MEDIUM':
      return 'border-yellow-300';
    case 'HIGH':
      return 'border-orange-300';
    case 'CRITICAL':
      return 'border-red-300';
    default:
      return 'border-gray-300';
  }
}

export function cn(...classes: (string | boolean | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}
