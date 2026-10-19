import React, { useState } from 'react';
import {
  Bug,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  FileCode,
  Loader2,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';
import type { InvestigationResponse, EvidenceCitation } from '../api';

interface InvestigationPanelProps {
  repoId: string | null;
  onSelectEvidence: (filePath: string, line: number) => void;
  onRunInvestigation: (desc: string, traceback: string) => Promise<void>;
  onGeneratePatch?: (targetFile: string, suggestedFix: string, issueDesc?: string) => Promise<void>;
  patchLoading?: boolean;
  investigation: InvestigationResponse | null;
  loading: boolean;
  error: string | null;
}

export function InvestigationPanel({
  repoId,
  onSelectEvidence,
  onRunInvestigation,
  onGeneratePatch,
  patchLoading,
  investigation,
  loading,
  error,
}: InvestigationPanelProps) {
  const [issueDesc, setIssueDesc] = useState(
    'Expense calculation crashes with ZeroDivisionError when participant count is 0.'
  );
  const [traceback, setTraceback] = useState(
    `File "expense.py", line 14, in calculate_expense_share\n  return total_amount / participant_count\nZeroDivisionError: division by zero`
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!repoId || !issueDesc.trim()) return;
    await onRunInvestigation(issueDesc, traceback);
  }

  return (
    <div className="investigation-container">
      {/* Investigation Form */}
      <div className="panel-card">
        <div className="panel-card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Bug style={{ width: 18, height: 18, color: '#f59e0b' }} />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>Bug Investigation Assistant</h3>
          </div>
          <span style={{ fontSize: '0.75rem', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <ShieldCheck style={{ width: 14, height: 14, color: '#10b981' }} /> Grounded Evidence
          </span>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.75rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: '#9ca3af', marginBottom: '0.25rem' }}>
              Issue Description
            </label>
            <input
              type="text"
              className="input-text"
              value={issueDesc}
              onChange={(e) => setIssueDesc(e.target.value)}
              placeholder="Describe the bug or unexpected behavior..."
              disabled={loading || !repoId}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: '#9ca3af', marginBottom: '0.25rem' }}>
              Stack Trace / Failure Output (Optional)
            </label>
            <textarea
              className="input-text"
              style={{ minHeight: '70px', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', resize: 'vertical' }}
              value={traceback}
              onChange={(e) => setTraceback(e.target.value)}
              placeholder="Paste traceback or error logs..."
              disabled={loading || !repoId}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.25rem' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !repoId}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              {loading ? (
                <>
                  <Loader2 className="spin" style={{ width: 16, height: 16 }} />
                  <span>Diagnosing with Ollama...</span>
                </>
              ) : (
                <>
                  <Sparkles style={{ width: 16, height: 16 }} />
                  <span>Start Investigation</span>
                </>
              )}
            </button>
          </div>
        </form>

        {error && (
          <div style={{ color: '#ef4444', fontSize: '0.8rem', marginTop: '0.75rem', display: 'flex', gap: '0.35rem' }}>
            <AlertTriangle style={{ width: 16, height: 16, flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Investigation Results */}
      {investigation && (
        <div className="panel-card" style={{ borderLeft: '3px solid var(--accent-primary)', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="panel-card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <CheckCircle2 style={{ width: 18, height: 18, color: '#10b981' }} />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>Root Cause Analysis</h3>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <div
                style={{
                  fontSize: '0.75rem',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  background:
                    investigation.execution_mode === 'live_model'
                      ? '#064e3b'
                      : investigation.execution_mode === 'mock'
                      ? '#312e81'
                      : '#78350f',
                  color:
                    investigation.execution_mode === 'live_model'
                      ? '#34d399'
                      : investigation.execution_mode === 'mock'
                      ? '#a5b4fc'
                      : '#fcd34d',
                  border: '1px solid currentColor',
                }}
              >
                {investigation.execution_mode === 'live_model'
                  ? `Live LLM (${investigation.provider_name})`
                  : investigation.execution_mode === 'mock'
                  ? `Mock Provider (${investigation.provider_name})`
                  : `Deterministic Fallback (${investigation.provider_name})`}
                {investigation.latency_seconds ? ` • ${investigation.latency_seconds}s` : ''}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#38bdf8', background: '#0c4a6e', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                Confidence: {(investigation.confidence * 100).toFixed(0)}%
              </div>
            </div>
          </div>

          {/* Root Cause Analysis & Quick Actions */}
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
            <div style={{ fontSize: '0.875rem', lineHeight: 1.6, color: '#f3f4f6', flex: 1, minWidth: '220px' }}>
              {investigation.root_cause}
            </div>
            {onGeneratePatch && (
              <button
                id="generate-patch-btn"
                data-testid="generate-patch-btn"
                className="btn btn-primary"
                style={{
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  padding: '0.5rem 0.9rem',
                  background: 'var(--accent-primary)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                  flexShrink: 0,
                }}
                disabled={patchLoading}
                onClick={() => {
                  const target = investigation.evidence[0]?.file_path || 'expense.py';
                  const fix = investigation.suggested_fix || investigation.root_cause;
                  onGeneratePatch(target, fix, issueDesc);
                }}
              >
                {patchLoading ? (
                  <Loader2 className="spin" style={{ width: 15, height: 15 }} />
                ) : (
                  <Sparkles style={{ width: 15, height: 15 }} />
                )}
                <span>Generate Patch</span>
              </button>
            )}
          </div>

          {/* Evidence Citations */}
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', marginBottom: '0.6rem', letterSpacing: '0.025em' }}>
              Supporting Evidence ({investigation.evidence.length} citations)
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {investigation.evidence.map((ev: EvidenceCitation, idx: number) => (
                <div
                  key={idx}
                  onClick={() => onSelectEvidence(ev.file_path, ev.start_line)}
                  style={{
                    background: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    padding: '0.75rem 0.85rem',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#3b82f6')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-color)')}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: '#60a5fa', fontWeight: 500 }}>
                      <FileCode style={{ width: 14, height: 14 }} />
                      <span>{ev.file_path}:{ev.start_line}-{ev.end_line}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', fontSize: '0.7rem', color: '#9ca3af' }}>
                      <span>Jump to code</span>
                      <ChevronRight style={{ width: 12, height: 12 }} />
                    </div>
                  </div>

                  <div style={{ fontSize: '0.775rem', color: '#9ca3af', marginBottom: '0.4rem', lineHeight: 1.4 }}>
                    {ev.explanation}
                  </div>

                  {ev.snippet && (
                    <pre
                      style={{
                        margin: 0,
                        background: '#0a0f1d',
                        padding: '0.45rem 0.6rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontFamily: 'var(--font-mono)',
                        color: '#f87171',
                        overflowX: 'auto',
                      }}
                    >
                      {ev.snippet}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Suggested Fix */}
          <div style={{ background: '#1e293b', borderRadius: '6px', padding: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#38bdf8' }}>
              Recommended Fix Strategy:
            </div>
            <div style={{ fontSize: '0.825rem', color: '#e2e8f0', lineHeight: 1.5 }}>
              {investigation.suggested_fix}
            </div>
            {investigation.recommended_test && (
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                <span style={{ fontWeight: 600 }}>Target Test:</span> {investigation.recommended_test}
              </div>
            )}

            {onGeneratePatch && (
              <div style={{ marginTop: '0.5rem', display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  id="generate-patch-btn-secondary"
                  className="btn btn-primary"
                  style={{
                    fontSize: '0.75rem',
                    padding: '0.45rem 0.85rem',
                    background: 'var(--accent-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                  disabled={patchLoading}
                  onClick={() => {
                    const target = investigation.evidence[0]?.file_path || 'expense.py';
                    const fix = investigation.suggested_fix || investigation.root_cause;
                    onGeneratePatch(target, fix, issueDesc);
                  }}
                >
                  {patchLoading ? (
                    <Loader2 className="spin" style={{ width: 14, height: 14 }} />
                  ) : (
                    <Sparkles style={{ width: 14, height: 14 }} />
                  )}
                  <span>Generate Patch</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

