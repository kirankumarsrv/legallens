import React, { useState, useEffect } from 'react';
import { entityAPI, EntityItem } from '../services/api';
import './EntitySummary.css';

interface EntitySummaryProps {
  caseId: string;
  onRefresh?: () => void;
}

const EntitySummary: React.FC<EntitySummaryProps> = ({ caseId, onRefresh }) => {
  const [entities, setEntities] = useState<Record<string, EntityItem>>({});
  const [canonicalMap, setCanonicalMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadEntities();
  }, [caseId]);

  const loadEntities = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await entityAPI.getEntities(caseId);
      setEntities(data.normalized_entities || {});
      setCanonicalMap(data.canonical_map || {});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load entities');
    } finally {
      setLoading(false);
    }
  };

  const getEntityTypeBadgeColor = (type: string): string => {
    const colors: Record<string, string> = {
      person: '#FF6B6B',
      date: '#4ECDC4',
      organization: '#45B7D1',
      location: '#96CEB4',
      section: '#FFEAA7',
      fir_number: '#DFE6E9',
      case_number: '#DFE6E9',
      authority: '#A29BFE',
    };
    return colors[type] || '#95A5A6';
  };

  const filterEntities = () => {
    if (filter === 'all') return entities;
    return Object.fromEntries(
      Object.entries(entities).filter(([_, item]) => item.type === filter)
    );
  };

  const filteredEntities = filterEntities();

  if (loading) {
    return <div className="entity-summary-loading">Loading entities...</div>;
  }

  return (
    <div className="entity-summary">
      <div className="entity-header">
        <h3>🏷️ Entity Summary</h3>
        <button className="btn-refresh" onClick={loadEntities} title="Refresh entities">
          ↻
        </button>
      </div>

      {error && <div className="entity-error">{error}</div>}

      <div className="entity-filters">
        <button
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All ({Object.keys(entities).length})
        </button>
        <button
          className={`filter-btn ${filter === 'person' ? 'active' : ''}`}
          onClick={() => setFilter('person')}
        >
          Persons ({Object.values(entities).filter(e => e.type === 'person').length})
        </button>
        <button
          className={`filter-btn ${filter === 'date' ? 'active' : ''}`}
          onClick={() => setFilter('date')}
        >
          Dates ({Object.values(entities).filter(e => e.type === 'date').length})
        </button>
        <button
          className={`filter-btn ${filter === 'organization' ? 'active' : ''}`}
          onClick={() => setFilter('organization')}
        >
          Organizations ({Object.values(entities).filter(e => e.type === 'organization').length})
        </button>
        <button
          className={`filter-btn ${filter === 'location' ? 'active' : ''}`}
          onClick={() => setFilter('location')}
        >
          Locations ({Object.values(entities).filter(e => e.type === 'location').length})
        </button>
        <button
          className={`filter-btn ${filter === 'section' ? 'active' : ''}`}
          onClick={() => setFilter('section')}
        >
          Sections ({Object.values(entities).filter(e => e.type === 'section').length})
        </button>
      </div>

      {Object.keys(filteredEntities).length === 0 ? (
        <div className="entity-empty">No entities found</div>
      ) : (
        <div className="entity-list">
          {Object.entries(filteredEntities).map(([name, entity]) => (
            <div key={name} className="entity-item">
              <div className="entity-name">
                <span
                  className="entity-badge"
                  style={{ backgroundColor: getEntityTypeBadgeColor(entity.type) }}
                >
                  {entity.type}
                </span>
                <span className="entity-text">{name}</span>
                <span className="entity-count">{entity.count}x</span>
              </div>

              {entity.roles && entity.roles.length > 0 && (
                <div className="entity-roles">
                  {entity.roles.map((role, idx) => (
                    <span key={idx} className="role-badge">
                      {role}
                    </span>
                  ))}
                </div>
              )}

              {canonicalMap[name] && canonicalMap[name] !== name && (
                <div className="entity-normalized">
                  <small>📌 Normalized from: {canonicalMap[name]}</small>
                </div>
              )}

              {entity.evidence_source && (
                <div className="entity-source">
                  <small>📄 Source: {entity.evidence_source}</small>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default EntitySummary;
