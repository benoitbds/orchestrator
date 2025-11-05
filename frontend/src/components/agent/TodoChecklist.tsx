"use client";
import { TodoItem } from '@/hooks/useLangGraphStream';
import { cn } from '@/lib/utils';
import dynamic from 'next/dynamic';

const Square = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Square })),
  { ssr: false }
);
const CheckSquare = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.CheckSquare })),
  { ssr: false }
);
const Loader2 = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Loader2 })),
  { ssr: false }
);

interface TodoChecklistProps {
  todos: TodoItem[];
}

export function TodoChecklist({ todos }: TodoChecklistProps) {
  if (todos.length === 0) return null;

  return (
    <div className="space-y-1">
      <div className="flex items-start gap-2 text-sm">
        <span className="text-blue-500 mt-0.5">●</span>
        <span className="font-medium">Update Todos</span>
      </div>
      <div className="pl-6 space-y-1">
        <div className="flex items-start gap-1 text-sm text-muted-foreground">
          <span className="select-none">⎿</span>
          <div className="flex-1 space-y-1">
            {todos.map((todo) => (
              <div 
                key={todo.id} 
                className={cn(
                  "flex items-start gap-2 transition-all duration-300",
                  todo.status === 'completed' && "text-green-600 dark:text-green-400"
                )}
              >
                {todo.status === 'completed' ? (
                  <CheckSquare className="h-4 w-4 mt-0.5 flex-shrink-0 animate-in zoom-in duration-300" />
                ) : todo.status === 'in_progress' ? (
                  <Loader2 className="h-4 w-4 mt-0.5 flex-shrink-0 animate-spin text-blue-500" />
                ) : (
                  <Square className="h-4 w-4 mt-0.5 flex-shrink-0" />
                )}
                <span className={cn(
                  "flex-1",
                  todo.status === 'completed' && "line-through"
                )}>
                  {todo.text}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
