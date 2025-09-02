import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState } from 'react';
import type { Step } from '@/types/history';

export type Filters = {
  status: 'all' | Step['status'];
  kind: 'all' | Step['kind'];
  time: '15m' | '1h' | '24h';
  group: 'run' | 'tool';
};

export function RightFiltersDrawer({ onChange }: { onChange: (f: Filters) => void }) {
  const [filters, setFilters] = useState<Filters>({ status: 'all', kind: 'all', time: '1h', group: 'run' });
  function update<K extends keyof Filters>(k: K, v: Filters[K]) {
    const next = { ...filters, [k]: v };
    setFilters(next);
    onChange(next);
  }
  return (
    <aside className="hidden w-60 flex-shrink-0 md:block">
      <div className="rounded-2xl border bg-white p-4 shadow-sm">
        <div className="mb-4 text-sm font-semibold">Filters</div>
        <div className="mb-3 text-sm">
          <div className="mb-1">Status</div>
          <Select value={filters.status} onValueChange={(v) => update('status', v as Filters['status'])}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="timeout">Timeout</SelectItem>
              <SelectItem value="running">Running</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="mb-3 text-sm">
          <div className="mb-1">Kind</div>
          <Select value={filters.kind} onValueChange={(v) => update('kind', v as Filters['kind'])}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="LLM">LLM</SelectItem>
              <SelectItem value="Tool">Tool</SelectItem>
              <SelectItem value="DB">DB</SelectItem>
              <SelectItem value="System">System</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="mb-3 text-sm">
          <div className="mb-1">Time</div>
          <Select value={filters.time} onValueChange={(v) => update('time', v as Filters['time'])}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="15m">Last 15m</SelectItem>
              <SelectItem value="1h">Last 1h</SelectItem>
              <SelectItem value="24h">Last 24h</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="text-sm">
          <div className="mb-1">Group by</div>
          <Select value={filters.group} onValueChange={(v) => update('group', v as Filters['group'])}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="run">Run</SelectItem>
              <SelectItem value="tool">Tool</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </aside>
  );
}
