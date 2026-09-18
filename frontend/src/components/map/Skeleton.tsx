import type { HTMLAttributes } from 'react';

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  className?: string;
}

/** Shimmer placeholder bar (see leaflet-overrides.css for the keyframes). */
export function Skeleton({ className = '', ...rest }: SkeletonProps) {
  return <div className={`gm-skeleton ${className}`} aria-hidden="true" {...rest} />;
}
