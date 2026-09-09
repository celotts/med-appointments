import React from 'react';
import { Pencil, Trash2 } from 'lucide-react';

interface Column<T> {
  header: string;
  accessor: keyof T | ((item: T) => React.ReactNode);
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onEdit?: (item: T) => void;
  onDelete?: (item: T) => void;
}

const DataTable = <T extends { id: any }>({
  data,
  columns,
  onEdit,
  onDelete,
}: DataTableProps<T>) => {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 shadow-sm">
      <table className="w-full text-left border-collapse">
        <thead className="bg-slate-50 text-medical-textMuted text-xs uppercase tracking-wider">
          <tr>
            {columns.map((col, idx) => (
              <th key={idx} className="px-6 py-3.5 font-semibold border-b border-slate-200">
                {col.header}
              </th>
            ))}
            {(onEdit || onDelete) && (
              <th className="px-6 py-3.5 font-semibold border-b border-slate-200 text-right w-24">
                Acciones
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
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
            data.map((item, idx) => (
              <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                {columns.map((col, colIdx) => (
                  <td key={colIdx} className="px-6 py-4 text-sm text-medical-textMain">
                    {typeof col.accessor === 'function'
                      ? col.accessor(item)
                      : (item[col.accessor] as React.ReactNode)}
                  </td>
                ))}
                {(onEdit || onDelete) && (
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {onEdit && (
                        <button
                          onClick={() => onEdit(item)}
                          className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Editar"
                        >
                          <Pencil size={15} />
                        </button>
                      )}
                      {onDelete && (
                        <button
                          onClick={() => onDelete(item)}
                          className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Eliminar"
                        >
                          <Trash2 size={15} />
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
      {data.length > 0 && (
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 text-xs text-medical-textMuted">
          {data.length} registro{data.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
};

export default DataTable;
