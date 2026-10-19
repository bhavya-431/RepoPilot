import React, { useState } from 'react';
import { Folder, FolderOpen, FileCode, FileText, ChevronRight, ChevronDown } from 'lucide-react';
import type { FileTreeNode } from '../api';

interface FileTreeProps {
  node: FileTreeNode;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
  level?: number;
}

export const FileTreeItem: React.FC<FileTreeProps> = ({
  node,
  selectedPath,
  onSelectFile,
  level = 0,
}) => {
  const [isOpen, setIsOpen] = useState(level < 2);

  if (node.is_dir) {
    // Hide root container label if empty path
    if (node.path === '') {
      return (
        <div>
          {node.children.map((child) => (
            <FileTreeItem
              key={child.path}
              node={child}
              selectedPath={selectedPath}
              onSelectFile={onSelectFile}
              level={level}
            />
          ))}
        </div>
      );
    }

    return (
      <div>
        <div
          className="tree-node"
          style={{ paddingLeft: `${level * 14 + 6}px` }}
          onClick={() => setIsOpen(!isOpen)}
        >
          {isOpen ? (
            <ChevronDown className="tree-node-icon" style={{ width: 12, height: 12 }} />
          ) : (
            <ChevronRight className="tree-node-icon" style={{ width: 12, height: 12 }} />
          )}
          {isOpen ? (
            <FolderOpen className="tree-node-icon" style={{ color: '#60a5fa' }} />
          ) : (
            <Folder className="tree-node-icon" style={{ color: '#93c5fd' }} />
          )}
          <span>{node.name}</span>
        </div>
        {isOpen && (
          <div>
            {node.children.map((child) => (
              <FileTreeItem
                key={child.path}
                node={child}
                selectedPath={selectedPath}
                onSelectFile={onSelectFile}
                level={level + 1}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  const isSelected = selectedPath === node.path;
  const isPython = node.name.endsWith('.py');

  return (
    <div
      className={`tree-node ${isSelected ? 'active' : ''}`}
      style={{ paddingLeft: `${level * 14 + 18}px` }}
      onClick={() => onSelectFile(node.path)}
    >
      {isPython ? (
        <FileCode className="tree-node-icon" style={{ color: '#38bdf8' }} />
      ) : (
        <FileText className="tree-node-icon" style={{ color: '#9ca3af' }} />
      )}
      <span>{node.name}</span>
    </div>
  );
};
