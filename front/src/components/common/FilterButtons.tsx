import React from 'react';

const filters = [
  { value: 'all', label: 'Todo' },
  { value: 'PENDIENTE', label: 'Pendiente' },
  { value: 'CONFIRMADA', label: 'Confirmada' },
  { value: 'EN ESPERA', label: 'En Espera' },
  { value: 'EN PROCESO', label: 'En Proceso' },
  { value: 'REAGENDADA', label: 'Reagendada' },
  { value: 'ATENDIDA', label: 'Atendida' },
  { value: 'SUSPENDIDA', label: 'Suspendida' },
  { value: 'CANCELADA', label: 'Cancelada' },
];

const filterColors: Record<string, { 
  baseBg: string; baseText: string; baseBorder: string; 
  activeBg: string; activeText: string; activeBorder: string;
  focusRing: string;
}> = {
  all: {
    baseBg: '#FFFFFF', baseText: '#64748B', baseBorder: '#E2E8F0',
    activeBg: '#0F172A', activeText: '#FFFFFF', activeBorder: '#0F172A',
    focusRing: 'focus-visible:ring-slate-400',
  },
  PENDIENTE: {
    baseBg: '#FFFFFF', baseText: '#B45309', baseBorder: '#FDE68A',
    activeBg: '#D97706', activeText: '#FFFFFF', activeBorder: '#D97706',
    focusRing: 'focus-visible:ring-amber-400',
  },
  CONFIRMADA: {
    baseBg: '#FFFFFF', baseText: '#1D4ED8', baseBorder: '#BFDBFE',
    activeBg: '#2563EB', activeText: '#FFFFFF', activeBorder: '#2563EB',
    focusRing: 'focus-visible:ring-blue-400',
  },
  'EN ESPERA': {
    baseBg: '#FFFFFF', baseText: '#7C3AED', baseBorder: '#DDD6FE',
    activeBg: '#8B5CF6', activeText: '#FFFFFF', activeBorder: '#8B5CF6',
    focusRing: 'focus-visible:ring-violet-400',
  },
  'EN PROCESO': {
    baseBg: '#FFFFFF', baseText: '#EA580C', baseBorder: '#FED7AA',
    activeBg: '#EA580C', activeText: '#FFFFFF', activeBorder: '#EA580C',
    focusRing: 'focus-visible:ring-orange-400',
  },
  REAGENDADA: {
    baseBg: '#FFFFFF', baseText: '#4F46E5', baseBorder: '#C7D2FE',
    activeBg: '#4F46E5', activeText: '#FFFFFF', activeBorder: '#4F46E5',
    focusRing: 'focus-visible:ring-indigo-400',
  },
  ATENDIDA: {
    baseBg: '#FFFFFF', baseText: '#059669', baseBorder: '#A7F3D0',
    activeBg: '#059669', activeText: '#FFFFFF', activeBorder: '#059669',
    focusRing: 'focus-visible:ring-emerald-400',
  },
  SUSPENDIDA: {
    baseBg: '#FFFFFF', baseText: '#475569', baseBorder: '#CBD5E1',
    activeBg: '#334155', activeText: '#FFFFFF', activeBorder: '#334155',
    focusRing: 'focus-visible:ring-slate-500',
  },
  CANCELADA: {
    baseBg: '#FFFFFF', baseText: '#DC2626', baseBorder: '#FECACA',
    activeBg: '#DC2626', activeText: '#FFFFFF', activeBorder: '#DC2626',
    focusRing: 'focus-visible:ring-red-400',
  },
};

interface FilterButtonsProps {
  activeFilter: string;
  onFilterChange: (filter: string) => void;
}

export const FilterButtons: React.FC<FilterButtonsProps> = ({ activeFilter, onFilterChange }) => {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filtros de estado de citas">
      {filters.map((filter) => {
        const isActive = activeFilter === filter.value;
        const colors = filterColors[filter.value];

        return (
          <button
            key={filter.value}
            onClick={() => onFilterChange(filter.value)}
            className={`
              relative px-4 py-2 rounded-xl text-sm font-semibold
              transition-colors duration-150 ease-out
              border-2 min-w-[8rem] text-center
              shadow-sm
              focus-visible:outline-none
              focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-slate-400
            `}
            style={{
              backgroundColor: isActive ? colors.activeBg : colors.baseBg,
              color: isActive ? colors.activeText : colors.baseText,
              borderColor: isActive ? colors.activeBorder : colors.baseBorder,
              // Force exact fixed width, variable height
              minWidth: '144px',
              width: '144px',
              minHeight: '44px',
              height: 'auto',
              boxSizing: 'border-box',
            } as React.CSSProperties}
            aria-pressed={isActive}
            aria-current={isActive ? 'true' : undefined}
          >
            <span className="flex items-center justify-center gap-1.5 whitespace-normal break-words">
              {filter.label}
              <span className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center transition-opacity duration-150" style={{ 
                opacity: 1,
                backgroundColor: 'rgba(255,255,255,0.2)',
              }}>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
};

export default FilterButtons;