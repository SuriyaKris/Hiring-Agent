import React, { useState, useEffect } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

const VERDICT_COLORS = {
  shortlist: 'bg-green-50 text-green-700 border-green-100',
  reject: 'bg-red-50 text-red-700 border-red-100 opacity-60',
  maybe: 'bg-amber-50 text-amber-700 border-amber-100',
  pending: 'bg-slate-50 text-slate-500 border-slate-200',
}

export default function Candidates({ onGenerateOutreach, sessionId }) {
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const [useEngineered, setUseEngineered] = useState(true)
  const [expFilter, setExpFilter] = useState('all')
  const [topLimit, setTopLimit] = useState('all')

  const load = async () => {
    try {
      setLoading(true)
      const url = sessionId
        ? `/api/me/sessions/${sessionId}/candidates`
        : '/api/candidates'
      const { data } = await axios.get(url)
      setCandidates(data)
    } catch { toast.error('Failed to load candidates.') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [sessionId])

  const setVerdict = async (linkedinUrl, verdict) => {
    try {
      await axios.patch('/api/candidates/verdict', { candidate_linkedin_url: linkedinUrl, verdict })
      setCandidates(prev => prev.map(c => c.linkedin_url === linkedinUrl ? { ...c, recruiter_verdict: verdict } : c))
      toast.success(`Marked as ${verdict}`)
    } catch { toast.error('Update failed.') }
  }

  const enrichCandidate = async (linkedinUrl) => {
    const toastId = toast.loading('Enriching candidate profile...')
    try {
      const { data } = await axios.post('/api/candidates/enrich', { candidate_linkedin_url: linkedinUrl })
      setCandidates(prev => prev.map(c => c.linkedin_url === linkedinUrl ? {
        ...c,
        email: data.basic_info?.email || '',
        phone: data.basic_info?.phone || '',
        full_name: data.basic_info?.full_name || c.full_name,
        profile_details: {
          ...c.profile_details,
          ...data.metadata?.raw_data
        }
      } : c))
      toast.success('Profile enriched successfully!', { id: toastId })
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Enrichment failed.'
      toast.error(errorMsg, { id: toastId })
    }
  }

  const sortedAndFiltered = [...candidates]
    .sort((a, b) => {
      const aScore = useEngineered && a.profile_details?.engineered_fitment_score !== undefined
        ? a.profile_details.engineered_fitment_score
        : a.fitment_score;
      const bScore = useEngineered && b.profile_details?.engineered_fitment_score !== undefined
        ? b.profile_details.engineered_fitment_score
        : b.fitment_score;
      return bScore - aScore;
    })
    .filter(c => filter === 'all' || c.recruiter_verdict === filter)
    .filter(c => !search || c.full_name.toLowerCase().includes(search.toLowerCase()) ||
      c.current_company.toLowerCase().includes(search.toLowerCase()) ||
      c.current_title.toLowerCase().includes(search.toLowerCase()))
    .filter(c => {
      if (expFilter === 'all') return true;
      const expStr = c.profile_details?.total_experience_years || "";
      const expMatch = expStr.match(/^([0-9.]+)\s*year/);
      const years = expMatch ? parseFloat(expMatch[1]) : 0;
      
      if (expFilter === '0-1') return years >= 0 && years <= 1;
      if (expFilter === '1-3') return years > 1 && years <= 3;
      if (expFilter === '3-5') return years > 3 && years <= 5;
      if (expFilter === '5-7') return years > 5 && years <= 7;
      if (expFilter === '7+') return years > 7;
      return true;
    })

  const filtered = topLimit === 'all'
    ? sortedAndFiltered
    : sortedAndFiltered.slice(0, Number(topLimit))

  if (loading) return <div className="text-center py-12 text-slate-500 text-sm">Loading candidates...</div>

  return (
    <div className="space-y-5 select-none animate-fade-in-up">
      {/* Controls row */}
      <div className="flex items-center gap-3">
        <input 
          value={search} 
          onChange={e => setSearch(e.target.value)}
          placeholder="Search name, company, title..."
          className="flex-1 bg-[#edf2fa] border border-slate-200/75 rounded-xl px-4.5 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:bg-white text-slate-800 transition-all font-semibold" 
        />
        <div className="flex gap-1.5 bg-slate-100 p-1 rounded-xl">
          {['all', 'shortlist', 'maybe', 'pending', 'reject'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all outline-none ${
                filter === f ? 'bg-white text-slate-850 shadow-sm border border-slate-200/40' : 'text-slate-500 hover:text-slate-800'
              }`}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
              {' '}({candidates.filter(c => f === 'all' ? true : c.recruiter_verdict === f).length})
            </button>
          ))}
        </div>
        <button 
          onClick={load} 
          className="text-slate-450 hover:text-slate-700 bg-[#edf2fa] hover:bg-slate-200/60 p-2.5 rounded-xl transition-all border border-slate-200/40 outline-none" 
          title="Refresh"
        >
          ↻
        </button>
        <button 
          onClick={() => window.open('/api/candidates/export', '_blank')} 
          className="bg-[#0B57D0] hover:bg-[#0842a0] text-white px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm outline-none"
          title="Export to Excel"
        >
          📥 Export
        </button>
      </div>

      {/* Grid of filters */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Experience Filter Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">EXPERIENCE LEVEL:</span>
            <div className="flex flex-wrap gap-1.5">
              {['all', '0-1', '1-3', '3-5', '5-7', '7+'].map(opt => {
                const count = candidates.filter(c => {
                  const expStr = c.profile_details?.total_experience_years || "";
                  const expMatch = expStr.match(/^([0-9.]+)\s*year/);
                  const years = expMatch ? parseFloat(expMatch[1]) : 0;
                  
                  if (opt === 'all') return true;
                  if (opt === '0-1') return years >= 0 && years <= 1;
                  if (opt === '1-3') return years > 1 && years <= 3;
                  if (opt === '3-5') return years > 3 && years <= 5;
                  if (opt === '5-7') return years > 5 && years <= 7;
                  if (opt === '7+') return years > 7;
                  return true;
                }).length;

                return (
                  <button 
                    key={opt} 
                    onClick={() => setExpFilter(opt)}
                    className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all outline-none ${
                      expFilter === opt
                        ? 'bg-blue-50 text-blue-700 border border-blue-100 shadow-sm'
                        : 'bg-slate-100 text-slate-650 hover:bg-slate-200'
                    }`}
                  >
                    {opt === 'all' ? 'All' : `${opt} yrs`} ({count})
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Top limit filter */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 flex items-center shadow-sm">
          <div className="flex items-center gap-3">
            <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">LIMIT DISPLAY:</span>
            <select
              value={topLimit}
              onChange={e => setTopLimit(e.target.value)}
              className="border border-slate-200 bg-[#edf2fa] text-slate-750 font-bold rounded-lg px-3 py-1 text-xs focus:ring-1 focus:ring-blue-500 cursor-pointer outline-none"
            >
              <option value="all">All Candidates</option>
              <option value="5">Top 5</option>
              <option value="10">Top 10</option>
              <option value="15">Top 15</option>
              <option value="20">Top 20</option>
            </select>
          </div>
        </div>
      </div>

      {/* Stats Summary Cards */}
      {candidates.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Sourced', val: candidates.length, color: 'text-slate-800' },
            { label: 'Recommended AEs', val: candidates.filter(c => c.recommended_action === 'Reach out now').length, color: 'text-green-700' },
            { label: 'Shortlisted AEs', val: candidates.filter(c => c.recruiter_verdict === 'shortlist').length, color: 'text-blue-700' },
            { label: 'Average Match Score', val: Math.round(candidates.reduce((a, c) => a + c.fitment_score, 0) / candidates.length) + '%', color: 'text-slate-800' },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-2xl border border-slate-200 p-4 text-center shadow-sm">
              <p className={`text-2xl font-extrabold ${s.color}`}>{s.val}</p>
              <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Candidate Grid list */}
      {filtered.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center shadow-sm select-none">
          <span className="text-3xl">👥</span>
          <h3 className="text-sm font-semibold text-slate-850 mt-3">
            {candidates.length === 0
              ? 'No candidates found. Trigger a pipeline run.'
              : 'No candidates match your current filter.'}
          </h3>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((c, i) => {
            const hasEngineered = c.profile_details?.engineered_fitment_score !== undefined && c.profile_details?.engineered_fitment_score !== null;
            const score = useEngineered && hasEngineered
              ? c.profile_details.engineered_fitment_score
              : c.fitment_score;

            const isShortlisted = c.recruiter_verdict === 'shortlist';
            const isRejected = c.recruiter_verdict === 'reject';

            return (
              <div 
                key={i} 
                className={`bg-white rounded-2xl border transition-all p-5 shadow-sm ${
                  isShortlisted ? 'border-green-300 ring-1 ring-green-100' :
                  isRejected ? 'border-red-150 opacity-60' :
                  'border-slate-200'
                }`}
              >
                <div className="flex items-start gap-4">
                  {/* Fitment score circle badge */}
                  <div className={`shrink-0 w-12 h-12 rounded-xl flex flex-col items-center justify-center font-bold shadow-sm ${
                    score >= 75 ? 'bg-green-50 text-green-700 border border-green-150' :
                    score >= 50 ? 'bg-amber-50 text-amber-700 border border-amber-150' :
                    'bg-red-50 text-red-650 border border-red-150'
                  }`}>
                    <span className="text-base leading-none font-extrabold">{Math.round(score)}</span>
                    <span className="text-[9px] opacity-75 font-semibold mt-0.5">%</span>
                  </div>

                  {/* Candidate Primary Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {c.linkedin_url ? (
                        <a 
                          href={c.linkedin_url} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          className="font-bold text-blue-600 hover:text-blue-800 text-[14px] flex items-center gap-1 leading-none"
                        >
                          {c.full_name}
                          <span className="text-[10px] opacity-60">🔗</span>
                        </a>
                      ) : (
                        <p className="font-bold text-slate-800 text-[14px] leading-none">{c.full_name}</p>
                      )}
                      {c.is_open_to_work && (
                        <span className="text-[10px] font-bold bg-green-55 text-green-700 px-2 py-0.5 rounded-full border border-green-100">Open to work</span>
                      )}
                    </div>
                    <p className="text-xs text-slate-650 font-semibold leading-relaxed">{c.current_title} · {c.current_company}</p>
                    <p className="text-xs text-slate-400 font-medium mt-0.5">{c.location}</p>
                    <p className="text-xs text-slate-500 font-medium mt-2 leading-relaxed bg-[#f8fafc] border border-slate-100 rounded-xl p-3">{c.score_reasoning}</p>

                    {/* Feature Engineering Breakdown */}
                    {useEngineered && c.profile_details?.engineered_features ? (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {Object.entries(c.profile_details.engineered_features).map(([k, v]) => {
                          let displayVal = v;
                          if (v === null || v === undefined) {
                            displayVal = 'N/A';
                          } else if (k.includes('match') || k.includes('sim')) {
                            displayVal = `${Math.round(v * 100)}%`;
                          } else {
                            displayVal = `${v.toFixed(1)} yrs`;
                          }
                          return (
                            <span key={k} className="text-[9px] bg-blue-50/50 text-[#0B57D0] border border-blue-100 rounded-lg px-2 py-0.5 font-extrabold tracking-wide uppercase">
                              {k.replace(/_/g, ' ')}: {displayVal}
                            </span>
                          );
                        })}
                      </div>
                    ) : (
                      c.score_breakdown && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {Object.entries(c.score_breakdown).filter(([k]) => k !== 'bonuses').map(([k, v]) => (
                            <span key={k} className="text-[9px] bg-slate-50 text-slate-500 border border-slate-200 rounded-lg px-2 py-0.5 font-extrabold uppercase">
                              {k.replace('_', ' ')}: {v}
                            </span>
                          ))}
                        </div>
                      )
                    )}
                  </div>

                  {/* Actions column */}
                  <div className="shrink-0 flex flex-col gap-2 items-end">
                    {c.email && (
                      <span className="text-[10px] text-green-700 font-bold bg-green-50 px-2.5 py-1 rounded-lg border border-green-100 inline-flex items-center gap-1" title={c.email}>
                        ✉️ {c.email}
                      </span>
                    )}
                    {!c.email && (
                      <button
                        onClick={() => enrichCandidate(c.linkedin_url)}
                        className="text-[10px] bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg font-bold shadow-sm transition-all outline-none"
                      >
                        ⚡ Enrich Profile
                      </button>
                    )}

                    {/* Verdict actions */}
                    <div className="flex gap-1 border border-slate-200/50 p-0.5 bg-slate-50 rounded-lg">
                      {['shortlist', 'maybe', 'reject'].map(v => (
                        <button key={v} onClick={() => setVerdict(c.linkedin_url, v)}
                          className={`text-[10px] px-2 py-1 rounded-md font-bold transition-all outline-none capitalize ${
                            c.recruiter_verdict === v
                              ? VERDICT_COLORS[v] + ' shadow-sm'
                              : 'text-slate-400 hover:text-slate-700'
                          }`}>
                          {v}
                        </button>
                      ))}
                    </div>

                    {/* Generate Outreach Button */}
                    <button 
                      onClick={() => onGenerateOutreach({
                        profile: c.profile_details || {
                          basic_info: {
                            full_name: c.full_name,
                            linkedin_url: c.linkedin_url,
                            email: c.email || '',
                            phone: c.phone || '',
                            headline: c.headline || '',
                            location: c.location || '',
                          },
                          experience: [],
                          skills: [],
                          education: [],
                        },
                        fitment_score: c.fitment_score,
                        score_breakdown: {
                          title_match: c.score_breakdown?.title_match ?? 0,
                          skills_match: c.score_breakdown?.skills_match ?? 0,
                          crm_background: c.score_breakdown?.crm_background ?? 0,
                          job_stability: c.score_breakdown?.job_stability ?? 0,
                          geography: c.score_breakdown?.geography ?? 0,
                          bonuses: c.score_breakdown?.bonuses ?? 0,
                        },
                        score_reasoning: c.score_reasoning,
                        recommended_action: c.recommended_action,
                      })}
                      className="text-[10px] bg-blue-50 text-blue-700 px-3 py-1.5 rounded-lg hover:bg-blue-100 border border-blue-150 transition-all font-bold outline-none"
                    >
                      ✉️ Generate Outreach
                    </button>

                    {/* Expansion details button */}
                    <button 
                      onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                      className="text-[10px] bg-slate-50 text-slate-700 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-all font-bold border border-slate-200 outline-none"
                    >
                      {expandedId === c.id ? 'Hide Details' : '🔍 View Details'}
                    </button>
                  </div>
                </div>

                {/* Candidate detailed profile expansion panel */}
                {expandedId === c.id && (
                  <div className="mt-5 pt-5 border-t border-dashed border-slate-200 space-y-5">
                    {/* Sourcing & Profile Details Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-[#f8fafc] rounded-2xl p-5 text-xs border border-slate-200/50">
                      <div>
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Name</span>
                        <p className="font-bold text-slate-800 mt-1">{c.full_name || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Persona</span>
                        <p className="font-bold text-slate-800 mt-1">{c.profile_details?.persona || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Email Status</span>
                        <p className="mt-1">
                          <span className={`inline-block px-2 py-0.5 rounded font-bold text-[9px] uppercase tracking-wide border ${
                            c.profile_details?.email_status === 'verified' 
                              ? 'bg-green-50 text-green-700 border-green-150' 
                              : 'bg-slate-50 text-slate-500 border-slate-200'
                          }`}>
                            {c.profile_details?.email_status || 'N/A'}
                          </span>
                        </p>
                      </div>
                      <div>
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Enrichment Source</span>
                        <p className="font-bold text-slate-800 mt-1">{c.profile_details?.enrichment_type || 'N/A'}</p>
                      </div>
                      <div className="col-span-2">
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Email Address</span>
                        <p className="font-bold text-slate-800 mt-1 truncate" title={c.email}>{c.email || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Time Zone</span>
                        <p className="font-bold text-slate-800 mt-1">{c.profile_details?.time_zone || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Total Experience</span>
                        <p className="font-bold text-slate-800 mt-1">{c.profile_details?.total_experience_years || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Time in Current Role</span>
                        <p className="font-bold text-slate-800 mt-1">{c.profile_details?.time_in_current_role || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Job Changes</span>
                        <p className="font-bold text-slate-800 mt-1">
                          {c.profile_details?.job_change_count ? `${c.profile_details.job_change_count} total roles` : 'N/A'}
                          {c.profile_details?.last_job_change && c.profile_details.last_job_change !== 'N/A' && (
                            <span className="text-[9px] text-slate-400 block font-semibold mt-0.5">Last: {c.profile_details.last_job_change}</span>
                          )}
                        </p>
                      </div>
                      <div className="col-span-2">
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Territories</span>
                        <p className="font-bold text-slate-800 mt-1" title={c.profile_details?.territories}>{c.profile_details?.territories || 'N/A'}</p>
                      </div>
                    </div>

                    {/* Work URLs */}
                    {c.profile_details?.work_urls && c.profile_details.work_urls.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Work URLs</h4>
                        <div className="flex flex-wrap gap-2 text-xs">
                          {c.profile_details.work_urls.map((link, idx) => (
                            <a key={idx} href={link.url} target="_blank" rel="noopener noreferrer" className="bg-blue-50/50 text-[#0B57D0] hover:bg-blue-100/50 font-bold px-3 py-1.5 rounded-lg border border-blue-100 flex items-center gap-1 transition-colors">
                              <span>🔗</span> {link.name}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* About */}
                    {c.profile_details?.summary?.about && (
                      <div className="space-y-2">
                        <h4 className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">About / Summary</h4>
                        <p className="text-xs text-slate-650 bg-[#f8fafc] border border-slate-200/50 rounded-xl p-4 italic leading-relaxed">
                          "{c.profile_details.summary.about}"
                        </p>
                      </div>
                    )}

                    {/* Experience list */}
                    {c.profile_details?.experience && c.profile_details.experience.length > 0 && (
                      <div className="space-y-3">
                        <h4 className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Work Experience History</h4>
                        <div className="space-y-4">
                          {c.profile_details.experience.map((exp, idx) => (
                            <div key={idx} className="text-xs pl-4 border-l-2 border-slate-250 py-0.5 space-y-0.5">
                              <div className="flex justify-between items-start">
                                <span className="font-bold text-slate-800">{exp.title}</span>
                                <span className="text-slate-400 font-bold text-[9px] uppercase tracking-wider">{exp.start_date}</span>
                              </div>
                              <p className="text-slate-500 font-bold">{exp.company_name}</p>
                              {exp.description && (
                                <p className="text-slate-500 mt-1.5 leading-relaxed font-medium">{exp.description}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Education */}
                    {c.profile_details?.education && c.profile_details.education.length > 0 && (
                      <div className="space-y-3">
                        <h4 className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Education</h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          {c.profile_details.education.map((edu, idx) => (
                            <div key={idx} className="bg-[#f8fafc] border border-slate-200/50 rounded-xl p-4">
                              <p className="font-bold text-slate-800 text-xs">{edu.school_name}</p>
                              <p className="text-slate-500 text-[11px] font-bold mt-1">{edu.degree} {edu.field_of_study ? `in ${edu.field_of_study}` : ''}</p>
                              {(edu.start_date || edu.end_date) && (
                                <p className="text-slate-400 text-[10px] font-bold uppercase tracking-wider mt-1">{edu.start_date} - {edu.end_date}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Awards & Certifications */}
                    {((c.profile_details?.certifications && c.profile_details.certifications.length > 0) || 
                      (c.profile_details?.awards && c.profile_details.awards.length > 0)) && (
                      <div className="space-y-3">
                        <h4 className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Awards & Certifications</h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          {c.profile_details?.certifications?.map((cert, idx) => (
                            <div key={`cert-${idx}`} className="bg-[#f8fafc] border border-slate-200/50 rounded-xl p-4">
                              <p className="font-bold text-slate-800 text-xs">🎓 {cert.name}</p>
                              <p className="text-slate-500 text-[11px] font-semibold mt-1">{cert.authority} {cert.license_number ? `· ${cert.license_number}` : ''}</p>
                            </div>
                          ))}
                          {c.profile_details?.awards?.map((award, idx) => (
                            <div key={`award-${idx}`} className="bg-[#f8fafc] border border-slate-200/50 rounded-xl p-4">
                              <p className="font-bold text-slate-800 text-xs">🏆 {award.title}</p>
                              <p className="text-slate-500 text-[11px] font-semibold mt-1">{award.issuer} {award.issue_date ? `· ${award.issue_date}` : ''}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Skills list */}
                    {c.profile_details?.skills && c.profile_details.skills.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Skills</h4>
                        <div className="flex flex-wrap gap-1.5">
                          {c.profile_details.skills.map((skill, idx) => (
                            <span key={idx} className="bg-blue-50/60 text-[#0B57D0] border border-blue-100 rounded-lg px-2.5 py-0.5 text-[10px] font-extrabold tracking-wide uppercase">
                              {skill.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
