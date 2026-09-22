import React, { useState, useMemo, useEffect } from 'react';

export interface Column<T> {
  header: string;
  accessor: keyof T | ((item: T) => React.ReactNode);
  sortable?: boolean;
  type?: 'string' | 'number' | 'date' | 'boolean';
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onEdit?: (item: T) => void;
  onDelete?: (item: T) => void;
  pageSize?: number;
  defaultSortKey?: keyof T | string;
  defaultSortDirection?: 'asc' | 'desc';
}

const escapeHtml = (unsafe: string | null | undefined) => {
  if (unsafe == null) return '';
  return unsafe
    .toString()
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>')
    .replace(/"/g, '"')
    .replace(/'/g, '&#039;');
};

const compareValues = <T,>(aVal: T, bVal: T, type: string = 'string'): number => {
  if (aVal === null || aVal === undefined) return 1;
  if (bVal === null || bVal === undefined) return -1;

  switch (type) {
    case 'number':
      return Number(aVal) - Number(bVal);
    case 'date':
      return new Date(aVal as string).getTime() - new Date(bVal as string).getTime();
    case 'boolean':
      return (aVal === bVal ? 0 : aVal ? 1 : -1) as unknown as number;
    case 'string':
    default:
      return String(aVal).localeCompare(String(bVal));
  }
};

const DataTable = <T extends { id: any }>({
  data,
  columns,
  onEdit,
  onDelete,
  pageSize: initialPageSize = 20,
  defaultSortKey = 'start_datetime',
  defaultSortDirection = 'desc',
}: DataTableProps<T>) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [sortKey, setSortKey] = useState<keyof T | string>(defaultSortKey);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>(defaultSortDirection);

  const sortedAndPaginatedData = useMemo(() => {
    let sortedData = [...data];

    if (sortKey) {
      const column = columns.find(c => c.accessor === sortKey);
      const type = column?.type || 'string';

      sortedData.sort((a, b) => {
        const aVal = a[sortKey as keyof T];
        const bVal = b[sortKey as keyof T];
        const comparison = compareValues(aVal, bVal, type);
        return sortDirection === 'asc' ? comparison : -comparison;
      });
    }

    const start = (currentPage - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [data, currentPage, pageSize, sortKey, sortDirection, columns]);

  const totalPages = Math.ceil(data.length / pageSize) || 1;

  useEffect(() => {
    setCurrentPage(1);
  }, [pageSize, data.length]);

  const handleSort = (key: keyof T | string) => {
    if (sortKey === key) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  const handlePageSizeChange = (newPageSize: number) => {
    const validSize = Math.max(1, Math.min(newPageSize, data.length || 1000));
    setPageSize(validSize);
    setCurrentPage(1);
  };

  const goToPage = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  };

  const handlePageSizeInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value > 0) {
      handlePageSizeChange(value);
    }
  };

  const getSortIcon = (columnAccessor: keyof T | ((item: T) => React.ReactNode)) => {
    if (typeof columnAccessor === 'function') return null;
    if (sortKey !== columnAccessor) {
      return <svg className="w-3 h-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16l-4-4 4-4M3 8l4 4 4-4M3 16l4-4 4 4" /></svg>;
    }
    return sortDirection === 'asc' 
      ? <svg className="w-3 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7-7" /></svg>
      : <svg className="w-3 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 5l-7 7-7 7" /></svg>;
  };

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 shadow-sm">
      <div className="overflow-x-auto overflow-y-auto" style={{ maxHeight: '600px' }}>
        <table className="w-full text-left border-collapse min-w-full">
          <thead className="bg-white text-medical-textMuted text-xs uppercase tracking-wider sticky top-0 z-[100] shadow-lg" style={{ backgroundColor: '#ffffff', position: 'sticky', top: 0 }}>
            <tr className="bg-white" style={{ backgroundColor: '#ffffff' }}>
              {columns.map((col, idx) => (
                <th 
                  key={idx} 
                  className="px-4 py-3 font-semibold border-b-2 border-slate-200 sticky top-0 bg-white z-[90] cursor-pointer hover:bg-slate-50 select-none"
                  onClick={() => col.sortable !== false && handleSort(col.accessor as string)}
                  style={{ userSelect: 'none', backgroundColor: '#ffffff' }}
                >
                  <div className="flex items-center gap-1">
                    <span>{col.header}</span>
                    {col.sortable !== false && typeof col.accessor !== 'function' && (
                      <span className="ml-1 inline-flex">{getSortIcon(col.accessor)}</span>
                    )}
                  </div>
                </th>
              ))}
              {(onEdit || onDelete) && (
                <th className="px-4 py-3 font-semibold border-b-2 border-slate-200 text-right w-24 sticky right-0 bg-white z-[90]" style={{ backgroundColor: '#ffffff' }}>
                  Acciones
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white" style={{ position: 'relative', zIndex: 0, backgroundColor: '#ffffff' }}>
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + (onEdit || onDelete ? 1 : 0)}
                  className="px-6 py-12 text-center text-slate-400"
                >
                  <div className="flex flex-col items-center gap-2">
                    <p className="text-sm">No se encontraron registros</p>
                  </div>
                </td>
              </tr>
            ) : (
              sortedAndPaginatedData.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/50 transition-colors bg-white">
                  {columns.map((col, colIdx) => (
                    <td key={colIdx} className="px-4 py-3 text-sm text-medical-textMain">
                      {typeof col.accessor === 'function'
                        ? col.accessor(item)
                        : escapeHtml((item as any)[col.accessor as string] as string)}
                    </td>
                  ))}
                  {(onEdit || onDelete) && (
                    <td className="px-4 py-3 text-right sticky right-0 bg-white z-10">
                      <div className="flex items-center justify-end gap-1">
                        {onEdit && (
                          <button
                            onClick={() => onEdit?.(item)}
                            className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title="Editar"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                          </button>
                        )}
                        {onDelete && (
                          <button
                            onClick={() => onDelete?.(item)}
                            className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Eliminar"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5.034 7H19z" /></svg>
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <label className="text-sm text-slate-600">Cant Reg:</label>
            <input
              type="number"
              value={pageSize}
              onChange={handlePageSizeInput}
              onBlur={(e) => handlePageSizeChange(parseInt(e.target.value, 10) || initialPageSize)}
              min={1}
              max={999}
              className="w-20 px-2 py-1 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-colors text-center"
              aria-label="Registros por página"
            />
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => goToPage(1)}
              disabled={currentPage === 1}
              className="px-2 py-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-colors font-bold"
              title="Primera"
              aria-label="Primera página"
            >
              {'<<'}
            </button>

            <button
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-2 py-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-colors font-bold"
              title="Anterior"
              aria-label="Página anterior"
            >
              {'<'}
            </button>

            <div className="flex items-center gap-1 mx-1">
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                let pageNum: number;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (currentPage <= 3) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = currentPage - 2 + i;
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => goToPage(pageNum)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                      currentPage === pageNum
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    aria-current={currentPage === pageNum ? 'page' : undefined}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => goToPage(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-2 py-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-colors font-bold"
              title="Siguiente"
              aria-label="Página siguiente"
            >
              {'>'}
            </button>

            <button
              onClick={() => goToPage(totalPages)}
              disabled={currentPage === totalPages}
              className="px-2 py-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-colors font-bold"
              title="Último"
              aria-label="Última página"
            >
              {'>>'}
            </button>
          </div>

<div className="text-sm text-slate-500">
            Página {currentPage} de {totalPages} · Total: {data.length} registros
          </div>
        </div>
      </div>
  );
};

export default DataTable;