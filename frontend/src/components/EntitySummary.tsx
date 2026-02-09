import React, { useState, useEffect } from 'react';
import { entityAPI } from '../services/api';
import './EntitySummary.css';

interface EntitySummaryProps {
  caseId: string;
  onRefresh?: () => void;
}

interface NormalizedEntities {
  persons?: string[];
  dates?: string[];
  sections?: string[];
  case_numbers?: string[];
  locations?: string[];
  organizations?: string[];
  authorities?: string[];
  amounts?: string[];
}

const EntitySummary: React.FC<EntitySummaryProps> = ({ caseId, onRefresh }) => {
  const [entities, setEntities] = useState<NormalizedEntities>({});
  const [canonicalMap, setCanonicalMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});

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

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => ({ ...prev, [category]: !prev[category] }));
  };

  const getCategoryIcon = (type: string): string => {
    const icons: Record<string, string> = {
      persons: '👤',
      dates: '📅',
      organizations: '🏢',
      locations: '📍',
      sections: '⚖️',
      case_numbers: '🔢',
      authorities: '🏛️',
      amounts: '💰',
    };
    return icons[type] || '📋';
  };

  const getCategoryColor = (type: string): string => {
    const colors: Record<string, string> = {
      persons: '#667eea',
      dates: '#4ECDC4',
      organizations: '#45B7D1',
      locations: '#96CEB4',
      sections: '#FFEAA7',
      case_numbers: '#DFE6E9',
      authorities: '#A29BFE',
      amounts: '#50E3C2',
    };
    return colors[type] || '#95A5A6';
  };

  const totalEntities = Object.values(entities).reduce((sum, arr) => sum + (arr?.length || 0), 0);

  if (loading) {
    return <div className="entity-summary-loading">Loading entities...</div>;
  }

  return (
    <div className="entity-summary">
      <div className="entity-header">
        <h3>🏷️ Entity Summary</h3>
        <div className="entity-stats">
          <span className="total-count">All ({totalEntities})</span>
          <button className="btn-refresh" onClick={loadEntities} title="Refresh entities">
            ↻
          </button>
        </div>
      </div>

      {error && <div className="entity-error">{error}</div>}

      {totalEntities === 0 ? (
        <div className="entity-empty">No entities extracted yet. Upload evidence or run compute to extract entities.</div>
      ) : (
        <div className="entity-categories">
          {Object.entries(entities).map(([category, items]) => {
            if (!items || items.length === 0) return null;
            const isExpanded = expandedCategories[category];
            
            return (
              <div key={category} className="entity-category">
                <div 
                  className="category-header"
                  onClick={() => toggleCategory(category)}
                  style={{ borderLeftColor: getCategoryColor(category) }}
                >
                  <div className="category-title">
                    <span className="category-icon">{getCategoryIcon(category)}</span>
                    <span className="category-name">{category.replace('_', ' ')}</span>
                    <span className="category-count">({items.length})</span>
                  </div>
                  <button className="expand-btn">
                    {isExpanded ? '×' : '→'}
                  </button>
                </div>
                
                {isExpanded && (
                  <div className="category-content">
                    {items.map((item: string, idx: number) => (
                      <div key={idx} className="entity-tag">
                        <span className="tag-text">{item}</span>
                        {canonicalMap[item] && canonicalMap[item] !== item && (
                          <span className="tag-canonical" title={`Normalized from: ${canonicalMap[item]}`}>
                            ⟳
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default EntitySummary;
