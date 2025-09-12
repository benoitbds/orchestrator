"use client";

import { useState, useRef, KeyboardEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { apiFetch } from '@/lib/api';

interface ChatComposerProps {
  onSend: (objective: string, runId?: string) => void | Promise<void>;
  isSending?: boolean;
  projectId?: number;
  disabled?: boolean;
}

export function ChatComposer({ onSend, isSending = false, projectId, disabled }: ChatComposerProps) {
  const [objective, setObjective] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async () => {
    const trimmedObjective = objective.trim();
    
    if (!trimmedObjective) {
      toast.error('Please enter an objective');
      textareaRef.current?.focus();
      return;
    }

    if (!projectId) {
      toast.error('Please select a project first');
      return;
    }

    setIsSubmitting(true);

    try {
      // Check if onSend handles the API call itself (new interface)
      const result = onSend(trimmedObjective);
      
      // If it returns a promise, wait for it
      if (result && typeof result.then === 'function') {
        await result;
      } else {
        // Old interface - make API call ourselves
        const response = await apiFetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            objective: trimmedObjective, 
            project_id: projectId 
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || 'Failed to start chat');
        }

        const { run_id } = await response.json();
        
        if (!run_id) {
          throw new Error('No run ID received');
        }

        // For backward compatibility, call onSend with runId
        if (typeof onSend === 'function') {
          onSend(trimmedObjective, run_id);
        }
      }

      setObjective('');
      
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to send message');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isSending && !isSubmitting && !disabled) {
        handleSubmit();
      }
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setObjective(e.target.value);
    
    // Auto-grow functionality
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  };

  const isDisabled = isSending || isSubmitting || disabled || !projectId;

  return (
    <div className="border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container max-w-4xl mx-auto p-4">
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Textarea
              ref={textareaRef}
              value={objective}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              placeholder={projectId ? "Ask me to analyze, create, or manage your backlog items..." : "Select a project to start chatting"}
              disabled={isDisabled}
              className="min-h-[44px] max-h-[200px] resize-none"
              aria-label="Chat message"
            />
            <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
              <span>Press Enter to send, Shift+Enter for new line</span>
              <span>{objective.length}/1000</span>
            </div>
          </div>
          
          <Button
            onClick={handleSubmit}
            disabled={isDisabled || !objective.trim()}
            size="lg"
            className="shrink-0"
            aria-label="Send message"
          >
            {(isSending || isSubmitting) ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}