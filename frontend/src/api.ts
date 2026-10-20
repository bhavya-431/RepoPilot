export interface RepoInfo {
  repo_id: string;
  name: string;
  root_path: string;
  manifest_type?: string | null;
  has_git: boolean;
  test_framework?: string | null;
}

export interface FileTreeNode {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  children: FileTreeNode[];
}

export interface FileLine {
  line_number: number;
  content: string;
}

export interface FileContent {
  file_path: string;
  total_lines: number;
  start_line: number;
  end_line: number;
  lines: { line_number: number; content: string }[];
  raw_text: string;
}

export interface SearchResultItem {
  file_path: string;
  line_number: number;
  line_content: string;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  results: SearchResultItem[];
}

export interface EvidenceCitation {
  file_path: string;
  start_line: number;
  end_line: number;
  snippet: string;
  explanation: string;
}

export interface InvestigationRequest {
  repo_id: string;
  issue_description: string;
  traceback?: string;
  target_files?: string[];
}

export interface InvestigationResponse {
  investigation_id: string;
  repo_id: string;
  status: string;
  root_cause: string;
  evidence: EvidenceCitation[];
  suggested_fix: string;
  recommended_test?: string | null;
  confidence: number;
  known_uncertainties?: string | null;
  provider_name?: string;
  execution_mode?: string;
  latency_seconds?: number | null;
}

export interface SystemStatus {
  status: string;
  ollama_online: boolean;
  models: string[];
  active_model: string;
}

// Configurable via VITE_API_URL (e.g. 'http://localhost:8000/api' or 'http://localhost:8000')
const rawEnvUrl = import.meta.env.VITE_API_URL?.trim();
export const API_BASE = rawEnvUrl
  ? (rawEnvUrl.endsWith('/api') ? rawEnvUrl : `${rawEnvUrl.replace(/\/+$/, '')}/api`)
  : 'http://localhost:8000/api';

export const BACKEND_ROOT = API_BASE.replace(/\/api\/?$/, '');

export const api = {
  async getSystemStatus(): Promise<SystemStatus> {
    const res = await fetch(`${API_BASE}/system/status`);
    if (!res.ok) throw new Error('Failed to query system status');
    return res.json();
  },

  async registerRepo(path: string): Promise<RepoInfo> {
    const res = await fetch(`${API_BASE}/repositories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to register repository' }));
      throw new Error(err.detail || 'Failed to register repository');
    }
    return res.json();
  },

  async listRepos(): Promise<RepoInfo[]> {
    const res = await fetch(`${API_BASE}/repositories`);
    if (!res.ok) throw new Error('Failed to fetch repositories');
    return res.json();
  },

  async getTree(repoId: string): Promise<FileTreeNode> {
    const res = await fetch(`${API_BASE}/repositories/${repoId}/tree`);
    if (!res.ok) throw new Error('Failed to fetch repository tree');
    return res.json();
  },

  async getFile(repoId: string, path: string, start?: number, end?: number): Promise<FileContent> {
    const params = new URLSearchParams({ path });
    if (start) params.append('start', start.toString());
    if (end) params.append('end', end.toString());

    const res = await fetch(`${API_BASE}/repositories/${repoId}/files?${params.toString()}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to load file' }));
      throw new Error(err.detail || 'Failed to load file');
    }
    return res.json();
  },

  async searchRepo(repoId: string, q: string): Promise<SearchResponse> {
    const res = await fetch(`${API_BASE}/repositories/${repoId}/search?q=${encodeURIComponent(q)}`);
    if (!res.ok) throw new Error('Search failed');
    return res.json();
  },

  async investigate(req: InvestigationRequest): Promise<InvestigationResponse> {
    const res = await fetch(`${API_BASE}/investigate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Investigation failed' }));
      throw new Error(err.detail || 'Investigation failed');
    }
    return res.json();
  },

  async generatePatch(req: GeneratePatchRequest): Promise<PatchProposalResponse> {
    const res = await fetch(`${API_BASE}/patches/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to generate patch' }));
      throw new Error(err.detail || 'Failed to generate patch');
    }
    return res.json();
  },

  async approvePatch(patchId: string): Promise<PatchProposalResponse> {
    const res = await fetch(`${API_BASE}/patches/${patchId}/approve`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to approve patch' }));
      throw new Error(err.detail || 'Failed to approve patch');
    }
    return res.json();
  },

  async rejectPatch(patchId: string, reason?: string): Promise<PatchProposalResponse> {
    const res = await fetch(`${API_BASE}/patches/${patchId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patch_id: patchId, reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to reject patch' }));
      throw new Error(err.detail || 'Failed to reject patch');
    }
    return res.json();
  },

  async runTests(req: RunTestRequest): Promise<TestExecutionResponse> {
    const res = await fetch(`${API_BASE}/tests/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to run tests' }));
      throw new Error(err.detail || 'Failed to run tests');
    }
    return res.json();
  },

  async startRepairSession(params: {
    repo_id: string;
    target_file: string;
    issue_description: string;
    root_cause: string;
    test_target?: string;
    max_iterations?: number;
  }): Promise<RepairSessionResponse> {
    const q = new URLSearchParams({
      repo_id: params.repo_id,
      target_file: params.target_file,
      issue_description: params.issue_description,
      root_cause: params.root_cause,
      test_target: params.test_target || 'test_expense.py',
      max_iterations: (params.max_iterations || 2).toString(),
    });
    const res = await fetch(`${API_BASE}/repair/start?${q.toString()}`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to start repair session' }));
      throw new Error(err.detail || 'Failed to start repair session');
    }
    return res.json();
  },

  async iterateRepair(sessionId: string, feedback?: string): Promise<RepairSessionResponse> {
    const q = feedback ? `?feedback=${encodeURIComponent(feedback)}` : '';
    const res = await fetch(`${API_BASE}/repair/${sessionId}/iterate${q}`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to execute repair iteration' }));
      throw new Error(err.detail || 'Failed to execute repair iteration');
    }
    return res.json();
  },

  async getVerificationReport(sessionId: string): Promise<VerificationReportResponse> {
    const res = await fetch(`${API_BASE}/repair/${sessionId}/report`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to get verification report' }));
      throw new Error(err.detail || 'Failed to get verification report');
    }
    return res.json();
  },
};

export interface GeneratePatchRequest {
  repo_id: string;
  target_file: string;
  issue_description: string;
  suggested_fix: string;
  root_cause?: string;
}

export interface PatchFileDiff {
  file_path: string;
  diff_text: string;
  added_count: number;
  removed_count: number;
  is_applicable: boolean;
  validation_error?: string | null;
}

export interface PatchProposalResponse {
  patch_id: string;
  repo_id: string;
  version: string;
  target_file: string;
  explanation: string;
  diff: PatchFileDiff;
  status: string; // 'pending_review' | 'approved' | 'rejected' | 'applied'
  provider_name?: string;
  execution_mode?: string;
  latency_seconds?: number | null;
}

export interface RunTestRequest {
  repo_id: string;
  test_target?: string;
  timeout_seconds?: number;
}

export interface TestExecutionResponse {
  execution_id: string;
  repo_id: string;
  command: string;
  status: 'passed' | 'failed' | 'timeout' | 'error';
  exit_code?: number | null;
  passed_count: number;
  failed_count: number;
  error_count: number;
  duration_seconds: number;
  stdout: string;
  stderr: string;
  failure_traceback?: string | null;
}

export interface RepairIteration {
  iteration_number: number;
  patch_id?: string | null;
  version: string;
  patch_explanation?: string | null;
  test_status?: string | null;
  test_stdout?: string | null;
  failure_traceback?: string | null;
  timestamp: string;
}

export interface RepairSessionResponse {
  session_id: string;
  repo_id: string;
  target_file: string;
  max_iterations: number;
  current_iteration: number;
  status: 'in_progress' | 'verified' | 'max_iterations_reached' | 'failed';
  iterations: RepairIteration[];
  final_verdict: string;
}

export interface VerificationReportResponse {
  report_id: string;
  repo_id: string;
  repo_name: string;
  session_id: string;
  timestamp: string;
  status: string;
  root_cause: string;
  fix_applied: string;
  tests_verified: boolean;
  iterations_taken: number;
  audit_events: Array<{ timestamp: string; event_type: string; details: any }>;
  markdown_report: string;
}




