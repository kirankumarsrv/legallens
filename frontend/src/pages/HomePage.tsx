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
      
      if (!newCase || !newCase.case_id || newCase.case_id === 'undefined') {
        console.error('Invalid case created:', newCase);
        alert('❌ Failed to create case (invalid response). Check server logs.');
        setLoading(false);
        return;
      }
      
      // Verify case was added to the list
      setCases([...cases, newCase]);
      setFormData({ caseName: '', caseType: '' });
      setShowCreateForm(false);
      
      // Show success message
      console.log(`✅ Case created successfully: ${newCase.case_id}`);
      alert(`✅ Case "${newCase.case_name}" created! Opening case...`);
      
      navigate(`/case/${newCase.case_id}`);
    } catch (error) {
      console.error('❌ Failed to create case:', error);
      alert(`❌ Failed to create case: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectCase = (caseId: string) => {
    navigate(`/case/${caseId}`);
  };

  const handleDeleteCase = async (caseId: string) => {
    setLoading(true);
    try {
      await caseAPI.delete(caseId);
      // Remove from local state
      setCases(cases.filter(c => c.case_id !== caseId));
      alert('✅ Case deleted successfully');
    } catch (error) {
      console.error('Failed to delete case:', error);
      alert('❌ Failed to delete case');
    } finally {
      setLoading(false);
    }
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
        onDeleteCase={handleDeleteCase}
        loading={loading}
      />
    </div>
  );
};

export default HomePage;
