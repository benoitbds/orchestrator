"use client";

import { useState, useRef } from 'react';
import { Send, Loader2, Paperclip, Mic, MicOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { AutocompleteInput } from './AutocompleteInput';
import { cn } from '@/lib/utils';
import { resolveShortRefs, extractIntentMetadata, type AgentRunPayload } from '@/lib/api';
import { toast } from 'sonner';

interface ChatComposerProps {
  onSendMessage: (message: string, meta?: AgentRunPayload['meta']) => Promise<void>;
  isLoading?: boolean;
  disabled?: boolean;
  projectId?: number;
  placeholder?: string;
  className?: string;
  showAttachments?: boolean;
  showVoice?: boolean;
}

export function ChatComposer({
  onSendMessage,
  isLoading = false,
  disabled = false,
  projectId,
  placeholder = "Ask about your backlog... (type / to reference items)",
  className,
  showAttachments = false,
  showVoice = false
}: ChatComposerProps) {
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const composerRef = useRef<HTMLDivElement>(null);

  const handleSubmit = async () => {
    if (!message.trim() || isLoading || disabled) return;
    
    const messageToSend = message.trim();
    setMessage('');
    
    try {
      if (!projectId) {
        throw new Error('No project selected');
      }
      
      const { text: resolved, references } = await resolveShortRefs(messageToSend, projectId);
      const metadata = extractIntentMetadata(messageToSend, references);
      
      if (metadata) {
        console.log('Extracted metadata:', metadata);
      }
      
      await onSendMessage(resolved, metadata || undefined);
    } catch (error) {
      setMessage(messageToSend);
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      toast.error(errorMessage);
      console.error('Failed to send message:', error);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Handle Ctrl/Cmd + Enter for multiline, Enter alone for submit
    if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      // Stop recording
      setIsRecording(false);
      // TODO: Implement voice recording functionality
    } else {
      // Start recording
      setIsRecording(true);
      // TODO: Implement voice recording functionality
    }
  };

  const canSend = message.trim().length > 0 && !isLoading && !disabled;

  return (
    <Card className={cn("p-4", className)} ref={composerRef}>
      <div className="space-y-3">
        {/* Main input area */}
        <div className="flex items-end gap-3">
          {/* Attachments button */}
          {showAttachments && (
            <Button
              variant="ghost"
              size="sm"
              disabled={disabled || isLoading}
              className="flex-shrink-0 h-10 w-10 p-0"
            >
              <Paperclip className="h-4 w-4" />
            </Button>
          )}

          {/* Message input with autocomplete */}
          <div className="flex-1">
            <AutocompleteInput
              value={message}
              onChange={setMessage}
              onSubmit={handleSubmit}
              placeholder={placeholder}
              projectId={projectId}
              disabled={disabled || isLoading}
              className="min-h-[40px] resize-none"
            />
          </div>

          {/* Voice recording button */}
          {showVoice && (
            <Button
              variant={isRecording ? "destructive" : "ghost"}
              size="sm"
              onClick={toggleRecording}
              disabled={disabled || isLoading}
              className="flex-shrink-0 h-10 w-10 p-0"
            >
              {isRecording ? (
                <MicOff className="h-4 w-4" />
              ) : (
                <Mic className="h-4 w-4" />
              )}
            </Button>
          )}

          {/* Send button */}
          <Button
            onClick={handleSubmit}
            disabled={!canSend}
            size="sm"
            className="flex-shrink-0 h-10 w-10 p-0"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Helper text */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span>Type <code className="px-1 py-0.5 bg-muted rounded">/</code> to reference backlog items</span>
            {showVoice && (
              <span>Click <Mic className="h-3 w-3 inline mx-1" /> to use voice input</span>
            )}
          </div>
          <div>
            Press <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Enter</kbd> to send, 
            <kbd className="px-1 py-0.5 bg-muted rounded text-xs ml-1">Shift+Enter</kbd> for new line
          </div>
        </div>

        {/* Recording indicator */}
        {isRecording && (
          <div className="flex items-center gap-2 px-3 py-2 bg-destructive/10 text-destructive rounded-md">
            <div className="w-2 h-2 bg-destructive rounded-full animate-pulse" />
            <span className="text-sm font-medium">Recording... Click to stop</span>
          </div>
        )}
      </div>
    </Card>
  );
}