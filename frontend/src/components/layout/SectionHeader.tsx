import { ReactNode } from 'react';
import { Badge } from '@/components/ui/badge';

interface SectionHeaderProps {
  title: string;
  badge?: string;
  secondaryAction?: ReactNode;
}

export function SectionHeader({ title, badge, secondaryAction }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold">{title}</h2>
        {badge && <Badge>{badge}</Badge>}
      </div>
      {secondaryAction}
    </div>
  );
}
