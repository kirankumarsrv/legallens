import React, { useState, useEffect } from 'react';
import { entityAPI, Clarification } from '../services/api';
import './ClarificationQuestions.css';

interface ClarificationQuestionsProps {
  caseId: string;
  onAnswerSubmitted?: () => void;
  onRefresh?: () => void;
}

const ClarificationQuestions: React.FC<ClarificationQuestionsProps> = ({
  caseId,
  onAnswerSubmitted,
  onRefresh,
}) => {
  const [clarifications, setClarifications] = useState<Clarification[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [resolvedCount, setResolvedCount] = useState(0);

  useEffect(() => {
    loadClarifications();
  }, [caseId]);

  const loadClarifications = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await entityAPI.getClarifications(caseId);
      setClarifications(data.clarifications || []);
      setResolvedCount(
        (data.clarifications || []).filter((c) => c.resolved).length
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load clarifications');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async (clarification: Clarification) => {
    const answer = answers[clarification.id];
    if (!answer || !answer.trim()) {
      alert('Please provide an answer');
      return;
    }

    try {
      setSubmitting(clarification.id);
      setError('');

      await entityAPI.submitAnswer(
        caseId,
        clarification.id,
        answer,
        undefined,
        notes[clarification.id] || undefined
      );

      // Update local state
      setClarifications((prevs) =>
        prevs.map((c) =>
          c.id === clarification.id
            ? {
                ...c,
                resolved: true,
                lawyer_answer: answer,
                notes: notes[clarification.id],
                resolved_at: new Date().toISOString(),
              }
            : c
        )
      );

      setResolvedCount((prev) => prev + 1);

      // Clear form
      setAnswers((prev) => ({ ...prev, [clarification.id]: '' }));
      setNotes((prev) => ({ ...prev, [clarification.id]: '' }));

      if (onAnswerSubmitted) {
        onAnswerSubmitted();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit answer');
    } finally {
      setSubmitting(null);
    }
  };

  const pendingClarifications = clarifications.filter((c) => !c.resolved);
  const resolvedClarifications = clarifications.filter((c) => c.resolved);

  if (loading) {
    return <div className="clarifications-loading">Loading clarifications...</div>;
  }

  return (
    <div className="clarifications-panel">
      <div className="clarifications-header">
        <h3>❓ Clarification Questions for Lawyer</h3>
        <div className="clarifications-stats">
          <span className="stat pending">
            Pending: <strong>{pendingClarifications.length}</strong>
          </span>
          <span className="stat resolved">
            Resolved: <strong>{resolvedCount}</strong>
          </span>
        </div>
        <button className="btn-refresh" onClick={loadClarifications} title="Refresh">
          ↻
        </button>
      </div>

      {error && <div className="clarifications-error">{error}</div>}

      {pendingClarifications.length === 0 && resolvedClarifications.length === 0 ? (
        <div className="clarifications-empty">
          ✅ No clarification questions. All entities are clear.
        </div>
      ) : (
        <>
          {pendingClarifications.length > 0 && (
            <div className="clarifications-section">
              <h4>Pending Answers ({pendingClarifications.length})</h4>
              <div className="clarifications-list">
                {pendingClarifications.map((clarification) => (
                  <div key={clarification.id} className="clarification-item pending-item">
                    <div className="clarification-type-badge">
                      {clarification.type === 'conflict'
                        ? '⚠️ Conflict'
                        : clarification.type === 'duplicate'
                        ? '🔄 Duplicate'
                        : '❓ Ambiguity'}
                    </div>

                    <div className="clarification-content">
                      <div className="clarification-question">
                        <strong>{clarification.question}</strong>
                      </div>

                      {clarification.context && (
                        <div className="clarification-context">
                          <small>Context: {clarification.context}</small>
                        </div>
                      )}

                      <div className="clarification-form">
                        <textarea
                          placeholder="Please provide your answer here..."
                          value={answers[clarification.id] || ''}
                          onChange={(e) =>
                            setAnswers((prev) => ({
                              ...prev,
                              [clarification.id]: e.target.value,
                            }))
                          }
                          className="answer-textarea"
                          disabled={submitting === clarification.id}
                        />

                        <textarea
                          placeholder="Additional notes (optional)..."
                          value={notes[clarification.id] || ''}
                          onChange={(e) =>
                            setNotes((prev) => ({
                              ...prev,
                              [clarification.id]: e.target.value,
                            }))
                          }
                          className="notes-textarea"
                          disabled={submitting === clarification.id}
                        />

                        <button
                          className="btn-submit-answer"
                          onClick={() => handleSubmitAnswer(clarification)}
                          disabled={submitting === clarification.id}
                        >
                          {submitting === clarification.id ? 'Submitting...' : '✓ Submit Answer'}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {resolvedClarifications.length > 0 && (
            <div className="clarifications-section resolved-section">
              <h4>Resolved ({resolvedClarifications.length})</h4>
              <div className="clarifications-list">
                {resolvedClarifications.map((clarification) => (
                  <div key={clarification.id} className="clarification-item resolved-item">
                    <div className="clarification-resolved-badge">✓ Resolved</div>

                    <div className="clarification-content">
                      <div className="clarification-question">
                        <strong>{clarification.question}</strong>
                      </div>

                      <div className="lawyer-answer">
                        <strong>Your Answer:</strong>
                        <p>{clarification.lawyer_answer}</p>
                      </div>

                      {clarification.notes && (
                        <div className="lawyer-notes">
                          <strong>Notes:</strong>
                          <p>{clarification.notes}</p>
                        </div>
                      )}

                      {clarification.resolved_at && (
                        <small className="resolved-timestamp">
                          Resolved: {new Date(clarification.resolved_at).toLocaleString()}
                        </small>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ClarificationQuestions;
