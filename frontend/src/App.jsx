import React, { useEffect, useState } from 'react'
import { HashRouter, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home.jsx'
import Interview from './pages/Interview.jsx'
import Summary from './pages/Summary.jsx'
import { api } from './api.js'

function Signal() {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    let mounted = true
    const check = () => api.health().then((h) => mounted && setHealth(h)).catch(() => mounted && setHealth({ status: 'unreachable' }))
    check()
    const id = setInterval(check, 15000)
    return () => { mounted = false; clearInterval(id) }
  }, [])

  if (!health) return null
  const online = health.llm_available
  return (
    <div className={`signal ${online ? '' : 'offline'}`} title={`Provider: ${health.llm_provider} · Model: ${health.model || 'n/a'}`}>
      <span className="pulse" />
      {online ? `${health.llm_provider?.toUpperCase()} ONLINE · ${health.model}` : `${health.llm_provider?.toUpperCase() || 'LLM'} OFFLINE · fallback mode`}
    </div>
  )
}

function BackendSettings() {
  const [open, setOpen] = useState(false)
  const [url, setUrl] = useState(api.getBaseUrl())

  const handleSave = (e) => {
    e.preventDefault()
    const cleanUrl = url.trim().replace(/\/$/, '')
    if (cleanUrl) {
      localStorage.setItem('VITE_API_BASE_URL', cleanUrl)
    } else {
      localStorage.removeItem('VITE_API_BASE_URL')
    }
    setOpen(false)
    window.location.reload()
  }

  return (
    <div className="backend-settings-container" style={{ position: 'relative' }}>
      <button 
        onClick={() => setOpen(!open)} 
        className="settings-toggle-btn"
        title="Configure Backend API URL"
        style={{
          background: 'none',
          border: 'none',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          padding: '6px',
          borderRadius: '4px',
          transition: 'color 0.2s, background-color 0.2s'
        }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
      </button>

      {open && (
        <div className="backend-settings-dropdown" style={{
          position: 'absolute',
          right: 0,
          top: '30px',
          width: '280px',
          background: 'var(--surface-raised)',
          border: '1px solid var(--border)',
          borderRadius: '6px',
          padding: '16px',
          boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
          zIndex: 1000
        }}>
          <h4 style={{ margin: '0 0 10px 0', fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>API Configuration</h4>
          <form onSubmit={handleSave}>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '10px', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Backend URL</label>
              <input 
                type="text" 
                value={url} 
                onChange={(e) => setUrl(e.target.value)} 
                placeholder="http://localhost:8000"
                style={{
                  width: '100%',
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  padding: '8px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontFamily: 'var(--font-mono)'
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button 
                type="button" 
                onClick={() => { setUrl(import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000') }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '11px',
                  cursor: 'pointer',
                  padding: '4px 8px'
                }}
              >
                Reset
              </button>
              <button 
                type="submit"
                style={{
                  background: 'var(--accent)',
                  border: 'none',
                  color: '#000',
                  fontWeight: '600',
                  fontSize: '11px',
                  cursor: 'pointer',
                  padding: '6px 12px',
                  borderRadius: '4px'
                }}
              >
                Save
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

export default function App() {
  return (
    <HashRouter>
      <div className="app-shell">
        <div className="topbar">
          <Link to="/" className="topbar-brand" style={{ textDecoration: 'none', color: 'inherit' }}>
            <span className="dot" />
            PANEL — AI SCREENING CONSOLE
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <BackendSettings />
            <Signal />
          </div>
        </div>
        <div className="main">
          <div className="container">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/interview/:sessionId" element={<Interview />} />
              <Route path="/summary/:sessionId" element={<Summary />} />
            </Routes>
          </div>
        </div>
      </div>
    </HashRouter>
  )
}
