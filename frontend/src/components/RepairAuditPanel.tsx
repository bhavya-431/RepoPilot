import { useState } from 'react';
import {
  RotateCcw,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  FileText,
  Download,
  Loader2,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import type { RepairSessionResponse, VerificationReportResponse } from '../api';

interface RepairAuditPanelProps {
  session: RepairSessionResponse | null;
  report: VerificationReportResponse | null;
  loading: boolean;
  onStartSession: () => Promise<void>;
  onExecuteIteration: (feedback?: string) => Promise<void>;
  onFetchReport: () => Promise<void>;
}

export function RepairAuditPanel({
  session,
  report,
  loading,
  onStartSession,
  onExecuteIteration,
  onFetchReport,
}: RepairAuditPanelProps) {
  const [feedback, setFeedback] = useState('');

  function downloadMarkdown() {
    if (!report) return;
    const blob = new Blob([report.markdown_report], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `VERIFICATION_REPORT_${report.session_id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-app)', overflow: 'hidden' }}>
      {/* Top Action Bar */}
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#f3f4f6', fontWeight: 600, fontSize: '0.85rem' }}>
            <RotateCcw style={{ width: 16, height: 16, color: '#f59e0b' }} />
            <span>Bounded Repair Loop & Audit Trail</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <ShieldCheck style={{ width: 13, height: 13, color: '#10b981' }} /> Bounded (Max 2 Cycles)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {!session ? (
            <button
              className="btn btn-primary"
              style={{ fontSize: '0.8rem', padding: '0.35rem 0.85rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
              onClick={onStartSession}
              disabled={loading}
            >
              {loading ? <Loader2 className="spin" style={{ width: 14, height: 14 }} /> : <Sparkles style={{ width: 14, height: 14 }} />}
              <span>Start Repair Session</span>
            </button>
          ) : session.status === 'in_progress' ? (
            <button
              className="btn btn-primary"
              style={{ background: '#2563eb', fontSize: '0.8rem', padding: '0.35rem 0.85rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
              onClick={() => onExecuteIteration(feedback)}
              disabled={loading}
            >
              {loading ? <Loader2 className="spin" style={{ width: 14, height: 14 }} /> : <ChevronRight style={{ width: 14, height: 14 }} />}
              <span>Execute Iteration ({session.current_iteration + 1} / {session.max_iterations})</span>
            </button>
          ) : (
            <button
              className="btn"
              style={{ background: '#10b981', color: '#fff', fontSize: '0.8rem', padding: '0.35rem 0.85rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
              onClick={onFetchReport}
              disabled={loading}
            >
              <FileText style={{ width: 14, height: 14 }} />
              <span>Generate Verification Report</span>
            </button>
          )}

          {report && (
            <button
              className="btn"
              style={{ background: '#1e293b', border: '1px solid #334155', color: '#38bdf8', fontSize: '0.8rem', padding: '0.35rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
              onClick={downloadMarkdown}
            >
              <Download style={{ width: 14, height: 14 }} />
              <span>Export MD</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Grid: Iteration Timeline on Left, Audit Report on Right */}
      <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Iteration Timeline */}
        <div style={{ borderRight: '1px solid var(--border-color)', padding: '1.25rem 1.25rem 2rem 1.25rem', overflowY: 'auto', minHeight: 0, boxSizing: 'border-box' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
            Repair Iterations
          </div>

          {session ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ padding: '0.6rem', background: 'var(--bg-surface-elevated)', borderRadius: '6px', fontSize: '0.8rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <span style={{ fontWeight: 600, color: '#f3f4f6' }}>Target: {session.target_file}</span>
                  <span style={{ fontSize: '0.7rem', color: '#38bdf8' }}>{session.status.toUpperCase()}</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{session.final_verdict}</div>
              </div>

              {session.iterations.map((it) => (
                <div
                  key={it.iteration_number}
                  style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    padding: '0.75rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <span style={{ fontWeight: 600, color: '#60a5fa', fontSize: '0.85rem' }}>
                      Attempt {it.version}
                    </span>
                    <span
                      style={{
                        fontSize: '0.7rem',
                        padding: '0.1rem 0.4rem',
                        borderRadius: '4px',
                        background: it.test_status === 'passed' ? '#064e3b' : '#7f1d1d',
                        color: it.test_status === 'passed' ? '#34d399' : '#f87171',
                      }}
                    >
                      {it.test_status?.toUpperCase()}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.75rem', color: '#cbd5e1', marginBottom: '0.4rem' }}>
                    {it.patch_explanation}
                  </div>

                  {it.failure_traceback && (
                    <pre
                      style={{
                        margin: 0,
                        background: '#070a13',
                        padding: '0.4rem',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        color: '#f87171',
                        fontFamily: 'var(--font-mono)',
                        maxHeight: '120px',
                        overflowY: 'auto',
                      }}
                    >
                      {it.failure_traceback}
                    </pre>
                  )}
                </div>
              ))}

              {session.status === 'in_progress' && (
                <div style={{ marginTop: '0.5rem' }}>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#9ca3af', marginBottom: '0.25rem' }}>
                    Optional Feedback for Next Iteration:
                  </label>
                  <input
                    type="text"
                    className="input-text"
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="e.g., Also check negative amounts"
                    style={{ fontSize: '0.75rem', padding: '0.4rem' }}
                  />
                </div>
              )}
            </div>
          ) : (
            <div style={{ color: '#6b7280', fontSize: '0.8rem', textAlign: 'center', marginTop: '3rem' }}>
              No active repair session. Click <strong>"Start Repair Session"</strong> to begin.
            </div>
          )}
        </div>

        {/* Audit & Verification Report View */}
        <div style={{ flex: 1, minHeight: 0, padding: '1.25rem 1.25rem 2rem 1.25rem', overflowY: 'auto', boxSizing: 'border-box' }}>
          {report ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {report.tests_verified ? (
                    <CheckCircle2 style={{ width: 22, height: 22, color: '#10b981' }} />
                  ) : (
                    <XCircle style={{ width: 22, height: 22, color: '#ef4444' }} />
                  )}
                  <h3 style={{ fontSize: '1rem', margin: 0 }}>Final Verification Audit Report</h3>
                </div>
                <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>Report: {report.report_id}</span>
              </div>

              <div
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '1.25rem',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.8rem',
                  lineHeight: 1.6,
                  color: '#cbd5e1',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {report.markdown_report}
              </div>
            </div>
          ) : (
            <div style={{ color: '#475569', textAlign: 'center', marginTop: '5rem', fontSize: '0.85rem' }}>
              The comprehensive verification report and immutable audit trail will appear here once iterations conclude.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
