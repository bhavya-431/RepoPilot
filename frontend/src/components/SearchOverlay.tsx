import React from 'react';
import type { SearchResultItem } from '../api';
import { Search, X, CornerDownRight } from 'lucide-react';

interface SearchOverlayProps {
  query: string;
  results: SearchResultItem[];
  loading: boolean;
  onClose: () => void;
  onSelectResult: (filePath: string, lineNumber: number) => void;
}

export const SearchOverlay: React.FC<SearchOverlayProps> = ({
  query,
  results,
  loading,
  onClose,
  onSelectResult,
}) => {
  return (
    <div className="search-results-overlay">
      <div className="search-results-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Search style={{ width: 16, height: 16, color: '#3b82f6' }} />
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>
              Search Results for <span style={{ color: '#60a5fa' }}>"{query}"</span>
            </h3>
            <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>({results.length} found)</span>
          </div>
          <button className="btn btn-secondary" onClick={onClose} style={{ padding: '0.25rem 0.5rem' }}>
            <X style={{ width: 14, height: 14 }} /> Close
          </button>
        </div>

        {loading ? (
          <p style={{ color: '#9ca3af', padding: '1rem 0' }}>Searching repository files...</p>
        ) : results.length === 0 ? (
          <p style={{ color: '#9ca3af', padding: '1rem 0' }}>No occurrences found for this query.</p>
        ) : (
          <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
            {results.map((r, i) => (
              <div
                key={`${r.file_path}-${r.line_number}-${i}`}
                className="search-result-item"
                onClick={() => onSelectResult(r.file_path, r.line_number)}
              >
                <div className="search-result-meta">
                  <span>{r.file_path}:{r.line_number}</span>
                  <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <CornerDownRight style={{ width: 12, height: 12 }} /> Jump to line
                  </span>
                </div>
                <div className="search-result-snippet">{r.line_content}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
