import React, { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'

const DEFAULT_MAX_QUESTIONS = 6

export default function Interview() {
  const { sessionId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const maxQuestions = location.state?.maxQuestions || DEFAULT_MAX_QUESTIONS

  const [question, setQuestion] = useState(null)
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [loadingQuestion, setLoadingQuestion] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const loadNextQuestion = useCallback(() => {
    setLoadingQuestion(true)
    setFeedback(null)
    setAnswer('')
    setError(null)
    api.nextQuestion(sessionId)
      .then(setQuestion)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingQuestion(false))
  }, [sessionId])

  useEffect(() => { loadNextQuestion() }, [loadNextQuestion])

  const onSubmitAnswer = async () => {
    if (!answer.trim() || !question) return
    setSubmitting(true)
    setError(null)
    try {
      const result = await api.submitAnswer(sessionId, question.qa_id, answer)
      setFeedback(result)
      if (result.session_status === 'completed') {
        setTimeout(() => navigate(`/summary/${sessionId}`), 1400)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const sequence = Array.from({ length: maxQuestions })

  return (
    <>
      <div className="eyebrow">Interactive Interview</div>
      <h1>Session in progress</h1>
      <p className="subtitle">
        Answer in your own words — the next question's difficulty adapts to how
        you do, and every question is grounded in retrieved reference material.
      </p>

      {error && <div className="error-banner">{error}</div>}

      <div className="sequence">
        {sequence.map((_, i) => {
          const stepNum = i + 1
          const done = question && stepNum < question.sequence
          const active = question && stepNum === question.sequence
          return <div key={i} className={`sequence-step ${done ? 'done' : ''} ${active ? 'active' : ''}`} />
        })}
      </div>

      <div className="card">
        {loadingQuestion && (
          <div className="loading-line"><span className="spinner" /> Retrieving context and generating question…</div>
        )}

        {!loadingQuestion && question && (
          <>
            <div className="meta-row">
              <span>Question {question.sequence} / {maxQuestions} · {question.topic}</span>
              <span className={`chip chip-${question.difficulty}`}>{question.difficulty}</span>
            </div>

            <p className="question-text">{question.question_text}</p>

            {!feedback && (
              <>
                <textarea
                  placeholder="Type your answer here…"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  disabled={submitting}
                />
                <div className="btn-row">
                  <button className="btn btn-primary" disabled={!answer.trim() || submitting} onClick={onSubmitAnswer}>
                    {submitting ? 'Evaluating…' : 'Submit answer'}
                  </button>
                </div>
              </>
            )}

            {feedback && (
              <div className="feedback-box">
                <div className="feedback-score">{feedback.evaluation_score.toFixed(1)}<span style={{ fontSize: 14, color: 'var(--text-muted)' }}> / 10</span></div>
                <p style={{ margin: '10px 0 0' }}>{feedback.evaluation_feedback}</p>
                {feedback.session_status !== 'completed' && (
                  <div className="btn-row">
                    <button className="btn btn-primary" onClick={loadNextQuestion}>Next question →</button>
                  </div>
                )}
                {feedback.session_status === 'completed' && (
                  <p className="loading-line" style={{ marginTop: 14 }}><span className="spinner" /> Interview complete — building your summary…</p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}
