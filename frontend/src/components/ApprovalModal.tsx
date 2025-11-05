import React, { useState } from 'react';
import { apiFetch } from '@/lib/api';

interface WorkflowStep {
  agent: string;
  objective: string;
  status: 'pending' | 'running' | 'done' | 'error' | 'awaiting_approval';
  requires_approval?: boolean;
}

interface ApprovalContext {
  workflow_steps?: WorkflowStep[];
  current_step_index?: number;
  expected_results?: {
    items_count?: number;
    documents_count?: number;
    description?: string;
  };
}

interface Props {
  runId: string;
  stepIndex: number;
  agent: string;
  objective: string;
  createdAt: string;
  timeoutAt: string;
  context?: ApprovalContext;
  projectId?: number;
  onDecision: (decision: 'approve' | 'reject' | 'modify', reason: string) => void;
  onClose?: () => void;
}

const getAutoApproveKey = (projectId: number, agent: string) => 
  `auto_approve_${projectId}_${agent}`;

const getAutoApprovePreference = (projectId: number | undefined, agent: string): boolean => {
  if (!projectId) return false;
  try {
    const stored = localStorage.getItem(getAutoApproveKey(projectId, agent));
    return stored === 'true';
  } catch {
    return false;
  }
};

const setAutoApprovePreference = (projectId: number | undefined, agent: string, value: boolean) => {
  if (!projectId) return;
  try {
    localStorage.setItem(getAutoApproveKey(projectId, agent), value.toString());
  } catch {
    // Ignore localStorage errors
  }
};

export const ApprovalModal: React.FC<Props> = ({
  runId,
  stepIndex,
  agent,
  objective,
  timeoutAt,
  context,
  projectId,
  onDecision,
  onClose
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [approvalStatus, setApprovalStatus] = useState<'idle' | 'approved' | 'rejected' | 'modified'>('idle');
  const [autoApprove, setAutoApprove] = useState(false);
  const [rememberChoice, setRememberChoice] = useState(getAutoApprovePreference(projectId, agent));

  const getAgentIcon = (agent: string) => {
    switch (agent) {
      case 'backlog': return '📋';
      case 'document': return '📄';
      case 'writer': return '✍️';
      case 'planner': return '📊';
      case 'integration': return '🔗';
      default: return '🤖';
    }
  };

  const handleDecision = async (decision: 'approve' | 'reject' | 'modify') => {
    setIsSubmitting(true);
    
    try {
      if (rememberChoice && decision === 'approve') {
        setAutoApprovePreference(projectId, agent, true);
      }
      
      const response = await apiFetch(`/approvals/${runId}/${stepIndex}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          decision,
          auto_approve_agent: autoApprove ? agent : undefined
        })
      });
      
      if (response.ok) {
        if (decision === 'approve') {
          setApprovalStatus('approved');
          setTimeout(() => {
            onDecision(decision, '');
            if (onClose) onClose();
          }, 1500);
        } else if (decision === 'reject') {
          setApprovalStatus('rejected');
          setTimeout(() => {
            onDecision(decision, '');
            if (onClose) onClose();
          }, 1000);
        } else {
          setApprovalStatus('modified');
          onDecision(decision, '');
          if (onClose) onClose();
        }
      } else {
        const error = await response.json();
        alert('Failed to submit decision: ' + (error.detail || 'Unknown error'));
        setIsSubmitting(false);
      }
    } catch (error) {
      alert('Error submitting decision: ' + error);
      setIsSubmitting(false);
    }
  };

  const timeRemaining = () => {
    const now = new Date();
    const timeout = new Date(timeoutAt);
    const diffMs = timeout.getTime() - now.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffSeconds = Math.floor((diffMs % (1000 * 60)) / 1000);
    
    if (diffMs <= 0) return { expired: true, text: "Expired" };
    return { expired: false, text: `${diffMinutes}:${diffSeconds.toString().padStart(2, '0')}` };
  };

  const getContextPreview = () => {
    if (!context) return null;
    
    const preview: string[] = [];
    
    if (agent === 'document' && context.expected_results?.documents_count) {
      preview.push(`${context.expected_results.documents_count} document(s) will be analyzed`);
    } else if (agent === 'backlog' && context.expected_results?.items_count) {
      preview.push(`Will create ~${context.expected_results.items_count} backlog items`);
    }
    
    if (context.workflow_steps && context.current_step_index !== undefined) {
      const totalSteps = context.workflow_steps.length;
      const completedSteps = context.workflow_steps.filter(s => s.status === 'done').length;
      preview.push(`Step ${context.current_step_index + 1}/${totalSteps} (${completedSteps} completed)`);
    }
    
    if (context.expected_results?.description) {
      preview.push(context.expected_results.description);
    }
    
    return preview.length > 0 ? preview : null;
  };

  const timer = timeRemaining();
  const contextPreview = getContextPreview();

  if (approvalStatus === 'approved') {
    return (
      <div className="bg-green-50 border border-green-300 rounded-lg p-4 mb-4 animate-pulse">
        <div className="flex items-center gap-3">
          <span className="text-3xl">✓</span>
          <div>
            <div className="font-semibold text-green-800">Step Approved!</div>
            <div className="text-sm text-green-700">Execution in progress...</div>
          </div>
        </div>
      </div>
    );
  }

  if (approvalStatus === 'rejected') {
    return (
      <div className="bg-red-50 border border-red-300 rounded-lg p-4 mb-4">
        <div className="flex items-center gap-3">
          <span className="text-3xl">✗</span>
          <div>
            <div className="font-semibold text-red-800">Step Rejected</div>
            <div className="text-sm text-red-700">Workflow stopped</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`border rounded-lg p-4 mb-4 ${
      timer.expired 
        ? 'bg-red-50 border-red-300' 
        : 'bg-yellow-50 border-yellow-200'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{getAgentIcon(agent)}</span>
          <div>
            <div className={`font-semibold ${
              timer.expired ? 'text-red-800' : 'text-yellow-800'
            }`}>
              {timer.expired ? '⏱️ Approval Expired' : '⏸ Approval Required'}
            </div>
            <div className={`text-sm ${
              timer.expired ? 'text-red-700' : 'text-yellow-700'
            }`}>
              Step {stepIndex + 1} • {agent}Agent
            </div>
          </div>
        </div>
        <div className={`text-xs font-mono ${
          timer.expired ? 'text-red-700 font-bold' : 'text-yellow-700'
        }`}>
          {timer.text}
        </div>
      </div>

      {timer.expired && (
        <div className="mb-3 bg-red-100 border border-red-200 rounded p-2 text-sm text-red-800">
          This approval has expired. The workflow may have auto-rejected or timed out. You can still approve to retry this step.
        </div>
      )}

      <div className="mb-3">
        <div className="text-sm text-gray-900 mb-2 font-medium">{objective}</div>
        
        {contextPreview && contextPreview.length > 0 && (
          <div className="mt-2 bg-blue-50 border border-blue-200 rounded p-3">
            <div className="text-xs font-semibold text-blue-900 mb-1">📊 Context</div>
            <ul className="space-y-1">
              {contextPreview.map((item, idx) => (
                <li key={idx} className="text-xs text-blue-800 flex items-start gap-1">
                  <span className="text-blue-600">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Auto-approve checkboxes */}
      <div className="mb-3 space-y-2">
        <label className="flex items-center text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={autoApprove}
            onChange={(e) => setAutoApprove(e.target.checked)}
            className="mr-2 w-4 h-4 rounded border-gray-300 text-yellow-600 focus:ring-yellow-500"
            disabled={isSubmitting}
          />
          <span>Auto-approve all future <strong>{agent}Agent</strong> steps in this run</span>
        </label>
        
        {projectId && (
          <label className="flex items-center text-sm text-gray-700 cursor-pointer">
            <input
              type="checkbox"
              checked={rememberChoice}
              onChange={(e) => setRememberChoice(e.target.checked)}
              className="mr-2 w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              disabled={isSubmitting}
            />
            <span>Remember my choice for <strong>{agent}Agent</strong> in this project</span>
          </label>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => handleDecision('approve')}
          disabled={isSubmitting}
          className="flex-1 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm font-medium"
        >
          {isSubmitting ? 'Submitting...' : '✓ Approve'}
        </button>
        
        <button
          onClick={() => handleDecision('reject')}
          disabled={isSubmitting}
          className="flex-1 bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm font-medium"
        >
          {isSubmitting ? 'Submitting...' : '✗ Reject'}
        </button>
        
        <button
          onClick={() => handleDecision('modify')}
          disabled={isSubmitting}
          className="flex-1 bg-yellow-600 text-white px-4 py-2 rounded-md hover:bg-yellow-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm font-medium"
        >
          {isSubmitting ? 'Submitting...' : '✏️ Modify'}
        </button>
      </div>
    </div>
  );
};