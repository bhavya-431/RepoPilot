# RepoPilot — Autonomous Software Engineering Agent

<p align="center">
  <strong>Grounded Bug Investigation • Surgical Patch Review • Controlled Test Verification • Bounded Self-Repair</strong>
</p>

---

## 🚀 Overview
**RepoPilot** is an autonomous, free, local-first AI Software Engineering Agent. Powered by a local Ollama daemon using open-weights models (`gemma4:latest`), RepoPilot investigates bugs, inspects code evidence, synthesizes unified patches, requires explicit developer approval, and executes regression tests within an isolated sandbox.

---

## ✨ Core Highlights & Principles

1. **Free & Local-First:** Runs 100% locally with zero cloud API keys or token costs.
2. **Evidence Before Hypotheses:** Extracts actual code slices and requires verifiable line-range citations for every claim.
3. **Explicit Human Approval:** Patches are presented as clear unified diffs (`+N / -M`). Zero code is committed without developer sign-off.
4. **Controlled Execution Sandbox:** Only allowlisted `pytest` commands are permitted. Subprocesses have strict timeouts and output caps.
5. **Bounded Repair Loop:** Halts strictly after a maximum of 2 repair attempts with an immutable audit trail and exportable verification report.

---

## 🛠️ Architecture

```
RepoPilot/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── main.py           # REST API router & dependency injection
│   │   ├── repository.py     # Safe tree exploration & lexical code search
│   │   ├── security.py       # Path traversal checks & boundary verification
│   │   ├── llm.py            # BaseLLMProvider, OllamaProvider, MockLLMProvider
│   │   ├── investigator.py   # Grounded evidence extraction & diagnosis
│   │   ├── patcher.py        # Unified diff generator & conflict detector
│   │   ├── runner.py         # Subprocess test runner with timeout & output caps
│   │   ├── repair.py         # Bounded repair loop & audit trail orchestrator
│   │   └── schemas.py        # Pydantic v2 data models
│   └── tests/                # 19 automated pytest unit & security tests
├── frontend/                 # React 19 + TypeScript + Vite UI
│   ├── src/
│   │   ├── App.tsx           # Multi-phase workspace shell & navigation tabs
│   │   ├── api.ts            # Typed REST client
│   │   ├── index.css         # Developer-first dark design system
│   │   └── components/
│   │       ├── CodeViewer.tsx        # Line-numbered syntax viewer
│   │       ├── FileTree.tsx          # Hierarchical folder tree
│   │       ├── SearchOverlay.tsx     # Fast symbol search
│   │       ├── InvestigationPanel.tsx# Diagnosis & evidence cards
│   │       ├── DiffViewer.tsx        # Unified patch review & approval
│   │       ├── TestRunnerPanel.tsx   # Sandbox test runner & terminal logs
│   │       └── RepairAuditPanel.tsx  # Iteration timeline & report export
├── benchmarks/
│   └── sample_repo/          # Reproducible Python benchmark with known bug
└── docs/                     # Full technical documentation suite
    ├── ARCHITECTURE.md       # Subsystem breakdowns & Mermaid diagrams
    ├── LEARNING_GUIDE.md     # Technical interview & architecture deep-dive
    ├── API_REFERENCE.md      # OpenAPI endpoints & payload documentation
    ├── SECURITY.md           # Defensive design & threat model
    ├── DECISIONS.md          # Architecture Decision Records (ADRs)
    └── RECOVERY_REPORT.md    # Crash recovery & verification audit
```

---

## ⚡ Quickstart

### Prerequisites
- Python 3.11+
- Node.js v18+ & npm
- [Ollama](https://ollama.com/) with `gemma4:latest` (or any local GGUF model)

### 1. Start Ollama Daemon
```powershell
ollama run gemma4:latest
```

### 2. Start Backend API
```powershell
# In RepoPilot root:
$env:PYTHONPATH="backend"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Docs: `http://localhost:8000/docs`

### 3. Start Frontend UI
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Running the Verification Test Suite

RepoPilot includes 26 comprehensive unit, security, and integration tests across all phases:

```powershell
$env:PYTHONPATH="backend"
python -m pytest backend/tests -v
```

All 26 tests pass 100%:
- `test_repository.py` (File tree, safe slicing, traversal prevention, lexical search)
- `test_investigation.py` (Evidence extraction, mock & live inference schemas)
- `test_llm.py` (Ollama provider options, truncation safeguards, error diagnostics)
- `test_patcher.py` (Unified diffs, approval workflow, conflict detection, investigation-to-patch pipeline, logic validation)
- `test_runner.py` (Subprocess timeout caps, output bounds, pytest summary parser)
- `test_repair.py` (Bounded retry ceiling, audit logging, Markdown report synthesis)

---

## 📄 License
MIT License.
