import React, { useState, useEffect } from 'react'
import { Toaster } from 'react-hot-toast'
import axios from 'axios'
import Pipeline from './pages/Pipeline'
import Candidates from './pages/Candidates'
import Outreach from './pages/Outreach'
import Dashboard from './pages/Dashboard'
import Auth from './pages/Auth'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [user, setUser] = useState(null)
  const [tab, setTab] = useState('dashboard')
  const [status, setStatus] = useState(null)
  const [selectedCandidate, setSelectedCandidate] = useState(null)

  // Configure axios auth header on mount or token change
  useEffect(() => {
    const activeToken = localStorage.getItem('token')
    if (activeToken) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${activeToken}`
      setToken(activeToken)
      try {
        setUser(JSON.parse(localStorage.getItem('user')))
      } catch {
        setUser(null)
      }
    } else {
      delete axios.defaults.headers.common['Authorization']
      setToken(null)
      setUser(null)
    }
  }, [token])

  useEffect(() => {
    axios.get('/api/status').then(r => setStatus(r.data)).catch(() => {})
  }, [])

  const handleLoginSuccess = (newToken) => {
    setToken(newToken)
    setTab('dashboard')
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    delete axios.defaults.headers.common['Authorization']
    setToken(null)
    setUser(null)
    setTab('dashboard')
  }

  const goToOutreach = (candidate) => {
    setSelectedCandidate(candidate)
    setTab('outreach')
  }

  // Intercept Axios errors for 401 and redirect to logout/auth
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          handleLogout()
        }
        return Promise.reject(error)
      }
    )
    return () => {
      axios.interceptors.response.eject(interceptor)
    }
  }, [])

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <Toaster position="top-right" />

      {!token ? (
        <div className="flex-1 flex items-center justify-center p-6">
          <Auth onLoginSuccess={handleLoginSuccess} />
        </div>
      ) : (
        <>
          {/* Sidebar */}
          <aside className="w-64 bg-gradient-to-b from-white via-slate-50 to-slate-100 border-r border-slate-200 flex flex-col justify-between flex-shrink-0 select-none">
            {/* Top segment */}
            <div className="p-6">
              {/* Logo branding */}
              <div className="flex items-center gap-3 mb-8">
                <div className="w-10 h-10 bg-[#0B57D0] text-white rounded-xl flex items-center justify-center shadow-sm">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-[14px] font-extrabold text-[#0B57D0] leading-none">Hiring Agent</h2>
                  <p className="text-[8px] text-slate-400 font-extrabold tracking-wider uppercase mt-1">Enterprise AI</p>
                </div>
              </div>

              {/* Call to action button */}
              <button
                onClick={() => setTab('pipeline')}
                className="w-full bg-[#0B57D0] hover:bg-[#0842a0] text-white rounded-xl py-3 px-4 flex items-center justify-center gap-2 font-bold text-xs shadow-sm transition-all mb-7 active:scale-[0.98] outline-none hover-btn-pulse"
              >
                <span>⚡</span> Run AI Pipeline
              </button>

              {/* Navigation Items */}
              <nav className="flex flex-col gap-1">
                {[
                  { id: 'dashboard', label: 'Dashboard', icon: (
                    <svg className="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4zM14 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2v-4z" />
                    </svg>
                  )},

                  { id: 'candidates', label: 'Candidates', icon: (
                    <svg className="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                  )},
                  { id: 'outreach', label: 'Outreach', icon: (
                    <svg className="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  )}
                ].map(t => {
                  const isActive = tab === t.id
                  return (
                    <button
                      key={t.id}
                      onClick={() => setTab(t.id)}
                      className={`w-full flex items-center gap-3.5 px-4.5 py-3 rounded-xl text-xs font-bold transition-all outline-none hover:scale-[1.01] ${
                        isActive
                          ? 'bg-[#eef2f6] text-slate-800 border-l-[3px] border-blue-600 rounded-l-none'
                          : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800'
                      }`}
                    >
                      <span className={isActive ? 'text-blue-600' : 'text-slate-400'}>{t.icon}</span>
                      {t.label}
                    </button>
                  )
                })}
              </nav>
            </div>
            {/* Bottom User Profile card in sidebar */}
            {user && (
              <div className="p-4 border-t border-slate-200/60 flex items-center justify-between">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-8 h-8 rounded-full bg-blue-100 text-[#0B57D0] flex items-center justify-center font-bold text-xs flex-shrink-0">
                    {user.full_name?.charAt(0).toUpperCase() || 'U'}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-slate-800 truncate">{user.full_name}</p>
                    <p className="text-[9px] font-semibold text-slate-400 truncate">{user.email}</p>
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-1.5 text-slate-450 hover:text-red-500 rounded-lg hover:bg-slate-100 transition-all outline-none"
                  title="Logout"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                </button>
              </div>
            )}
          </aside>

          {/* Main Area */}
          <div className="flex-1 flex flex-col min-w-0 bg-gradient-to-tr from-[#f8fafc] via-[#f1f5f9] to-[#eff6ff]/35">
            {/* Header bar */}
            <header className="bg-gradient-to-r from-blue-50 via-indigo-50/40 to-slate-50 border-b border-slate-200 px-10 py-5.5 flex items-center justify-between flex-shrink-0 select-none">
              <div>
                <h1 className="text-[17px] font-bold text-slate-800 leading-tight">4CECloud AI Hiring Agent</h1>
                <p className="text-xs text-blue-600/70 font-semibold mt-0.5">US Sales Sourcing & Exclusions · Phase 2</p>
              </div>
              <div className="flex items-center gap-5">
                {status && (
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                      status.using_mock_data
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-green-50 text-green-800 border-green-200'
                    }`}>
                      {status.using_mock_data ? '🧪 POC — mock' : '🟢 Apollo Live'}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-800 font-semibold border border-blue-200">
                      {status.llm_provider === 'groq' ? '⚡ Groq' : '🤖 OpenAI'}
                      {' · '}{status.fast_model?.split('-').slice(0,3).join('-')}
                    </span>
                  </div>
                )}

              </div>
            </header>

            {/* Main view panel */}
            <main className="flex-1 overflow-y-auto px-10 py-8">
              {tab === 'dashboard' && (
                <Dashboard
                  onNavigateToOutreach={goToOutreach}
                  onNavigateToPipeline={() => setTab('pipeline')}
                />
              )}
              {tab === 'pipeline' && <Pipeline onCandidatesReady={() => setTab('candidates')} />}
              {tab === 'candidates' && <Candidates onGenerateOutreach={goToOutreach} />}
              {tab === 'outreach' && <Outreach candidate={selectedCandidate} />}
            </main>
          </div>
        </>
      )}
    </div>
  )
}
