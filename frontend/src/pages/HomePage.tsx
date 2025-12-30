import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { caseAPI, CaseInfo } from '../services/api';
import CaseList from '../components/CaseList';
import './HomePage.css';

interface CreateCaseFormState {
  caseName: string;
  caseType: string;
}

const HomePage: React.FC = () => {
  const [cases, setCases] = useState<CaseInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState<CreateCaseFormState>({ caseName: '', caseType: '' });
  const navigate = useNavigate();

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    setLoading(true);
    try {
      const caseList = await caseAPI.list();
      setCases(caseList);
    } catch (error) {
      console.error('Failed to load cases:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCase = async () => {
    if (!formData.caseName.trim()) {
      alert('Please enter a case name');
      return;
    }

    setLoading(true);
    try {
      const newCase = await caseAPI.create({
        case_name: formData.caseName,
        case_type: formData.caseType,
      });
      setCases([...cases, newCase]);
      setFormData({ caseName: '', caseType: '' });
      setShowCreateForm(false);
      navigate(`/case/${newCase.case_id}`);
    } catch (error) {
      console.error('Failed to create case:', error);
      alert('Failed to create case');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectCase = (caseId: string) => {
    navigate(`/case/${caseId}`);
  };

  return (
    <div className="home-page">
      <div className="home-header">
        <h1>Legal Case Workflow Manager</h1>
        <p>Manage your legal cases with AI-powered facts, arguments, and predictions</p>
      </div>

      {showCreateForm && (
        <div className="create-case-modal">
          <div className="modal-content">
            <h2>Create New Case</h2>
            <input
              type="text"
              placeholder="Case Name"
              value={formData.caseName}
              onChange={(e) => setFormData({ ...formData, caseName: e.target.value })}
              className="input-field"
            />
            <input
              type="text"
              placeholder="Case Type (optional)"
              value={formData.caseType}
              onChange={(e) => setFormData({ ...formData, caseType: e.target.value })}
              className="input-field"
            />
            <div className="modal-actions">
              <button onClick={handleCreateCase} className="btn-primary" disabled={loading}>
                {loading ? 'Creating...' : 'Create Case'}
              </button>
              <button onClick={() => setShowCreateForm(false)} className="btn-secondary">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <CaseList
        cases={cases}
        onSelectCase={handleSelectCase}
        onCreateCase={() => setShowCreateForm(true)}
        loading={loading}
      />
    </div>
  );
};

export default HomePage;
