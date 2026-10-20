import { useState, useEffect } from 'react';
import { api, BACKEND_ROOT, type RepoInfo, type FileTreeNode, type FileContent, type SearchResultItem, type InvestigationResponse, type SystemStatus, type PatchProposalResponse } from './api';
import { FileTreeItem } from './components/FileTree';
import { CodeViewer } from './components/CodeViewer';
import { SearchOverlay } from './components/SearchOverlay';
import { InvestigationPanel } from './components/InvestigationPanel';
import { DiffViewer } from './components/DiffViewer';
import { TestRunnerPanel } from './components/TestRunnerPanel';
import { RepairAuditPanel } from './components/RepairAuditPanel';
import {
  Compass,
  FolderGit2,
  Search,
  Cpu,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Code2,
  Bug,
  FileDiff,
  PlayCircle,
  RotateCcw,
} from 'lucide-react';
import './index.css';

export function App() {
  const [repoPathInput, setRepoPathInput] = useState('benchmarks/sample_repo');
  const [currentRepo, setCurrentRepo] = useState<RepoInfo | null>(null);
  const [tree, setTree] = useState<FileTreeNode | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<FileContent | null>(null);
  const [highlightLine, setHighlightLine] = useState<number | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Active view tab: 'investigate' | 'patch' | 'tests' | 'repair' | 'explorer'
  const [activeTab, setActiveTab] = useState<'investigate' | 'patch' | 'tests' | 'repair' | 'explorer'>('investigate');

  // System status
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  // Investigation state
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [investigating, setInvestigating] = useState(false);
  const [investigationError, setInvestigationError] = useState<string | null>(null);

  // Patch state
  const [activePatch, setActivePatch] = useState<PatchProposalResponse | null>(null);
  const [patchGenerating, setPatchGenerating] = useState(false);
  const [patchActionLoading, setPatchActionLoading] = useState(false);

  // Test Runner state
  const [testResult, setTestResult] = useState<any | null>(null);
  const [testRunning, setTestRunning] = useState(false);

  // Repair Loop state
  const [repairSession, setRepairSession] = useState<any | null>(null);
  const [verificationReport, setVerificationReport] = useState<any | null>(null);
  const [repairLoading, setRepairLoading] = useState(false);




  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSearchOverlay, setShowSearchOverlay] = useState(false);

  // Quick auto-load default sample repository & system status on mount
  useEffect(() => {
    handleRegisterRepo('benchmarks/sample_repo');
    checkSystem();
  }, []);

  async function checkSystem() {
    try {
      const status = await api.getSystemStatus();
      setSystemStatus(status);
    } catch {
      // Backend may not have loaded yet
    }
  }


  async function handleRegisterRepo(path: string) {
    setErrorMsg(null);
    try {
      const repo = await api.registerRepo(path);
      setCurrentRepo(repo);
      const fileTree = await api.getTree(repo.repo_id);
      setTree(fileTree);
      // Auto select first file if available
      if (fileTree.children && fileTree.children.length > 0) {
        const firstFile = fileTree.children.find((c) => !c.is_dir) || fileTree.children[0];
        if (!firstFile.is_dir) {
          loadFile(repo.repo_id, firstFile.path);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load repository');
    }
  }

  async function loadFile(repoId: string, filePath: string, line?: number) {
    setSelectedFile(filePath);
    setHighlightLine(line || null);
    setFileLoading(true);
    setErrorMsg(null);
    try {
      const content = await api.getFile(repoId, filePath);
      setFileContent(content);
      if (line) {
        setTimeout(() => {
          const el = document.getElementById(`line-${line}`);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 150);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error opening file');
    } finally {
      setFileLoading(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!currentRepo || !searchQuery.trim()) return;

    setIsSearching(true);
    setShowSearchOverlay(true);
    try {
      const res = await api.searchRepo(currentRepo.repo_id, searchQuery);
      setSearchResults(res.results);
    } catch (err: any) {
      setErrorMsg(err.message || 'Search failed');
    } finally {
      setIsSearching(false);
    }
  }

  async function handleRunInvestigation(desc: string, tb: string) {
    if (!currentRepo) return;
    setInvestigating(true);
    setInvestigationError(null);
    try {
      const res = await api.investigate({
        repo_id: currentRepo.repo_id,
        issue_description: desc,
        traceback: tb,
      });
      setInvestigation(res);
    } catch (err: any) {
      setInvestigationError(err.message || 'Investigation failed');
    } finally {
      setInvestigating(false);
    }
  }

  function handleSelectEvidence(filePath: string, line: number) {
    if (currentRepo) {
      loadFile(currentRepo.repo_id, filePath, line);
    }
  }

  function handleSelectSearchResult(filePath: string, line: number) {
    setShowSearchOverlay(false);
    if (currentRepo) {
      loadFile(currentRepo.repo_id, filePath, line);
    }
  }

  async function handleGeneratePatch(targetFile: string, suggestedFix: string, issueDesc?: string) {
    if (!currentRepo || !investigation) return;
    setPatchGenerating(true);
    setErrorMsg(null);
    try {
      const resolvedTarget = targetFile || investigation.evidence[0]?.file_path || 'expense.py';
      const resolvedFix = suggestedFix || investigation.suggested_fix || investigation.root_cause;
      const proposal = await api.generatePatch({
        repo_id: currentRepo.repo_id,
        target_file: resolvedTarget,
        issue_description: issueDesc || investigation.root_cause || "Expense calculation crashes on zero participants",
        suggested_fix: resolvedFix,
        root_cause: investigation.root_cause,
      });
      setActivePatch(proposal);
      setActiveTab('patch');
    } catch (err: any) {
      setErrorMsg(err.message || 'Patch generation failed');
    } finally {
      setPatchGenerating(false);
    }
  }

  async function handleApprovePatch(patchId: string) {
    setPatchActionLoading(true);
    setErrorMsg(null);
    try {
      const updated = await api.approvePatch(patchId);
      setActivePatch(updated);
      // Reload current file in viewer so changes reflect immediately
      if (currentRepo && activePatch) {
        loadFile(currentRepo.repo_id, activePatch.target_file);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to approve and apply patch');
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleRejectPatch(patchId: string, reason?: string) {
    setPatchActionLoading(true);
    setErrorMsg(null);
    try {
      const updated = await api.rejectPatch(patchId, reason);
      setActivePatch(updated);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to reject patch');
    } finally {
      setPatchActionLoading(false);
    }
  }

  async function handleRunTest(target?: string) {
    if (!currentRepo) return;
    setTestRunning(true);
    setErrorMsg(null);
    try {
      const res = await api.runTests({
        repo_id: currentRepo.repo_id,
        test_target: target || 'test_expense.py',
        timeout_seconds: 30,
      });
      setTestResult(res);
      setActiveTab('tests');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to execute test');
    } finally {
      setTestRunning(false);
    }
  }

  async function handleStartRepairSession() {
    if (!currentRepo) return;
    setRepairLoading(true);
    setErrorMsg(null);
    try {
      const session = await api.startRepairSession({
        repo_id: currentRepo.repo_id,
        target_file: 'expense.py',
        issue_description: 'calculate_expense_share crashes with ZeroDivisionError when participant count is 0',
        root_cause: investigation?.root_cause || 'Missing zero check before division',
        test_target: 'test_expense.py',
        max_iterations: 2,
      });
      setRepairSession(session);
      setActiveTab('repair');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start repair session');
    } finally {
      setRepairLoading(false);
    }
  }

  async function handleExecuteRepairIteration(feedback?: string) {
    if (!repairSession) return;
    setRepairLoading(true);
    setErrorMsg(null);
    try {
      const updated = await api.iterateRepair(repairSession.session_id, feedback);
      setRepairSession(updated);
      if (updated.status === 'verified' || updated.status === 'max_iterations_reached') {
        const report = await api.getVerificationReport(repairSession.session_id);
        setVerificationReport(report);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Repair iteration failed');
    } finally {
      setRepairLoading(false);
    }
  }

  async function handleFetchVerificationReport() {
    if (!repairSession) return;
    setRepairLoading(true);
    try {
      const report = await api.getVerificationReport(repairSession.session_id);
      setVerificationReport(report);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to fetch verification report');
    } finally {
      setRepairLoading(false);
    }
  }





  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">
            <Compass style={{ width: 22, height: 22 }} />
          </div>
          <span className="brand-title">RepoPilot</span>
          <span className="brand-tag">Autonomous SE Agent</span>
        </div>

        {/* View Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', background: '#0a0f1d', padding: '0.2rem', borderRadius: '6px' }}>
          <button
            onClick={() => setActiveTab('investigate')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.75rem',
              borderRadius: '4px',
              border: 'none',
              background: activeTab === 'investigate' ? 'var(--bg-surface-elevated)' : 'transparent',
              color: activeTab === 'investigate' ? '#f3f4f6' : '#9ca3af',
              fontSize: '0.8rem',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            <Bug style={{ width: 15, height: 15, color: '#f59e0b' }} />
            <span>Bug Investigator</span>
          </button>
          <button
            onClick={() => setActiveTab('patch')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.75rem',
              borderRadius: '4px',
              border: 'none',
              background: activeTab === 'patch' ? 'var(--bg-surface-elevated)' : 'transparent',
              color: activeTab === 'patch' ? '#f3f4f6' : '#9ca3af',
              fontSize: '0.8rem',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            <FileDiff style={{ width: 15, height: 15, color: '#10b981' }} />
            <span>Patch Review {activePatch && `(${activePatch.version})`}</span>
          </button>
          <button
            onClick={() => setActiveTab('tests')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.75rem',
              borderRadius: '4px',
              border: 'none',
              background: activeTab === 'tests' ? 'var(--bg-surface-elevated)' : 'transparent',
              color: activeTab === 'tests' ? '#f3f4f6' : '#9ca3af',
              fontSize: '0.8rem',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            <PlayCircle style={{ width: 15, height: 15, color: '#a855f7' }} />
            <span>
              Test Verification
              {testResult && (
                <span
                  style={{
                    marginLeft: '0.3rem',
                    fontSize: '0.7rem',
                    padding: '0.05rem 0.35rem',
                    borderRadius: '4px',
                    background: testResult.status === 'passed' ? '#064e3b' : '#7f1d1d',
                    color: testResult.status === 'passed' ? '#34d399' : '#f87171',
                  }}
                >
                  {testResult.status.toUpperCase()}
                </span>
              )}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('repair')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.75rem',
              borderRadius: '4px',
              border: 'none',
              background: activeTab === 'repair' ? 'var(--bg-surface-elevated)' : 'transparent',
              color: activeTab === 'repair' ? '#f3f4f6' : '#9ca3af',
              fontSize: '0.8rem',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            <RotateCcw style={{ width: 15, height: 15, color: '#f59e0b' }} />
            <span>
              Repair & Audit
              {repairSession && (
                <span
                  style={{
                    marginLeft: '0.3rem',
                    fontSize: '0.7rem',
                    padding: '0.05rem 0.35rem',
                    borderRadius: '4px',
                    background: repairSession.status === 'verified' ? '#064e3b' : '#1e293b',
                    color: repairSession.status === 'verified' ? '#34d399' : '#38bdf8',
                  }}
                >
                  {repairSession.status === 'verified' ? 'VERIFIED' : `IT ${repairSession.current_iteration}/2`}
                </span>
              )}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('explorer')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.75rem',
              borderRadius: '4px',
              border: 'none',
              background: activeTab === 'explorer' ? 'var(--bg-surface-elevated)' : 'transparent',
              color: activeTab === 'explorer' ? '#f3f4f6' : '#9ca3af',
              fontSize: '0.8rem',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            <Code2 style={{ width: 15, height: 15, color: '#38bdf8' }} />
            <span>Code Explorer</span>
          </button>


        </div>

        <div className="header-status">
          <div className="status-badge">
            <Cpu style={{ width: 14, height: 14, color: systemStatus?.ollama_online ? '#10b981' : '#f59e0b' }} />
            <span>
              {systemStatus?.ollama_online
                ? `Local Engine: ${systemStatus.active_model}`
                : 'Local Engine: Connecting...'}
            </span>
          </div>
          <div className="status-badge">
            <div className="status-dot"></div>
            <span>Backend Online</span>
          </div>
        </div>
      </header>


      {/* Main App Body */}
      <div className="app-body">
        {/* Sidebar */}
        <aside className="app-sidebar">
          {/* Repo Selection Box */}
          <div className="sidebar-section">
            <div className="sidebar-title">Select Repository</div>
            <div className="repo-input-group">
              <input
                type="text"
                className="input-text"
                value={repoPathInput}
                onChange={(e) => setRepoPathInput(e.target.value)}
                placeholder="Path to Python repository"
              />
              <button
                className="btn btn-primary"
                onClick={() => handleRegisterRepo(repoPathInput)}
              >
                Open
              </button>
            </div>
            {errorMsg && (
              <div style={{ color: '#ef4444', fontSize: '0.75rem', marginTop: '0.5rem', display: 'flex', gap: '0.25rem' }}>
                <AlertCircle style={{ width: 14, height: 14, flexShrink: 0 }} />
                <span>{errorMsg}</span>
              </div>
            )}
          </div>

          {/* Repo Metadata Card */}
          {currentRepo && (
            <div className="sidebar-section" style={{ background: 'var(--bg-surface-elevated)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, fontSize: '0.85rem' }}>
                <FolderGit2 style={{ width: 16, height: 16, color: '#3b82f6' }} />
                <span>{currentRepo.name}</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.25rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {currentRepo.root_path}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                {currentRepo.test_framework && (
                  <span style={{ fontSize: '0.7rem', padding: '0.1rem 0.4rem', background: '#1e293b', borderRadius: '4px', color: '#38bdf8' }}>
                    Runner: {currentRepo.test_framework}
                  </span>
                )}
                <span style={{ fontSize: '0.7rem', padding: '0.1rem 0.4rem', background: '#1e293b', borderRadius: '4px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                  <CheckCircle2 style={{ width: 10, height: 10 }} /> Safe Sandbox
                </span>
              </div>
            </div>
          )}

          {/* Explorer Tree */}
          <div className="sidebar-section" style={{ padding: '0.75rem 1rem 0.25rem', borderBottom: 'none' }}>
            <div className="sidebar-title">Repository Explorer</div>
          </div>
          <div className="tree-container">
            {tree ? (
              <FileTreeItem
                node={tree}
                selectedPath={selectedFile}
                onSelectFile={(path) => currentRepo && loadFile(currentRepo.repo_id, path)}
              />
            ) : (
              <p style={{ fontSize: '0.8rem', color: '#6b7280', padding: '0.5rem' }}>
                No repository loaded.
              </p>
            )}
          </div>
        </aside>

        {/* Main Workspace */}
        <main className="app-main">
          {/* Workspace Subheader with search bar */}
          <div className="workspace-header">
            <form onSubmit={handleSearch} className="search-box">
              <Search className="search-icon" />
              <input
                type="text"
                placeholder="Search repository code & symbols (Enter)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                disabled={!currentRepo}
              />
            </form>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.8rem', color: '#9ca3af' }}>
              <span>Phase 1: Repository Explorer</span>
              <a
                href={`${BACKEND_ROOT}/docs`}
                target="_blank"
                rel="noreferrer"
                style={{ color: '#3b82f6', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
              >
                API Docs <ExternalLink style={{ width: 12, height: 12 }} />
              </a>
            </div>
          </div>

          {/* Code Viewer, Investigation View, or Patch Review View */}
          <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
            {activeTab === 'investigate' ? (
              <div style={{ display: 'grid', gridTemplateColumns: '440px 1fr', width: '100%', height: '100%', minHeight: 0 }}>
                <div style={{ borderRight: '1px solid var(--border-color)', overflowY: 'auto', minHeight: 0, boxSizing: 'border-box' }}>
                  <InvestigationPanel
                    repoId={currentRepo?.repo_id || null}
                    onSelectEvidence={handleSelectEvidence}
                    onRunInvestigation={handleRunInvestigation}
                    onGeneratePatch={handleGeneratePatch}
                    patchLoading={patchGenerating}
                    investigation={investigation}
                    loading={investigating}
                    error={investigationError}
                  />
                </div>
                <div style={{ height: '100%', minHeight: 0, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
                  <CodeViewer
                    content={fileContent}
                    loading={fileLoading}
                    highlightLine={highlightLine}
                  />
                </div>
              </div>
            ) : activeTab === 'patch' ? (
              <DiffViewer
                patch={activePatch}
                loading={patchGenerating}
                onApprove={handleApprovePatch}
                onReject={handleRejectPatch}
                actionLoading={patchActionLoading}
                hasInvestigation={!!investigation}
                onGeneratePatchFromInvestigation={async () => {
                  if (investigation) {
                    const target = investigation.evidence[0]?.file_path || 'expense.py';
                    const fix = investigation.suggested_fix || investigation.root_cause;
                    await handleGeneratePatch(target, fix);
                  }
                }}
                onNavigateToInvestigate={() => setActiveTab('investigate')}
              />
            ) : activeTab === 'tests' ? (
              <TestRunnerPanel
                repoId={currentRepo?.repo_id || null}
                onRunTest={handleRunTest}
                testResult={testResult}
                loading={testRunning}
                defaultTarget="test_expense.py"
              />
            ) : activeTab === 'repair' ? (
              <RepairAuditPanel
                session={repairSession}
                report={verificationReport}
                loading={repairLoading}
                onStartSession={handleStartRepairSession}
                onExecuteIteration={handleExecuteRepairIteration}
                onFetchReport={handleFetchVerificationReport}
              />
            ) : (
              <CodeViewer
                content={fileContent}
                loading={fileLoading}
                highlightLine={highlightLine}
              />
            )}


          </div>

        </main>
      </div>

      {/* Lexical Search Overlay */}
      {showSearchOverlay && (
        <SearchOverlay
          query={searchQuery}
          results={searchResults}
          loading={isSearching}
          onClose={() => setShowSearchOverlay(false)}
          onSelectResult={handleSelectSearchResult}
        />
      )}
    </div>
  );
}

export default App;
