import React, { useState } from 'react';
import { ArgumentItem } from '../services/api';
import './ArgumentEditor.css';

interface ArgumentEditorProps {
  arguments: ArgumentItem[];
  facts: Array<{ fact_id: string; fact: string }>;
  onAddArgument: (argument: string, factIds: string[]) => void;
  onUpdateArgument: (argumentId: string, argument: string, factIds: string[]) => void;
  onApproveArgument: (argumentId: string) => void;
  onRejectArgument: (argumentId: string) => void;
  onLockArgument: (argumentId: string) => void;
  loading: boolean;
}

const ArgumentEditor: React.FC<ArgumentEditorProps> = ({
  arguments,
  facts,
  onAddArgument,
  onUpdateArgument,
  onApproveArgument,
  onRejectArgument,
  onLockArgument,
  loading,
}) => {
  const [showForm, setShowForm] = useState(false);
  const [newArgument, setNewArgument] = useState('');
  const [selectedFactIds, setSelectedFactIds] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editArgument, setEditArgument] = useState('');
  const [editFactIds, setEditFactIds] = useState<string[]>([]);

  const handleAddArgument = () => {
    if (newArgument.trim() && selectedFactIds.length > 0) {
      onAddArgument(newArgument, selectedFactIds);
      setNewArgument('');
      setSelectedFactIds([]);
      setShowForm(false);
    }
  };

  const handleSaveEdit = (argumentId: string) => {
    if (editArgument.trim() && editFactIds.length > 0) {
      onUpdateArgument(argumentId, editArgument, editFactIds);
      setEditingId(null);
    }
  };

  const startEdit = (arg: ArgumentItem) => {
    setEditingId(arg.argument_id);
    setEditArgument(arg.argument);
    setEditFactIds(arg.fact_ids);
  };

  const toggleFactSelection = (factId: string, isEditMode: boolean) => {
    const setter = isEditMode ? setEditFactIds : setSelectedFactIds;
    const current = isEditMode ? editFactIds : selectedFactIds;
    if (current.includes(factId)) {
      setter(current.filter((id) => id !== factId));
    } else {
      setter([...current, factId]);
    }
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
    <div className="argument-editor">
      <div className="argument-editor-header">
        <h3>Arguments ({arguments.length})</h3>
        <button onClick={() => setShowForm(!showForm)} className="btn-secondary">
          {showForm ? '× Close' : '+ Add Argument'}
        </button>
      </div>

      {showForm && (
        <div className="argument-form">
          <textarea
            placeholder="Enter legal argument"
            value={newArgument}
            onChange={(e) => setNewArgument(e.target.value)}
            className="textarea-field"
            rows={4}
          />
          <div className="fact-selector">
            <label>Select supporting facts:</label>
            <div className="fact-checkboxes">
              {facts.map((fact) => (
                <label key={fact.fact_id} className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={selectedFactIds.includes(fact.fact_id)}
                    onChange={() => toggleFactSelection(fact.fact_id, false)}
                  />
                  <span>{fact.fact.substring(0, 50)}...</span>
                </label>
              ))}
            </div>
          </div>
          <div className="form-actions">
            <button onClick={handleAddArgument} className="btn-primary" disabled={loading || selectedFactIds.length === 0}>
              {loading ? 'Saving...' : 'Save Argument'}
            </button>
            <button onClick={() => setShowForm(false)} className="btn-secondary">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="argument-list">
        {arguments.map((arg) => (
          <div key={arg.argument_id} className="argument-item">
            {editingId === arg.argument_id ? (
              <div className="argument-edit-form">
                <textarea
                  value={editArgument}
                  onChange={(e) => setEditArgument(e.target.value)}
                  className="textarea-field"
                  rows={4}
                />
                <div className="fact-selector">
                  <label>Supporting facts:</label>
                  <div className="fact-checkboxes">
                    {facts.map((fact) => (
                      <label key={fact.fact_id} className="checkbox-item">
                        <input
                          type="checkbox"
                          checked={editFactIds.includes(fact.fact_id)}
                          onChange={() => toggleFactSelection(fact.fact_id, true)}
                        />
                        <span>{fact.fact.substring(0, 50)}...</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="form-actions">
                  <button onClick={() => handleSaveEdit(arg.argument_id)} className="btn-primary">
                    Save
                  </button>
                  <button onClick={() => setEditingId(null)} className="btn-secondary">
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="argument-content">
                  <p className="argument-text">{arg.argument}</p>
                  <div className="argument-details">
                    <div className="supporting-facts">
                      <strong>Based on {arg.fact_ids.length} fact(s)</strong>
                    </div>
                    <span
                      className="status"
                      style={{ backgroundColor: getStatusColor(arg.status), color: 'white', padding: '2px 8px', borderRadius: '4px' }}
                    >
                      {arg.status}
                    </span>
                  </div>
                </div>
                <div className="argument-actions">
                  {arg.status === 'pending' && (
                    <>
                      <button onClick={() => startEdit(arg)} className="btn-edit">
                        Edit
                      </button>
                      <button onClick={() => onApproveArgument(arg.argument_id)} className="btn-approve">
                        ✓ Approve
                      </button>
                      <button onClick={() => onRejectArgument(arg.argument_id)} className="btn-reject">
                        ✗ Reject
                      </button>
                    </>
                  )}
                  {arg.status === 'approved' && (
                    <button onClick={() => onLockArgument(arg.argument_id)} className="btn-lock">
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

export default ArgumentEditor;
