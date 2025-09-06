"use client";

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { ConversationHistoryPanel } from './ConversationHistoryPanel';
import { useConversationHistory } from '@/hooks/useConversationHistory';
import { toast } from 'sonner';
import { Send, Loader2 } from 'lucide-react';

export function ConversationDemo() {
  const [objective, setObjective] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { runs, isLoading, error, refresh, startConversation } = useConversationHistory({
    autoRefresh: true,
    refreshInterval: 5000,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!objective.trim() || isSubmitting) return;

    try {
      setIsSubmitting(true);
      await startConversation(objective.trim());
      setObjective('');
      toast.success('Conversation started!');
    } catch (error) {
      toast.error('Failed to start conversation');
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="h-screen flex">
      {/* Left side - Input */}
      <div className="w-1/3 border-r flex flex-col">
        <div className="p-4 border-b">
          <h1 className="text-lg font-semibold">Agent Chat</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Start conversations and see them in compact or debug mode
          </p>
        </div>
        
        <div className="p-4 flex-1">
          <Card className="p-4">
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label htmlFor="objective" className="text-sm font-medium">
                  What would you like to accomplish?
                </label>
                <Input
                  id="objective"
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                  placeholder="e.g., List all features in the project"
                  className="mt-1"
                  disabled={isSubmitting}
                />
              </div>
              
              <Button 
                type="submit" 
                className="w-full" 
                disabled={!objective.trim() || isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Start Conversation
                  </>
                )}
              </Button>
            </form>
          </Card>
          
          {error && (
            <Card className="p-4 mt-4 border-destructive">
              <div className="text-sm text-destructive">
                <strong>Error:</strong> {error}
              </div>
            </Card>
          )}
        </div>
      </div>
      
      {/* Right side - History */}
      <div className="flex-1">
        <ConversationHistoryPanel
          runs={runs}
          isLoading={isLoading}
          onRefresh={refresh}
        />
      </div>
    </div>
  );
}