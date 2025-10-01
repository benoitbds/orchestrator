import React, { useState } from 'react';

interface Props {
  runId: string;
  stepIndex: number;
  agent: string;
  objective: string;
  createdAt: string;
  timeoutAt: string;
  onDecision: (decision: 'approve' | 'reject' | 'modify', reason: string) => void;
  onClose: () => void;
}

export const ApprovalModal: React.FC<Props> = ({
  runId,
  stepIndex,
  agent,
  objective,
  createdAt,
  timeoutAt,
  onDecision,
  onClose
}) => {
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

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
      const response = await fetch(`/api/approvals/${runId}/${stepIndex}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, reason })
      });
      
      if (response.ok) {
        onDecision(decision, reason);
        onClose();
      } else {
        const error = await response.json();
        alert('Failed to submit decision: ' + (error.detail || 'Unknown error'));
      }
    } catch (error) {
      alert('Error submitting decision: ' + error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const timeRemaining = () => {
    const now = new Date();
    const timeout = new Date(timeoutAt);
    const diffMs = timeout.getTime() - now.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffSeconds = Math.floor((diffMs % (1000 * 60)) / 1000);
    
    if (diffMs <= 0) return "Expired";
    return `${diffMinutes}:${diffSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full">
        {/* Header */}
        <div className="bg-yellow-50 border-b border-yellow-200 p-6 rounded-t-lg">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-yellow-800 flex items-center">
              ⏸ Approval Required
            </h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-xl"
            >
              ×
            </button>
          </div>
          <div className="mt-2 text-sm text-yellow-700">
            Time remaining: <span className="font-mono font-semibold">{timeRemaining()}</span>
          </div>
        </div>

        <div className="p-6">
          {/* Step Information */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <div className="flex items-center mb-2">
              <span className="text-2xl mr-3">{getAgentIcon(agent)}</span>
              <div>
                <div className="text-sm text-gray-600">
                  Step {stepIndex + 1} • {agent}Agent
                </div>
                <div className="font-semibold text-gray-900">{objective}</div>
              </div>
            </div>
          </div>

          {/* Context Information */}
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <h3 className="font-semibold mb-2 text-gray-800">Execution Context</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Run ID:</span>
                <span className="ml-2 font-mono">{runId}</span>
              </div>
              <div>
                <span className="text-gray-600">Created:</span>
                <span className="ml-2">{new Date(createdAt).toLocaleTimeString()}</span>
              </div>
            </div>
          </div>

          {/* Decision Reason */}
          <div className="mb-6">
            <label className="block text-sm font-medium mb-2 text-gray-700">
              Decision Reason (optional)
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 h-24 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Add a comment about your decision..."
              disabled={isSubmitting}
            />
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={() => handleDecision('approve')}
              disabled={isSubmitting}
              className="flex-1 bg-green-600 text-white px-6 py-3 rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isSubmitting ? 'Submitting...' : '✓ Approve & Continue'}
            </button>
            
            <button
              onClick={() => handleDecision('reject')}
              disabled={isSubmitting}
              className="flex-1 bg-red-600 text-white px-6 py-3 rounded-md hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isSubmitting ? 'Submitting...' : '✗ Reject & Stop'}
            </button>
            
            <button
              onClick={() => handleDecision('modify')}
              disabled={isSubmitting}
              className="flex-1 bg-yellow-600 text-white px-6 py-3 rounded-md hover:bg-yellow-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isSubmitting ? 'Submitting...' : '✏️ Modify & Continue'}
            </button>
          </div>

          {/* Help Text */}
          <div className="mt-4 text-xs text-gray-500 bg-gray-50 rounded p-3">
            <strong>Actions:</strong>
            <ul className="mt-1 space-y-1">
              <li><strong>Approve:</strong> Continue workflow with this step as planned</li>
              <li><strong>Reject:</strong> Cancel entire workflow and stop execution</li>
              <li><strong>Modify:</strong> Continue but note modifications for future steps</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};