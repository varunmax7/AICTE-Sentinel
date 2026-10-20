import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
}

/**
 * Minimal generic table. The spec (§3) names TanStack Table for the real
 * queue/report screens — those arrive with sorting, pagination and column
 * filters in Phase P2 (queue) and P9 (reports); nothing in Phase P1 needs
 * that yet, so this stays a plain `<table>` until a consumer does.
 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  emptyLabel = "No data.",
  className,
}: {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyLabel?: string;
  className?: string;
}) {
  return (
    <div className={cn("overflow-x-auto rounded-xl border border-border", className)}>
      <table className="w-full text-sm">
        <thead className="bg-surface-2 text-left text-xs font-medium uppercase tracking-wide text-muted">
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={cn("px-4 py-2.5", col.className)}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border bg-surface">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-muted">
                {emptyLabel}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={rowKey(row)} className="hover:bg-surface-2">
                {columns.map((col) => (
                  <td key={col.key} className={cn("px-4 py-2.5 text-text", col.className)}>
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
