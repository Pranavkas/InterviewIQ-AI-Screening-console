import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'

export default function Home() {
  const [roles, setRoles] = useState([])
  const [selectedRole, setSelectedRole] = useState(null)
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    api.listRoles().then(setRoles).catch(() => setError('Could not reach the backend. Is it running on port 8000?'))
  }, [])

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0])
  }

  const onSubmit = async () => {
    if (!file || !selectedRole) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.uploadResume(file, selectedRole)
      navigate(`/interview/${res.session_id}`, { state: { role: res.role, maxQuestions: res.max_questions } })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="eyebrow">Candidate Entry</div>
      <h1>Start a structured technical screening</h1>
      <p className="subtitle">
        Upload a resume and pick a target role. Questions are generated live from
        the candidate's background and a role-specific knowledge base — nothing
        here is scripted in advance.
      </p>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="field">
          <label>Target role</label>
          <div className="role-grid">
            {roles.map((r) => (
              <button
                key={r.key}
                className={`role-option ${selectedRole === r.key ? 'selected' : ''}`}
                onClick={() => setSelectedRole(r.key)}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label>Resume (PDF or .txt)</label>
          <div
            className={`dropzone ${dragging ? 'dragging' : ''}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            tabIndex={0}
            role="button"
          >
            {file ? (
              <>
                <div>Selected file</div>
                <div className="dropzone-filename">{file.name}</div>
              </>
            ) : (
              <div>Click to browse, or drag a resume file here</div>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.txt"
              hidden
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </div>
        </div>

        <div className="btn-row">
          <button
            className="btn btn-primary"
            disabled={!file || !selectedRole || loading}
            onClick={onSubmit}
          >
            {loading ? 'Parsing resume…' : 'Begin interview'}
          </button>
        </div>
      </div>
    </>
  )
}
