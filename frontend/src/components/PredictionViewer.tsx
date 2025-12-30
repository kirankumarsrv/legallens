import React from 'react';
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
        <h3>Outcome Prediction</h3>
      </div>

      {prediction ? (
        <div className="prediction-content">
          <div className="prediction-box">
            <p className="prediction-text">{prediction}</p>
            <div className="confidence-meter">
              <div className="confidence-bar" style={{ width: `${confidence * 100}%` }}>
                {(confidence * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          {history.length > 1 && (
            <div className="history-section">
              <h4>Prediction History</h4>
              <div className="history-list">
                {history.map((item, index) => (
                  <div key={index} className="history-item">
                    <div className="history-content">
                      <p className="history-text">{item.prediction.substring(0, 100)}...</p>
                      <div className="history-details">
                        <span className="timestamp">{new Date(item.timestamp).toLocaleString()}</span>
                        <span className="confidence">{(item.confidence * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                    <button
                      onClick={() => onRestore(index)}
                      disabled={loading}
                      className="btn-restore"
                    >
                      Restore
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="empty-prediction">
          <p>No prediction yet. Complete facts and arguments to generate prediction.</p>
        </div>
      )}
    </div>
  );
};

export default PredictionViewer;
