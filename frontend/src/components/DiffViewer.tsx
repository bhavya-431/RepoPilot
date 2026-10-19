import {
  FileDiff,
  Check,
  X,
  AlertCircle,
  FileCode,
  ShieldCheck,
  Loader2,
  Sparkles,
} from 'lucide-react';
import type { PatchProposalResponse } from '../api';

interface DiffViewerProps {
  patch: PatchProposalResponse | null;
  loading: boolean;
  onApprove: (patchId: string) => Promise<void>;
  onReject: (patchId: string, reason?: string) => Promise<void>;
  actionLoading: boolean;
  hasInvestigation?: boolean;
  onGeneratePatchFromInvestigation?: () => Promise<void>;
  onNavigateToInvestigate?: () => void;
}

export function DiffViewer({
  patch,
  loading,
  onApprove,
  onReject,
  actionLoading,
  hasInvestigation,
  onGeneratePatchFromInvestigation,
  onNavigateToInvestigate,
}: DiffViewerProps) {
  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#9ca3af', gap: '0.75rem' }}>
        <Loader2 className="spin" style={{ width: 28, height: 28, color: '#3b82f6' }} />
        <span>Synthesizing unified patch with Ollama...</span>
      </div>
    );
  }

  if (!patch) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#6b7280', gap: '1rem', padding: '2rem', textAlign: 'center' }}>
        <FileDiff style={{ width: 42, height: 42, color: '#4b5563' }} />
        <div>
          <h4 style={{ fontSize: '1rem', color: '#e2e8f0', marginBottom: '0.35rem', fontWeight: 600 }}>No patch proposal active</h4>
          <p style={{ fontSize: '0.85rem', maxWidth: '380px', color: '#9ca3af', lineHeight: 1.5 }}>
            {hasInvestigation
              ? 'An investigation was completed. Generate a surgical patch proposal to preview code diffs.'
              : 'Run a live investigation on the Bug Investigator tab and click "Generate Patch" to preview surgical diffs.'}
          </p>
        </div>
        {hasInvestigation && onGeneratePatchFromInvestigation && (
          <button
            id="diff-empty-generate-btn"
            className="btn btn-primary"
            style={{
              fontSize: '0.825rem',
              fontWeight: 600,
              padding: '0.5rem 1rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
            }}
            onClick={onGeneratePatchFromInvestigation}
          >
            <Sparkles style={{ width: 15, height: 15 }} />
            <span>Generate Patch Proposal</span>
          </button>
        )}
        {!hasInvestigation && onNavigateToInvestigate && (
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.825rem', padding: '0.45rem 0.9rem' }}
            onClick={onNavigateToInvestigate}
          >
            Go to Bug Investigator
          </button>
        )}
      </div>
    );
  }

  const { diff, version, target_file, explanation, status, patch_id } = patch;
  const lines = diff.diff_text.split('\n');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-app)', overflow: 'hidden' }}>
      {/* Patch Action Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.75rem 1.25rem',
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-color)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#60a5fa', fontWeight: 600, fontSize: '0.85rem' }}>
            <FileCode style={{ width: 16, height: 16 }} />
            <span>{target_file}</span>
          </div>
          <span
            style={{
              fontSize: '0.7rem',
              padding: '0.15rem 0.5rem',
              borderRadius: '12px',
              fontWeight: 600,
              background: '#1e293b',
              color: '#38bdf8',
            }}
          >
            {version}
          </span>
          <div style={{ display: 'flex', gap: '0.4rem', fontSize: '0.75rem' }}>
            <span style={{ color: '#10b981', fontWeight: 600 }}>+{diff.added_count}</span>
            <span style={{ color: '#ef4444', fontWeight: 600 }}>-{diff.removed_count}</span>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          {status === 'pending_review' && (
            <>
              <button
                className="btn"
                style={{
                  background: '#ef44441a',
                  color: '#ef4444',
                  border: '1px solid #ef444440',
                  padding: '0.35rem 0.75rem',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
                disabled={actionLoading}
                onClick={() => onReject(patch_id, 'User rejected proposed patch')}
              >
                <X style={{ width: 14, height: 14 }} />
                <span>Reject</span>
              </button>

              <button
                className="btn btn-primary"
                style={{
                  background: '#10b981',
                  borderColor: '#059669',
                  padding: '0.35rem 0.9rem',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
                disabled={actionLoading || !diff.is_applicable}
                onClick={() => onApprove(patch_id)}
              >
                {actionLoading ? (
                  <Loader2 className="spin" style={{ width: 14, height: 14 }} />
                ) : (
                  <Check style={{ width: 14, height: 14 }} />
                )}
                <span>Approve & Apply</span>
              </button>
            </>
          )}

          {status === 'applied' && (
            <span
              style={{
                fontSize: '0.75rem',
                color: '#10b981',
                background: '#064e3b',
                padding: '0.25rem 0.6rem',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                fontWeight: 600,
              }}
            >
              <ShieldCheck style={{ width: 14, height: 14 }} /> Patch Applied
            </span>
          )}

          {status === 'rejected' && (
            <span
              style={{
                fontSize: '0.75rem',
                color: '#ef4444',
                background: '#450a0a',
                padding: '0.25rem 0.6rem',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                fontWeight: 600,
              }}
            >
              <X style={{ width: 14, height: 14 }} /> Rejected
            </span>
          )}
        </div>
      </div>

      {/* Explanation Banner & Provider Telemetry */}
      <div style={{ padding: '0.6rem 1.25rem', background: '#0f172a', borderBottom: '1px solid var(--border-color)', fontSize: '0.8rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1 }}>
          <Sparkles style={{ width: 15, height: 15, color: '#f59e0b', flexShrink: 0 }} />
          <span>{explanation}</span>
        </div>
        <div
          style={{
            fontSize: '0.75rem',
            padding: '0.15rem 0.5rem',
            borderRadius: '4px',
            whiteSpace: 'nowrap',
            background:
              patch.execution_mode === 'live_model'
                ? '#064e3b'
                : patch.execution_mode === 'mock'
                ? '#312e81'
                : '#78350f',
            color:
              patch.execution_mode === 'live_model'
                ? '#34d399'
                : patch.execution_mode === 'mock'
                ? '#a5b4fc'
                : '#fcd34d',
            border: '1px solid currentColor',
          }}
        >
          {patch.execution_mode === 'live_model'
            ? `Live LLM (${patch.provider_name})`
            : patch.execution_mode === 'mock'
            ? `Mock Provider (${patch.provider_name})`
            : `Deterministic Fallback (${patch.provider_name})`}
          {patch.latency_seconds ? ` • ${patch.latency_seconds}s` : ''}
        </div>
      </div>

      {/* Validation Warning if not applicable */}
      {!diff.is_applicable && diff.validation_error && (
        <div style={{ padding: '0.5rem 1.25rem', background: '#7f1d1d33', borderBottom: '1px solid #ef4444', color: '#f87171', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <AlertCircle style={{ width: 14, height: 14 }} />
          <span>Patch Conflict: {diff.validation_error}</span>
        </div>
      )}

      {/* Unified Diff Content View */}
      <div style={{ flex: 1, overflowY: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', padding: '0.75rem 0 1.5rem 0' }}>
        {lines.map((line, idx) => {
          let lineBg = 'transparent';
          let textColor = '#e2e8f0';

          if (line.startsWith('+++') || line.startsWith('---')) {
            textColor = '#94a3b8';
            lineBg = '#1e293b40';
          } else if (line.startsWith('@@')) {
            textColor = '#38bdf8';
            lineBg = '#0c4a6e30';
          } else if (line.startsWith('+')) {
            textColor = '#4ade80';
            lineBg = '#14532d30';
          } else if (line.startsWith('-')) {
            textColor = '#f87171';
            lineBg = '#7f1d1d30';
          }

          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                padding: '0.1rem 1.25rem',
                background: lineBg,
                color: textColor,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              <span style={{ width: '30px', userSelect: 'none', color: '#475569', fontSize: '0.75rem', textAlign: 'right', marginRight: '1rem' }}>
                {idx + 1}
              </span>
              <span>{line || ' '}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
