import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api.js'

export default function Summary() {
  const { sessionId } = useParams()
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getSummary(sessionId).then(setSummary).catch((e) => setError(e.message))
  }, [sessionId])

  if (error) return <div className="error-banner">{error}</div>
  if (!summary) return <div className="loading-line"><span className="spinner" /> Compiling session report…</div>

  return (
    <>
      <div className="eyebrow">Final Output</div>
      <h1>Session summary</h1>
      <p className="subtitle">Structured record of the interaction, with a basic automated read on strengths and gaps.</p>

      <div className="card">
        <div className="summary-score-hero">
          <span className="value">{summary.overall_score != null ? summary.overall_score.toFixed(1) : '—'}</span>
          <span className="of10">/ 10 overall</span>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: 14, lineHeight: 1.6 }}>{summary.summary_text}</p>

        <div className="section-title">Topic coverage</div>
        <div className="tag-list">
          {summary.topic_coverage.map((t) => <span className="tag" key={t}>{t}</span>)}
        </div>

        {summary.strengths.length > 0 && (
          <>
            <div className="section-title">Strengths</div>
            <div className="tag-list">
              {summary.strengths.map((s, i) => <span className="tag" key={i} style={{ color: 'var(--green)', borderColor: 'var(--green)' }}>{s}</span>)}
            </div>
          </>
        )}

        {summary.weaknesses.length > 0 && (
          <>
            <div className="section-title">Areas to probe further</div>
            <div className="tag-list">
              {summary.weaknesses.map((w, i) => <span className="tag" key={i} style={{ color: 'var(--coral)', borderColor: 'var(--coral)' }}>{w}</span>)}
            </div>
          </>
        )}
      </div>

      <div className="section-title" style={{ marginTop: 40 }}>Full transcript</div>
      {summary.qa_history.map((qa) => (
        <div className="transcript-item" key={qa.sequence}>
          <p className="transcript-q">Q{qa.sequence}. {qa.question_text}</p>
          <p className="transcript-a">{qa.answer_text || '(no answer recorded)'}</p>
          <div className="transcript-footer">
            <span>{qa.topic} · {qa.difficulty}</span>
            <span>{qa.evaluation_score != null ? `${qa.evaluation_score.toFixed(1)} / 10` : '—'}</span>
          </div>
        </div>
      ))}

      <div className="btn-row" style={{ marginTop: 24 }}>
        <Link to="/" className="btn btn-ghost">Start a new session</Link>
      </div>
    </>
  )
}
