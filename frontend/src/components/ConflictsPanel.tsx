import React, { useState, useEffect } from 'react';
import { entityAPI, EntityConflict } from '../services/api';
import './ConflictsPanel.css';

interface ConflictsPanelProps {
  caseId: string;
  onRefresh?: () => void;
}

const ConflictsPanel: React.FC<ConflictsPanelProps> = ({ caseId, onRefresh }) => {
  const [conflicts, setConflicts] = useState<EntityConflict[]>([]);
  const [summary, setSummary] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [expandedConflict, setExpandedConflict] = useState<string | null>(null);

  useEffect(() => {
    loadConflicts();
  }, [caseId]);

  const loadConflicts = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await entityAPI.getConflicts(caseId);
      setConflicts(data.conflicts || []);
      setSummary(data.summary || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conflicts');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string): string => {
    const colors: Record<string, string> = {
      high: '#DC3545',
      medium: '#FFC107',
      low: '#28A745',
    };
    return colors[severity] || '#6C757D';
  };

  const getSeverityIcon = (severity: string): string => {
    const icons: Record<string, string> = {
      high: '🚨',
      medium: '⚠️',
      low: 'ℹ️',
    };
    return icons[severity] || '•';
  };

  if (loading) {
    return <div className="conflicts-loading">Loading conflicts...</div>;
  }

  return (
    <div className="conflicts-panel">
      <div className="conflicts-header">
        <h3>⚠️ Entity Conflicts</h3>
        {conflicts.length > 0 && (
          <span className="conflict-badge">{conflicts.length} issues</span>
        )}
        <button className="btn-refresh" onClick={loadConflicts} title="Refresh conflicts">
          ↻
        </button>
      </div>

      {error && <div className="conflicts-error">{error}</div>}

      {summary && (
        <div className="conflicts-summary">
          <strong>Summary:</strong>
          <div className="summary-text">{summary}</div>
        </div>
      )}

      {conflicts.length === 0 ? (
        <div className="conflicts-empty">
          ✅ No conflicts detected. All entities have clear roles.
        </div>
      ) : (
        <div className="conflicts-list">
          {conflicts
            .sort((a, b) => {
              const severityOrder = { high: 0, medium: 1, low: 2 };
              return (severityOrder[a.severity] ?? 3) - (severityOrder[b.severity] ?? 3);
            })
            .map((conflict, idx) => (
              <div key={idx} className={`conflict-item conflict-${conflict.severity}`}>
                <div
                  className="conflict-header-item"
                  onClick={() =>
                    setExpandedConflict(expandedConflict === conflict.entity_name ? null : conflict.entity_name)
                  }
                >
                  <span className="severity-icon">{getSeverityIcon(conflict.severity)}</span>
                  <div className="conflict-info">
                    <span className="conflict-entity">{conflict.entity_name}</span>
                    <span
                      className="severity-badge"
                      style={{ backgroundColor: getSeverityColor(conflict.severity) }}
                    >
                      {conflict.severity.toUpperCase()}
                    </span>
                  </div>
                  <span className="expand-icon">
                    {expandedConflict === conflict.entity_name ? '▼' : '▶'}
                  </span>
                </div>

                {expandedConflict === conflict.entity_name && (
                  <div className="conflict-details">
                    <div className="conflict-description">
                      <strong>Issue:</strong> {conflict.description}
                    </div>

                    <div className="conflict-roles">
                      <strong>Conflicting Roles:</strong>
                      <div className="roles-grid">
                        {conflict.roles.map((role, i) => (
                          <span key={i} className="role-tag">
                            {role}
                          </span>
                        ))}
                      </div>
                    </div>

                    {conflict.occurrences && conflict.occurrences.length > 0 && (
                      <div className="conflict-occurrences">
                        <strong>Found In:</strong>
                        <ul>
                          {conflict.occurrences.map((occ, i) => (
                            <li key={i}>
                              <em>{occ.source}</em>: "{occ.text}"
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="conflict-action">
                      <small>💡 A clarification question will be generated for this conflict.</small>
                    </div>
                  </div>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  );
};

export default ConflictsPanel;
