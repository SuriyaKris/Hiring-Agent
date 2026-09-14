import React, { useState, useEffect } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import Candidates from './Candidates'

export default function Dashboard({ onNavigateToOutreach, onNavigateToPipeline }) {
  const [view, setView] = useState('roles') // 'roles' | 'sessions' | 'candidates'
  const [roles, setRoles] = useState([])
  const [selectedRole, setSelectedRole] = useState(null)
  const [sessions, setSessions] = useState([])
  const [selectedSession, setSelectedSession] = useState(null)
  const [loading, setLoading] = useState(true)

  // 1. Fetch all role tracks
  const loadRoles = async () => {
    try {
      setLoading(true)
      const { data } = await axios.get('/api/me/roles')
      setRoles(data)
    } catch (err) {
      if (err.response?.status !== 401) {
        toast.error(err.response?.data?.detail || 'Failed to load roles dashboard.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (view === 'roles') {
      loadRoles()
    }
  }, [view])

  // 2. Drill down: Select a role track -> load sessions
  const handleSelectRole = async (role) => {
    try {
      setLoading(true)
      setSelectedRole(role)
      const { data } = await axios.get(`/api/me/roles/${role.role_track_id}/sessions`)
      setSessions(data)
      setView('sessions')
    } catch (err) {
      if (err.response?.status !== 401) {
        toast.error(err.response?.data?.detail || 'Failed to load search history sessions.')
      }
    } finally {
      setLoading(false)
    }
  }

  // 3. Drill down: Select a session -> show candidates
  const handleSelectSession = (session) => {
    setSelectedSession(session)
    setView('candidates')
  }

  // Back button helper
  const handleBack = () => {
    if (view === 'candidates') {
      setView('sessions')
      setSelectedSession(null)
    } else if (view === 'sessions') {
      setView('roles')
      setSelectedRole(null)
      setSessions([])
    }
  }

  const formatDate = (isoString) => {
    if (!isoString) return 'Never'
    const date = new Date(isoString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading && view === 'roles') {
    return <div className="text-center py-12 text-slate-500 text-sm">Loading dashboard...</div>
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Navigation Breadcrumb & Title */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {view !== 'roles' && (
            <button
              onClick={handleBack}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg flex items-center gap-1.5 transition-all shadow-sm active:scale-95"
            >
              ← Back
            </button>
          )}
          <div>
            <h2 className="text-lg font-bold text-slate-800">
              {view === 'roles' && 'Recruiter Sourcing Dashboard'}
              {view === 'sessions' && `${selectedRole?.role_name} Search History`}
              {view === 'candidates' && `Candidates for Search Run (${formatDate(selectedSession?.created_at)})`}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {view === 'roles' && 'Overview of all structured job role pipelines'}
              {view === 'sessions' && 'Historical search sessions mapped to this role'}
              {view === 'candidates' && `Showing candidates found during this specific search session`}
            </p>
          </div>
        </div>
      </div>

      {/* View Router */}
      {view === 'roles' && (
        <>
          {roles.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-sm animate-fade-in">
              <h3 className="text-sm font-semibold text-slate-800 mt-1">No search history yet</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Once you run a sourcing search in the ⚡ Run Pipeline tab, history results will cluster here.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {roles.map((r, idx) => (
                <div
                  key={r.role_track_id}
                  onClick={() => handleSelectRole(r)}
                  className={`bg-white border rounded-xl p-5 cursor-pointer flex flex-col justify-between h-44 shadow-sm hover-card-premium ${
                    idx === 0
                      ? 'border-blue-500 border-dashed border-2'
                      : 'border-slate-200'
                  }`}
                >
                  <div>
                    <div className="flex justify-between items-start">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-semibold border border-blue-100">
                        {r.search_count} {r.search_count === 1 ? 'Search' : 'Searches'}
                      </span>
                      <button className="text-slate-400 hover:text-slate-600 p-0.5">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M6 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm12 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm-6 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
                        </svg>
                      </button>
                    </div>
                    <h3 className="text-sm font-bold text-slate-800 mt-3 line-clamp-1">{r.role_name}</h3>
                  </div>

                  <div className="border-t border-slate-100 pt-3 mt-4 flex items-end justify-between">
                    <div>
                      <p className="text-[10px] uppercase font-semibold text-slate-400 leading-none">Total Unique Profiles</p>
                      <p className="text-2xl font-extrabold text-slate-800 mt-1 leading-none">{r.candidate_count}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] uppercase font-semibold text-slate-400 leading-none">Last Searched</p>
                      <p className="text-xs text-slate-650 font-bold mt-1.5 leading-none">{formatDate(r.last_search_at).split(',')[0]}</p>
                    </div>
                  </div>
                </div>
              ))}

              {/* Create New Pipeline Card */}
              <div
                onClick={onNavigateToPipeline}
                className="bg-blue-50/10 border border-dashed border-slate-300 rounded-xl p-5 hover:bg-blue-50/20 hover:border-blue-400 cursor-pointer flex flex-col items-center justify-center text-center h-44 shadow-sm hover-card-premium"
              >
                <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-blue-600 mb-3 font-semibold text-lg">
                  +
                </div>
                <h3 className="text-xs font-bold text-slate-800">Create New Pipeline</h3>
                <p className="text-[10px] text-slate-400 mt-1 font-medium">Configure AI sourcing rules</p>
              </div>
            </div>
          )}
        </>
      )}

      {view === 'sessions' && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="px-6 py-4">Search Date</th>
                  <th className="px-6 py-4">Snippet Job Details</th>
                  <th className="px-6 py-4 text-center">Profiles Found</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm text-slate-600">
                {sessions.map((s) => (
                  <tr key={s.session_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-slate-800">
                      {formatDate(s.created_at)}
                    </td>
                    <td className="px-6 py-4 max-w-xs truncate text-xs text-slate-500">
                      {s.jd_snippet}
                    </td>
                    <td className="px-6 py-4 text-center font-semibold text-slate-700">
                      {s.candidate_count}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleSelectSession(s)}
                        className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold shadow-sm transition-all"
                      >
                        Browse Candidates →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {view === 'candidates' && selectedSession && (
        <Candidates
          sessionId={selectedSession.session_id}
          onGenerateOutreach={onNavigateToOutreach}
        />
      )}
    </div>
  )
}
