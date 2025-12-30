import React from 'react';
import { CaseInfo } from '../services/api';
import './CaseList.css';

interface CaseListProps {
  cases: CaseInfo[];
  onSelectCase: (caseId: string) => void;
  onCreateCase: () => void;
  loading: boolean;
}

const CaseList: React.FC<CaseListProps> = ({ cases, onSelectCase, onCreateCase, loading }) => {
  if (loading) {
    return <div className="case-list loading">Loading cases...</div>;
  }

  return (
    <div className="case-list">
      <div className="case-list-header">
        <h2>Cases</h2>
        <button onClick={onCreateCase} className="btn-primary">
          + New Case
        </button>
      </div>

      {cases.length === 0 ? (
        <div className="empty-state">
          <p>No cases found. Create a new case to get started.</p>
        </div>
      ) : (
        <ul className="case-items">
          {cases.map((caseItem) => (
            <li key={caseItem.case_id} className="case-item" onClick={() => onSelectCase(caseItem.case_id)}>
              <div className="case-name">{caseItem.case_name}</div>
              <div className="case-meta">
                <span className="status">{caseItem.status}</span>
                <span className="fact-count">{caseItem.fact_count} facts</span>
                <span className="arg-count">{caseItem.argument_count} arguments</span>
              </div>
              <div className="case-time">Created: {new Date(caseItem.created_at).toLocaleDateString()}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default CaseList;
