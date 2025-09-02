import { ReactNode } from 'react';
import { Button } from '@/components/ui/button';

interface Action {
  label: string;
  onClick: () => void;
}

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  subtitle?: string;
  primaryAction: Action;
  secondaryAction?: Action;
}

export function EmptyState({ icon, title, subtitle, primaryAction, secondaryAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center p-6">
      {icon && <div className="mb-4 text-muted-foreground">{icon}</div>}
      <h3 className="mb-2 text-lg font-medium">{title}</h3>
      {subtitle && <p className="mb-4 text-sm text-muted-foreground">{subtitle}</p>}
      <div className="flex gap-2">
        <Button onClick={primaryAction.onClick}>{primaryAction.label}</Button>
        {secondaryAction && (
          <Button variant="ghost" onClick={secondaryAction.onClick}>
            {secondaryAction.label}
          </Button>
        )}
      </div>
    </div>
  );
}
