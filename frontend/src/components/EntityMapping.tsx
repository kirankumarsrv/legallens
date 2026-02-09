import React, { useState, useEffect } from 'react';
import { entityAPI } from '../services/api';
import './EntityMapping.css';

interface EntityMappingProps {
  caseId: string;
  onRefresh?: () => void;
}

const EntityMapping: React.FC<EntityMappingProps> = ({ caseId, onRefresh }) => {
  const [canonicalMap, setCanonicalMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    loadMapping();
  }, [caseId]);

  const loadMapping = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await entityAPI.getEntities(caseId);
      const mappedData = data.canonical_map || {};
      // Filter to only show actual mappings (where from !== to)
      const mappings = Object.fromEntries(
        Object.entries(mappedData).filter(([from, to]) => from !== to)
      );
      setCanonicalMap(mappings);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load entity mapping');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="mapping-loading">Loading entity mappings...</div>;
  }

  return (
    <div className="entity-mapping">
      <div className="mapping-header">
        <h3>🔄 Entity Normalization</h3>
        <button className="btn-refresh" onClick={loadMapping} title="Refresh">
          ↻
        </button>
      </div>

      {error && <div className="mapping-error">{error}</div>}

      {Object.keys(canonicalMap).length === 0 ? (
        <div className="mapping-empty">
          ✅ No duplicates found. All entities have unique names.
        </div>
      ) : (
        <div className="mapping-list">
          <p className="mapping-intro">
            The following variations were consolidated into canonical forms:
          </p>
          <div className="mappings-grid">
            {Object.entries(canonicalMap).map(([original, canonical]) => (
              <div key={original} className="mapping-item">
                <div className="mapping-flow">
                  <div className="mapping-original">
                    <span className="variation-badge">Variation</span>
                    <span className="variation-text">{original}</span>
                  </div>

                  <div className="mapping-arrow">
                    <span className="arrow-icon">→</span>
                    <span className="arrow-label">Normalized to</span>
                  </div>

                  <div className="mapping-canonical">
                    <span className="canonical-badge">Canonical</span>
                    <span className="canonical-text">{canonical}</span>
                  </div>
                </div>

                <div className="mapping-similarity">
                  <span className="similarity-score">Similar entity consolidated</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mapping-summary">
            <h4>Normalization Summary</h4>
            <ul>
              <li>
                <strong>{Object.keys(canonicalMap).length}</strong> variations identified
              </li>
              <li>
                <strong>{new Set(Object.values(canonicalMap)).size}</strong> canonical forms created
              </li>
              <li>Fuzzy matching threshold: <strong>85% similarity</strong></li>
              <li>Methods used: Token-based matching, initial matching, phonetic similarity</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default EntityMapping;
