import React from 'react';

interface SkeletonProps {
  className?: string;
  lines?: number;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '', lines = 1 }) => {
  return (
    <div className={`animate-pulse ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-4 bg-slate-200 rounded mb-2 last:mb-0"
          style={{ width: `${85 - i * 15}%` }}
        />
      ))}
    </div>
  );
};

export const TableSkeleton: React.FC<{ rows?: number; cols?: number }> = ({
  rows = 5,
  cols = 4,
}) => {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200">
      <div className="bg-slate-50 px-6 py-4 border-b border-slate-200">
        <div className="flex gap-4">
          {Array.from({ length: cols }).map((_, i) => (
            <div key={i} className="h-4 bg-slate-200 rounded animate-pulse flex-1" />
          ))}
        </div>
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="px-6 py-4 border-b border-slate-100 flex gap-4"
        >
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="h-4 bg-slate-100 rounded animate-pulse flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
};

export const CardSkeleton: React.FC = () => {
  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 animate-pulse">
      <div className="flex items-center gap-4">
        <div className="h-12 w-12 bg-slate-200 rounded-xl" />
        <div className="flex-1">
          <div className="h-4 bg-slate-200 rounded w-24 mb-2" />
          <div className="h-7 bg-slate-200 rounded w-16" />
        </div>
      </div>
    </div>
  );
};
