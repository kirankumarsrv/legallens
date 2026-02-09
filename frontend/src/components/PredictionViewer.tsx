import React from 'react';
import ReactMarkdown from 'react-markdown';
import { PredictionHistoryItem } from '../services/api';
import './PredictionViewer.css';

interface PredictionViewerProps {
  prediction: string;
  confidence: number;
  history: PredictionHistoryItem[];
  onRestore: (index: number) => void;
  loading: boolean;
}

const PredictionViewer: React.FC<PredictionViewerProps> = ({ prediction, confidence, history, onRestore, loading }) => {
  return (
    <div className="prediction-viewer">
      <div className="prediction-header">
        <h3>🎯 Outcome Prediction</h3>
        <span className="section-badge">AI Generated</span>
      </div>

      {prediction ? (
        <div className="prediction-content">
          <div className="prediction-box">
            <div className="prediction-text">
              {prediction.split('\n\n').map((para, idx) => (
                <div key={idx} className="prediction-paragraph">
                  <ReactMarkdown>{para}</ReactMarkdown>
                </div>
              ))}
            </div>
            <div className="confidence-section">
              <label className="confidence-label">Confidence Level</label>
              <div className="confidence-meter">
                <div 
                  className="confidence-bar" 
                  style={{ 
                    width: `${confidence * 100}%`,
                    background: confidence > 0.7 ? 'linear-gradient(90deg, #27ae60 0%, #16a085 100%)' : 
                                confidence > 0.4 ? 'linear-gradient(90deg, #f39c12 0%, #e67e22 100%)' :
                                'linear-gradient(90deg, #e74c3c 0%, #c0392b 100%)'
                  }}>
                  <span className="confidence-text">{(confidence * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>
          </div>

          {history.length > 1 && (
            <div className="history-section">
              <h4>📜 Prediction History</h4>
              <div className="history-list">
                {history.map((item, index) => (
                  <div key={index} className="history-item">
                    <div className="history-content">
                      <p className="history-text">{item.prediction.substring(0, 150)}...</p>
                      <div className="history-details">
                        <span className="timestamp">🕒 {new Date(item.timestamp).toLocaleString()}</span>
                        <span className="confidence">📊 {(item.confidence * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                    <button
                      onClick={() => onRestore(index)}
                      disabled={loading}
                      className="btn-restore"
                    >
                      ↺ Restore
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="empty-prediction">
          <div className="empty-icon">🎯</div>
          <p>No prediction yet. Complete facts and arguments to generate prediction.</p>
        </div>
      )}
    </div>
  );
};

export default PredictionViewer;
