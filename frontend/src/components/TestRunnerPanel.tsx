import { useState } from 'react';
import {
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Terminal,
  Loader2,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import type { TestExecutionResponse } from '../api';

interface TestRunnerPanelProps {
  repoId: string | null;
  onRunTest: (target?: string) => Promise<void>;
  testResult: TestExecutionResponse | null;
  loading: boolean;
  defaultTarget?: string;
}

export function TestRunnerPanel({
  repoId,
  onRunTest,
  testResult,
  loading,
  defaultTarget = 'test_expense.py',
}: TestRunnerPanelProps) {
  const [target, setTarget] = useState(defaultTarget);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-app)', overflow: 'hidden' }}>
      {/* Test Controls Bar */}
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
            <Terminal style={{ width: 16, height: 16, color: '#38bdf8' }} />
            <span>Controlled Test Runner</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <ShieldCheck style={{ width: 13, height: 13, color: '#10b981' }} /> Allowlist Sandbox (pytest)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="text"
            className="input-text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="test_target.py or directory"
            style={{ width: '200px', fontSize: '0.75rem', padding: '0.35rem 0.6rem' }}
            disabled={loading || !repoId}
          />

          <button
            className="btn btn-primary"
            style={{
              padding: '0.35rem 0.85rem',
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
            disabled={loading || !repoId}
            onClick={() => onRunTest(target)}
          >
            {loading ? (
              <>
                <Loader2 className="spin" style={{ width: 14, height: 14 }} />
                <span>Running Pytest...</span>
              </>
            ) : (
              <>
                <Play style={{ width: 14, height: 14, fill: 'currentColor' }} />
                <span>Run Tests</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Execution Outcome Badge Header */}
      {testResult ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.6rem 1.25rem',
            background:
              testResult.status === 'passed'
                ? '#064e3b25'
                : testResult.status === 'failed'
                ? '#7f1d1d25'
                : '#451a0325',
            borderBottom: '1px solid var(--border-color)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {testResult.status === 'passed' && (
              <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 600, fontSize: '0.85rem' }}>
                <CheckCircle2 style={{ width: 18, height: 18 }} /> VERIFIED PASSED
              </span>
            )}
            {testResult.status === 'failed' && (
              <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 600, fontSize: '0.85rem' }}>
                <XCircle style={{ width: 18, height: 18 }} /> TESTS FAILED
              </span>
            )}
            {testResult.status === 'timeout' && (
              <span style={{ color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 600, fontSize: '0.85rem' }}>
                <Clock style={{ width: 18, height: 18 }} /> TIMEOUT EXCEEDED
              </span>
            )}
            {testResult.status === 'error' && (
              <span style={{ color: '#f97316', display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 600, fontSize: '0.85rem' }}>
                <AlertTriangle style={{ width: 18, height: 18 }} /> EXECUTION ERROR
              </span>
            )}

            <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem' }}>
              <span style={{ color: '#10b981', background: '#064e3b40', padding: '0.1rem 0.4rem', borderRadius: '4px' }}>
                {testResult.passed_count} Passed
              </span>
              <span style={{ color: '#ef4444', background: '#7f1d1d40', padding: '0.1rem 0.4rem', borderRadius: '4px' }}>
                {testResult.failed_count} Failed
              </span>
              {testResult.error_count > 0 && (
                <span style={{ color: '#f59e0b', background: '#78350f40', padding: '0.1rem 0.4rem', borderRadius: '4px' }}>
                  {testResult.error_count} Errors
                </span>
              )}
            </div>
          </div>

          <div style={{ fontSize: '0.75rem', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>Duration: {testResult.duration_seconds}s</span>
            <span>Exit Code: {testResult.exit_code}</span>
          </div>
        </div>
      ) : (
        <div style={{ padding: '0.6rem 1.25rem', background: '#0f172a', borderBottom: '1px solid var(--border-color)', fontSize: '0.8rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <RefreshCw style={{ width: 14, height: 14 }} />
          <span>Status: Honest Verification Boundary (Tests not yet run for current workspace state)</span>
        </div>
      )}

      {/* Terminal Output Stream */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          background: '#070a13',
          padding: '1rem 1.25rem 2rem 1.25rem',
          boxSizing: 'border-box',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.8rem',
          lineHeight: 1.5,
          color: '#cbd5e1',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
        }}
      >
        {loading ? (
          <div style={{ color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Loader2 className="spin" style={{ width: 16, height: 16 }} />
            <span>Spawning isolated subprocess with PYTHONPATH and timeout monitor...</span>
          </div>
        ) : testResult ? (
          <div>
            <div style={{ color: '#64748b', marginBottom: '0.75rem', fontSize: '0.75rem' }}>
              $ {testResult.command}
            </div>
            <div>{testResult.stdout || 'No stdout captured'}</div>
            {testResult.stderr && (
              <div style={{ color: '#f87171', marginTop: '0.75rem' }}>
                {testResult.stderr}
              </div>
            )}
          </div>
        ) : (
          <div style={{ color: '#475569', textAlign: 'center', marginTop: '3rem' }}>
            Click <strong>"Run Tests"</strong> above to execute regression tests inside the safe sandbox.
          </div>
        )}
      </div>
    </div>
  );
}
