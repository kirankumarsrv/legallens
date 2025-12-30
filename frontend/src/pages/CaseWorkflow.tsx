import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  factAPI,
  argumentAPI,
  predictionAPI,
  stateAPI,
  FactItem,
  ArgumentItem,
  PredictionHistoryItem,
} from '../services/api';
import FactEditor from '../components/FactEditor';
import ArgumentEditor from '../components/ArgumentEditor';
import PredictionViewer from '../components/PredictionViewer';
import './CaseWorkflow.css';

const CaseWorkflow: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();

  const [facts, setFacts] = useState<FactItem[]>([]);
  const [arguments_, setArguments] = useState<ArgumentItem[]>([]);
  const [predictions, setPredictions] = useState<PredictionHistoryItem[]>([]);
  const [currentPrediction, setCurrentPrediction] = useState('');
  const [currentConfidence, setCurrentConfidence] = useState(0);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'facts' | 'arguments' | 'predictions'>('facts');

  if (!caseId) {
    return <div className="error">Case ID not found</div>;
  }

  useEffect(() => {
    loadCaseData();
  }, [caseId]);

  const loadCaseData = async () => {
    setLoading(true);
    try {
      const [factsData, argsData, predsData] = await Promise.all([
        factAPI.list(caseId),
        argumentAPI.list(caseId),
        predictionAPI.getHistory(caseId),
      ]);

      setFacts(factsData);
      setArguments(argsData);
      setPredictions(predsData);

      if (predsData.length > 0) {
        const latest = predsData[predsData.length - 1];
        setCurrentPrediction(latest.prediction);
        setCurrentConfidence(latest.confidence);
      }
    } catch (error) {
      console.error('Failed to load case data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddFact = async (fact: string, source: string) => {
    try {
      const newFact = await factAPI.create(caseId, { fact, source });
      setFacts([...facts, newFact]);
    } catch (error) {
      console.error('Failed to add fact:', error);
      alert('Failed to add fact');
    }
  };

  const handleUpdateFact = async (factId: string, fact: string, source: string) => {
    try {
      const updated = await factAPI.update(caseId, factId, { fact, source });
      setFacts(facts.map((f) => (f.fact_id === factId ? updated : f)));
    } catch (error) {
      console.error('Failed to update fact:', error);
      alert('Failed to update fact');
    }
  };

  const handleApproveFact = async (factId: string) => {
    try {
      const updated = await factAPI.approve(caseId, factId);
      setFacts(facts.map((f) => (f.fact_id === factId ? updated : f)));
    } catch (error) {
      console.error('Failed to approve fact:', error);
    }
  };

  const handleRejectFact = async (factId: string) => {
    try {
      const updated = await factAPI.reject(caseId, factId);
      setFacts(facts.map((f) => (f.fact_id === factId ? updated : f)));
    } catch (error) {
      console.error('Failed to reject fact:', error);
    }
  };

  const handleLockFact = async (factId: string) => {
    try {
      const updated = await factAPI.lock(caseId, factId);
      setFacts(facts.map((f) => (f.fact_id === factId ? updated : f)));
    } catch (error) {
      console.error('Failed to lock fact:', error);
    }
  };

  const handleAddArgument = async (argument: string, factIds: string[]) => {
    try {
      const newArg = await argumentAPI.create(caseId, { argument, fact_ids: factIds });
      setArguments([...arguments_, newArg]);
    } catch (error) {
      console.error('Failed to add argument:', error);
      alert('Failed to add argument');
    }
  };

  const handleUpdateArgument = async (argumentId: string, argument: string, factIds: string[]) => {
    try {
      const updated = await argumentAPI.update(caseId, argumentId, { argument, fact_ids: factIds });
      setArguments(arguments_.map((a) => (a.argument_id === argumentId ? updated : a)));
    } catch (error) {
      console.error('Failed to update argument:', error);
      alert('Failed to update argument');
    }
  };

  const handleApproveArgument = async (argumentId: string) => {
    try {
      const updated = await argumentAPI.approve(caseId, argumentId);
      setArguments(arguments_.map((a) => (a.argument_id === argumentId ? updated : a)));
    } catch (error) {
      console.error('Failed to approve argument:', error);
    }
  };

  const handleRejectArgument = async (argumentId: string) => {
    try {
      const updated = await argumentAPI.reject(caseId, argumentId);
      setArguments(arguments_.map((a) => (a.argument_id === argumentId ? updated : a)));
    } catch (error) {
      console.error('Failed to reject argument:', error);
    }
  };

  const handleLockArgument = async (argumentId: string) => {
    try {
      const updated = await argumentAPI.lock(caseId, argumentId);
      setArguments(arguments_.map((a) => (a.argument_id === argumentId ? updated : a)));
    } catch (error) {
      console.error('Failed to lock argument:', error);
    }
  };

  const handleRestorePrediction = async (index: number) => {
    try {
      await predictionAPI.restore(caseId, index);
      loadCaseData();
    } catch (error) {
      console.error('Failed to restore prediction:', error);
      alert('Failed to restore prediction');
    }
  };

  const progressPercent =
    Math.round(
      ((facts.filter((f) => f.status === 'locked').length * 0.3 +
        arguments_.filter((a) => a.status === 'locked').length * 0.3 +
        (currentPrediction ? 0.4 : 0)) /
        1) *
        100
    ) || 0;

  if (loading) {
    return <div className="loading-page">Loading case...</div>;
  }

  return (
    <div className="case-workflow">
      <div className="workflow-header">
        <button onClick={() => navigate('/')} className="btn-back">
          ← Back to Cases
        </button>
        <h1>Case Workflow: {caseId}</h1>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progressPercent}%` }}></div>
          <span className="progress-text">{progressPercent}% Complete</span>
        </div>
      </div>

      <div className="workflow-tabs">
        <button
          className={`tab ${activeTab === 'facts' ? 'active' : ''}`}
          onClick={() => setActiveTab('facts')}
        >
          📄 Facts ({facts.length})
        </button>
        <button
          className={`tab ${activeTab === 'arguments' ? 'active' : ''}`}
          onClick={() => setActiveTab('arguments')}
        >
          📋 Arguments ({arguments_.length})
        </button>
        <button
          className={`tab ${activeTab === 'predictions' ? 'active' : ''}`}
          onClick={() => setActiveTab('predictions')}
        >
          🔮 Prediction
        </button>
      </div>

      <div className="workflow-content">
        {activeTab === 'facts' && (
          <FactEditor
            facts={facts}
            onAddFact={handleAddFact}
            onUpdateFact={handleUpdateFact}
            onApproveFact={handleApproveFact}
            onRejectFact={handleRejectFact}
            onLockFact={handleLockFact}
            loading={loading}
          />
        )}

        {activeTab === 'arguments' && (
          <ArgumentEditor
            arguments={arguments_}
            facts={facts.map((f) => ({ fact_id: f.fact_id, fact: f.fact }))}
            onAddArgument={handleAddArgument}
            onUpdateArgument={handleUpdateArgument}
            onApproveArgument={handleApproveArgument}
            onRejectArgument={handleRejectArgument}
            onLockArgument={handleLockArgument}
            loading={loading}
          />
        )}

        {activeTab === 'predictions' && (
          <PredictionViewer
            prediction={currentPrediction}
            confidence={currentConfidence}
            history={predictions}
            onRestore={handleRestorePrediction}
            loading={loading}
          />
        )}
      </div>
    </div>
  );
};

export default CaseWorkflow;
