import React from 'react';
import { Check } from 'lucide-react';

const filters = [
  { value: 'all', label: 'Todo' },
  { value: 'PENDIENTE', label: 'Pendiente' },
  { value: 'CONFIRMADA', label: 'Confirmada' },
  { value: 'REAGENDADA', label: 'Reagendada' },
  { value: 'ATENDIDA', label: 'Atendida' },
  { value: 'SUSPENDIDA', label: 'Suspendida' },
  { value: 'CANCELADA', label: 'Cancelada' },
];

const filterColors: Record<string, { base: string; active: string }> = {
  all: {
    base: 'bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-700 border-slate-200',
    active: 'bg-slate-900 text-white border-slate-900 shadow-[0_0_0_3px_rgb(15_23_42),0_8px_20px_-5px_rgb(15_23_42/_0.4)]',
  },
  PENDIENTE: {
    base: 'bg-white text-amber-700 hover:bg-amber-50 hover:text-amber-800 border-amber-200',
    active: 'bg-amber-600 text-white border-amber-600 shadow-[0_0_0_3px_rgb(217_119_6),0_8px_20px_-5px_rgb(217_119_6/_0.4)]',
  },
  CONFIRMADA: {
    base: 'bg-white text-blue-700 hover:bg-blue-50 hover:text-blue-800 border-blue-200',
    active: 'bg-blue-600 text-white border-blue-600 shadow-[0_0_0_3px_rgb(37_99_235),0_8px_20px_-5px_rgb(37_99_235/_0.4)]',
  },
  REAGENDADA: {
    base: 'bg-white text-indigo-700 hover:bg-indigo-50 hover:text-indigo-800 border-indigo-200',
    active: 'bg-indigo-600 text-white border-indigo-600 shadow-[0_0_0_3px_rgb(79_70_229),0_8px_20px_-5px_rgb(79_70_229/_0.4)]',
  },
  ATENDIDA: {
    base: 'bg-white text-emerald-700 hover:bg-emerald-50 hover:text-emerald-800 border-emerald-200',
    active: 'bg-emerald-600 text-white border-emerald-600 shadow-[0_0_0_3px_rgb(5_150_105),0_8px_20px_-5px_rgb(5_150_105/_0.4)]',
  },
  SUSPENDIDA: {
    base: 'bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-800 border-slate-300',
    active: 'bg-slate-700 text-white border-slate-700 shadow-[0_0_0_3px_rgb(51_65_85),0_8px_20px_-5px_rgb(51_65_85/_0.4)]',
  },
  CANCELADA: {
    base: 'bg-white text-red-700 hover:bg-red-50 hover:text-red-800 border-red-200',
    active: 'bg-red-600 text-white border-red-600 shadow-[0_0_0_3px_rgb(220_38_38),0_8px_20px_-5px_rgb(220_38_38/_0.4)]',
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
              px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300
              border-2
              ${isActive ? colors.active : colors.base}
              ${isActive 
                ? 'scale-105 shadow-xl ring-4 ring-offset-2 ring-offset-white' 
                : 'hover:scale-102 active:scale-98'
              }
              focus-visible:outline-none focus-visible:ring-4
              ${isActive 
                ? 'focus-visible:ring-current focus-visible:ring-opacity-50' 
                : 'focus-visible:ring-slate-300'
              }
            `}
            aria-pressed={isActive}
            aria-current={isActive ? 'true' : undefined}
            style={isActive ? { zIndex: 10 } : undefined}
          >
            <span className="flex items-center gap-2">
              {filter.label}
              {isActive && (
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-white/20 flex items-center justify-center">
                  <Check className="w-3.5 h-3.5" strokeWidth={3.5} />
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
};

export default FilterButtons;