const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch (_) { /* ignore */ }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  health: () => fetch(`${BASE_URL}/api/health`).then(handle),

  listRoles: () => fetch(`${BASE_URL}/api/candidates/roles`).then(handle),

  uploadResume: (file, role) => {
    const form = new FormData()
    form.append('file', file)
    form.append('role', role)
    return fetch(`${BASE_URL}/api/candidates/upload-resume`, {
      method: 'POST',
      body: form,
    }).then(handle)
  },

  nextQuestion: (sessionId) =>
    fetch(`${BASE_URL}/api/interview/${sessionId}/next-question`).then(handle),

  submitAnswer: (sessionId, qaId, answerText) =>
    fetch(`${BASE_URL}/api/interview/${sessionId}/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ qa_id: qaId, answer_text: answerText }),
    }).then(handle),

  getSummary: (sessionId) =>
    fetch(`${BASE_URL}/api/interview/${sessionId}/summary`).then(handle),
}
