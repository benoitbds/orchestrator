import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export const Accordion = ({ children }: { children: React.ReactNode }) => <div>{children}</div>;

export const AccordionItem = ({ children }: { value: string; children: React.ReactNode }) => <div>{children}</div>;

export const AccordionTrigger = ({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) => (
  <button
    type="button"
    onClick={onClick}
    className={cn('flex w-full items-center justify-between py-2 font-medium')}
  >
    {children}
    <ChevronDown className="h-4 w-4" />
  </button>
);

export const AccordionContent = ({ open, children }: { open: boolean; children: React.ReactNode }) => (
  open ? <div className="overflow-hidden text-sm"><div className="pb-4 pt-0">{children}</div></div> : null
);
