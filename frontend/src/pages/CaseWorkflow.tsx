import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  caseAPI,
  factAPI,
  argumentAPI,
  predictionAPI,
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
  const [currentAnalysis, setCurrentAnalysis] = useState('');
  const [currentDraft, setCurrentDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);
  const [reasoningTrace, setReasoningTrace] = useState<string[]>([]);
  const [problemStatement, setProblemStatement] = useState<string>('');
  const [evidenceFiles, setEvidenceFiles] = useState<File[]>([]);
  const [evidenceFilePaths, setEvidenceFilePaths] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<'facts' | 'arguments' | 'predictions'>('facts');
  
  // Retrieval tool toggles
  const [enableWebSearch, setEnableWebSearch] = useState(true);
  const [enableResearchPapers, setEnableResearchPapers] = useState(false);
  const [enableGoogleScholar, setEnableGoogleScholar] = useState(true);
  const [enableArxiv, setEnableArxiv] = useState(true);
  const [enableIndianLegalDB, setEnableIndianLegalDB] = useState(true);

  if (!caseId) {
    return <div className="error">Case ID not found</div>;
  }

  if (caseId === 'undefined') {
    // Defensive: avoid making requests to /cases/undefined
    return (
      <div className="error">
        Invalid case ID ("undefined"). Return to <a href="/">home</a> and reopen the case.
      </div>
    );
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
      // Load persisted state flags (problem statement, evidence paths)
      try {
        const flags = await (await import('../services/api')).stateAPI.getFlags(caseId);
        if (flags) {
          if (flags.problem_statement) setProblemStatement(flags.problem_statement as string);
          if (Array.isArray(flags.evidence_files)) setEvidenceFilePaths(flags.evidence_files as string[]);
        }
      } catch (err) {
        // non-fatal
      }
    } catch (error) {
      console.error('Failed to load case data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRunCompute = async () => {
    if (!caseId) return;
    setComputing(true);
    setReasoningTrace([]);

    // Use SSE stream endpoint to get per-node progress
    const params = new URLSearchParams();
    params.set('enable_web_search', enableWebSearch.toString());
    params.set('enable_research_papers', enableResearchPapers.toString());
    params.set('enable_google_scholar', enableGoogleScholar.toString());
    params.set('enable_arxiv', enableArxiv.toString());
    params.set('enable_indian_legal_db', enableIndianLegalDB.toString());
    const url = `${(import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'}/cases/${caseId}/compute/stream?${params.toString()}`;

    const es = new EventSource(url);
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.phase === 'start') {
          setReasoningTrace((s) => [...s, data.message]);
        } else if (data.phase === 'evidence_ingest' || data.phase === 'fact_gathering' || data.phase === 'legal_analysis' || data.phase === 'prediction') {
          setReasoningTrace((s) => [...s, `${data.phase}: ${data.message}`]);
        } else if (data.phase === 'done') {
          if (data.prediction) setCurrentPrediction(data.prediction);
          if (typeof data.prediction_confidence === 'number') setCurrentConfidence(data.prediction_confidence);
          if (data.analysis) setCurrentAnalysis(data.analysis);
          if (data.draft) setCurrentDraft(data.draft);
          if (Array.isArray(data.reasoning_trace)) setReasoningTrace((s) => [...s, ...data.reasoning_trace]);
          es.close();
          setComputing(false);
          // reload lists
          loadCaseData();
        } else if (data.phase === 'error') {
          setReasoningTrace((s) => [...s, `ERROR: ${data.message}`]);
          es.close();
          setComputing(false);
        } else {
          // generic message
          setReasoningTrace((s) => [...s, JSON.stringify(data)]);
        }
      } catch (err) {
        // sometimes server sends plain strings
        setReasoningTrace((s) => [...s, ev.data]);
      }
    };

    es.onerror = (e) => {
      setReasoningTrace((s) => [...s, 'Stream error or closed']);
      es.close();
      setComputing(false);
    };
  };

  const handleUploadEvidence = async () => {
    if (!caseId) return;
    if (evidenceFiles.length === 0) {
      alert('Select files first');
      return;
    }

    try {
      setComputing(true);
      const resp = await caseAPI.uploadEvidence(caseId, evidenceFiles);
      if (resp && Array.isArray(resp.saved)) {
        setEvidenceFilePaths(resp.saved);
        alert(`Uploaded ${resp.saved.length} file(s)`);
      }
    } catch (err) {
      console.error('Upload failed', err);
      alert('Upload failed');
    } finally {
      setComputing(false);
    }
  };

  const handleSaveProblem = async () => {
    if (!caseId) return;
    try {
      setComputing(true);
      await caseAPI.saveProblem(caseId, problemStatement);
      alert('Problem statement saved');
    } catch (err) {
      console.error('Save failed', err);
      alert('Failed to save problem statement');
    } finally {
      setComputing(false);
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
        <div className="compute-actions">
          <button className="btn-primary" onClick={handleRunCompute} disabled={computing}>
            {computing ? 'Running...' : 'Run Compute'}
          </button>
          <button
            className="btn-secondary"
            onClick={async () => {
              if (!caseId) return;
              try {
                setComputing(true);
                await (await import('../services/api')).factAPI.lockAll(caseId);
                // reload facts and UI
                await loadCaseData();
                alert('Locked all approved facts');
              } catch (err) {
                console.error('Lock all failed', err);
                alert('Failed to lock all approved facts');
              } finally {
                setComputing(false);
              }
            }}
            disabled={computing}
          >
            Lock All Approved
          </button>
          <button
            className="btn-primary"
            onClick={async () => {
              if (!caseId) return;
              try {
                setComputing(true);
                // Lock approved facts then trigger compute using locked facts only
                await factAPI.lockAll(caseId);
                await loadCaseData();
                // start compute stream (uses locked facts)
                await handleRunCompute();
              } catch (err) {
                console.error('Use locked facts failed', err);
                alert('Failed to lock and run analysis');
              } finally {
                setComputing(false);
              }
            }}
            disabled={computing || facts.filter((f) => f.status === 'approved').length === 0}
          >
            Use Locked Facts for Analysis
          </button>
          <button
            className="btn-primary"
            onClick={async () => {
              if (!caseId) return;
              try {
                setComputing(true);
                const resp = await (await import('../services/api')).caseAPI.generateDraft(caseId);
                if (resp.draft) {
                  setCurrentDraft(resp.draft);
                  alert('Draft generated successfully');
                }
              } catch (err) {
                console.error('Draft generation failed', err);
                alert('Failed to generate draft');
              } finally {
                setComputing(false);
              }
            }}
            disabled={computing || !currentPrediction}
          >
            📝 Generate Draft
          </button>
        </div>
      </div>

      <div className="problem-panel">
        <h3>Problem Statement & Evidence</h3>
        <textarea
          placeholder="Enter the problem statement for this case..."
          value={problemStatement}
          onChange={(e) => setProblemStatement(e.target.value)}
          className="problem-textarea"
        />
        <div className="problem-actions">
          <button className="btn-secondary" onClick={handleSaveProblem} disabled={computing || problemStatement.trim().length===0}>
            Save Problem
          </button>
        </div>
        <div className="evidence-upload">
          <label>Attach evidence files (PDF/image names only for now):</label>
          <input
            type="file"
            multiple
            onChange={(e) => setEvidenceFiles(Array.from(e.target.files || []))}
          />
          <div className="attached-list">
            {evidenceFiles.map((f, i) => (
              <div key={i} className="attached-item">{f.name}</div>
            ))}
          </div>
          <div className="upload-actions">
            <button className="btn-primary" onClick={handleUploadEvidence} disabled={computing || evidenceFiles.length === 0}>
              {computing ? 'Uploading...' : 'Upload Files'}
            </button>
            {evidenceFilePaths.length > 0 && (
              <div className="uploaded-list">
                <strong>Uploaded:</strong>
                <ul>
                  {evidenceFilePaths.map((p, i) => (
                    <li key={i}>{p}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
        
        {/* Retrieval Tools Configuration */}
        <div className="retrieval-config">
          <h4>🔧 Fact Retrieval Sources</h4>
          <p className="config-description">Select which sources to use for gathering legal facts and precedents</p>
          <div className="toggle-grid">
            <label className="toggle-item">
              <input
                type="checkbox"
                checked={enableWebSearch}
                onChange={(e) => setEnableWebSearch(e.target.checked)}
              />
              <span className="toggle-label">
                <strong>🌐 Web Search</strong>
                <small>Tavily/Google/Bing general web search</small>
              </span>
            </label>
            
            <label className="toggle-item">
              <input
                type="checkbox"
                checked={enableGoogleScholar}
                onChange={(e) => setEnableGoogleScholar(e.target.checked)}
              />
              <span className="toggle-label">
                <strong>🎓 Google Scholar</strong>
                <small>Academic legal papers & citations</small>
              </span>
            </label>
            
            <label className="toggle-item">
              <input
                type="checkbox"
                checked={enableArxiv}
                onChange={(e) => setEnableArxiv(e.target.checked)}
              />
              <span className="toggle-label">
                <strong>📖 ArXiv</strong>
                <small>Legal research papers & preprints</small>
              </span>
            </label>
            
            <label className="toggle-item">
              <input
                type="checkbox"
                checked={enableIndianLegalDB}
                onChange={(e) => setEnableIndianLegalDB(e.target.checked)}
              />
              <span className="toggle-label">
                <strong>⚖️ Indian Legal DBs</strong>
                <small>IndianKanoon & specialized databases</small>
              </span>
            </label>
            
            <label className="toggle-item">
              <input
                type="checkbox"
                checked={enableResearchPapers}
                onChange={(e) => setEnableResearchPapers(e.target.checked)}
              />
              <span className="toggle-label">
                <strong>📄 Research Papers</strong>
                <small>Local PDF semantic search</small>
              </span>
            </label>
          </div>
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
            args={arguments_}
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
        {reasoningTrace.length > 0 && (
          <div className="reasoning-trace">
            <h3>Reasoning Trace</h3>
            <ol>
              {reasoningTrace.map((r, idx) => (
                <li key={idx}>{r}</li>
              ))}
            </ol>
          </div>
        )}
        {currentAnalysis && (
          <div className="analysis-section">
            <h3>📋 Legal Analysis</h3>
            <div className="analysis-content">
              {currentAnalysis}
            </div>
          </div>
        )}
        {currentDraft && (
          <div className="draft-section">
            <h3>📄 Legal Draft/Memorandum</h3>
            <div className="draft-content">
              {currentDraft}
            </div>
            <button
              className="btn-secondary"
              onClick={() => {
                const element = document.createElement('a');
                element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(currentDraft));
                element.setAttribute('download', `case_${caseId}_draft.txt`);
                element.style.display = 'none';
                document.body.appendChild(element);
                element.click();
                document.body.removeChild(element);
              }}
            >
              📥 Download Draft
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CaseWorkflow;
