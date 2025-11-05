import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export const Accordion = ({ children }: { children: React.ReactNode }) => <div>{children}</div>;

export const AccordionItem = ({ children }: { value: string; children: React.ReactNode }) => <div className="mb-6">{children}</div>;

export const AccordionTrigger = ({ children, onClick, open }: { children: React.ReactNode; onClick?: () => void; open?: boolean }) => (
  <button
    type="button"
    onClick={onClick}
    className={cn('flex w-full items-center justify-between py-2 font-semibold text-sm hover:text-primary transition-colors')}
  >
    {children}
    {open ? <ChevronDown className="h-4 w-4 transition-transform duration-200" /> : <ChevronRight className="h-4 w-4 transition-transform duration-200" />}
  </button>
);

export const AccordionContent = ({ open, children }: { open: boolean; children: React.ReactNode }) => (
  <div className={cn(
    "overflow-hidden transition-all duration-200",
    open ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0"
  )}>
    <div className="pb-4 pt-2">{children}</div>
  </div>
);
