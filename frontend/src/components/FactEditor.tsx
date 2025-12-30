import React, { useState } from 'react';
import { FactItem } from '../services/api';
import './FactEditor.css';

interface FactEditorProps {
  facts: FactItem[];
  onAddFact: (fact: string, source: string) => void;
  onUpdateFact: (factId: string, fact: string, source: string) => void;
  onApproveFact: (factId: string) => void;
  onRejectFact: (factId: string) => void;
  onLockFact: (factId: string) => void;
  loading: boolean;
}

const FactEditor: React.FC<FactEditorProps> = ({
  facts,
  onAddFact,
  onUpdateFact,
  onApproveFact,
  onRejectFact,
  onLockFact,
  loading,
}) => {
  const [showForm, setShowForm] = useState(false);
  const [newFact, setNewFact] = useState('');
  const [newSource, setNewSource] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editFact, setEditFact] = useState('');
  const [editSource, setEditSource] = useState('');

  const handleAddFact = () => {
    if (newFact.trim() && newSource.trim()) {
      onAddFact(newFact, newSource);
      setNewFact('');
      setNewSource('');
      setShowForm(false);
    }
  };

  const handleSaveEdit = (factId: string) => {
    if (editFact.trim() && editSource.trim()) {
      onUpdateFact(factId, editFact, editSource);
      setEditingId(null);
    }
  };

  const startEdit = (fact: FactItem) => {
    setEditingId(fact.fact_id);
    setEditFact(fact.fact);
    setEditSource(fact.source);
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: '#FFA500',
      approved: '#4CAF50',
      rejected: '#F44336',
      locked: '#2196F3',
    };
    return colors[status] || '#666';
  };

  return (
    <div className="fact-editor">
      <div className="fact-editor-header">
        <h3>Facts ({facts.length})</h3>
        <button onClick={() => setShowForm(!showForm)} className="btn-secondary">
          {showForm ? '× Close' : '+ Add Fact'}
        </button>
      </div>

      {showForm && (
        <div className="fact-form">
          <input
            type="text"
            placeholder="Enter fact"
            value={newFact}
            onChange={(e) => setNewFact(e.target.value)}
            className="input-field"
          />
          <input
            type="text"
            placeholder="Source (evidence/document)"
            value={newSource}
            onChange={(e) => setNewSource(e.target.value)}
            className="input-field"
          />
          <div className="form-actions">
            <button onClick={handleAddFact} className="btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Save Fact'}
            </button>
            <button onClick={() => setShowForm(false)} className="btn-secondary">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="fact-list">
        {facts.map((fact) => (
          <div key={fact.fact_id} className="fact-item">
            {editingId === fact.fact_id ? (
              <div className="fact-edit-form">
                <textarea
                  value={editFact}
                  onChange={(e) => setEditFact(e.target.value)}
                  className="textarea-field"
                />
                <input
                  type="text"
                  value={editSource}
                  onChange={(e) => setEditSource(e.target.value)}
                  className="input-field"
                />
                <div className="form-actions">
                  <button onClick={() => handleSaveEdit(fact.fact_id)} className="btn-primary">
                    Save
                  </button>
                  <button onClick={() => setEditingId(null)} className="btn-secondary">
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="fact-content">
                  <p className="fact-text">{fact.fact}</p>
                  <div className="fact-details">
                    <span className="source">📄 {fact.source}</span>
                    <span
                      className="status"
                      style={{ backgroundColor: getStatusColor(fact.status), color: 'white', padding: '2px 8px', borderRadius: '4px' }}
                    >
                      {fact.status}
                    </span>
                  </div>
                </div>
                <div className="fact-actions">
                  {fact.status === 'pending' && (
                    <>
                      <button onClick={() => startEdit(fact)} className="btn-edit">
                        Edit
                      </button>
                      <button onClick={() => onApproveFact(fact.fact_id)} className="btn-approve">
                        ✓ Approve
                      </button>
                      <button onClick={() => onRejectFact(fact.fact_id)} className="btn-reject">
                        ✗ Reject
                      </button>
                    </>
                  )}
                  {fact.status === 'approved' && (
                    <button onClick={() => onLockFact(fact.fact_id)} className="btn-lock">
                      🔒 Lock
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default FactEditor;
