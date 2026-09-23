import React from 'react';

const filters = [
  { value: 'all', label: 'Todo' },
  { value: 'PENDIENTE', label: 'Pendiente' },
  { value: 'CONFIRMADA', label: 'Confirmada' },
  { value: 'REAGENDADA', label: 'Reagendada' },
  { value: 'COMPLETADA', label: 'Atendida' },
  { value: 'SUSPENDIDA', label: 'Suspendida' },
  { value: 'CANCELADA', label: 'Cancelada' },
];

const filterColors: Record<string, string> = {
  all: 'bg-slate-100 text-slate-700 hover:bg-slate-200',
  PENDIENTE: 'bg-amber-100 text-amber-700 hover:bg-amber-200 border-amber-300',
  CONFIRMADA: 'bg-blue-100 text-blue-700 hover:bg-blue-200 border-blue-300',
  REAGENDADA: 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200 border-indigo-300',
  COMPLETADA: 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200 border-emerald-300',
  SUSPENDIDA: 'bg-slate-200 text-slate-700 hover:bg-slate-300 border-slate-400',
  CANCELADA: 'bg-red-100 text-red-700 hover:bg-red-200 border-red-300',
};

interface FilterButtonsProps {
  activeFilter: string;
  onFilterChange: (filter: string) => void;
}

export const FilterButtons: React.FC<FilterButtonsProps> = ({ activeFilter, onFilterChange }) => {
  return (
    <div className="flex flex-wrap gap-2">
      {filters.map((filter) => (
        <button
          key={filter.value}
          onClick={() => onFilterChange(filter.value)}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
            activeFilter === filter.value
              ? filterColors[filter.value].replace('hover:', '').replace('hover:', '') + ' border-2'
              : filterColors[filter.value] + ' border'
          }`}
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
};

export default FilterButtons;