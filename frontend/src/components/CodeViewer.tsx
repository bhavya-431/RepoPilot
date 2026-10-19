import React from 'react';
import type { FileContent } from '../api';
import { FileCode, ShieldCheck } from 'lucide-react';

interface CodeViewerProps {
  content: FileContent | null;
  loading: boolean;
  highlightLine?: number | null;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({
  content,
  loading,
  highlightLine,
}) => {
  if (loading) {
    return (
      <div className="empty-state">
        <p>Loading file contents safely...</p>
      </div>
    );
  }

  if (!content) {
    return (
      <div className="empty-state">
        <FileCode className="empty-state-icon" />
        <h3>No File Selected</h3>
        <p>Select a file from the repository explorer on the left to inspect its code.</p>
      </div>
    );
  }

  return (
    <div className="code-viewer-container">
      <div className="code-viewer-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FileCode style={{ width: 16, height: 16, color: '#38bdf8' }} />
          <span>{content.file_path}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.75rem', color: '#9ca3af' }}>
          <span>{content.total_lines} lines</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#10b981' }}>
            <ShieldCheck style={{ width: 14, height: 14 }} /> Boundary Verified
          </span>
        </div>
      </div>
      <div className="code-viewer-body">
        {content.lines.map((line) => {
          const isHighlighted = highlightLine === line.line_number;
          return (
            <div
              key={line.line_number}
              id={`line-${line.line_number}`}
              className="code-line"
              style={{
                backgroundColor: isHighlighted ? 'rgba(59, 130, 246, 0.2)' : undefined,
                borderLeft: isHighlighted ? '2px solid #3b82f6' : '2px solid transparent',
              }}
            >
              <div className="line-number">{line.line_number}</div>
              <div className="line-content">{line.content}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
