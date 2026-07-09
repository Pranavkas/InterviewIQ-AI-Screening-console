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

export default function App() {
  return (
    <HashRouter>
      <div className="app-shell">
        <div className="topbar">
          <Link to="/" className="topbar-brand" style={{ textDecoration: 'none', color: 'inherit' }}>
            <span className="dot" />
            PANEL — AI SCREENING CONSOLE
          </Link>
          <Signal />
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
