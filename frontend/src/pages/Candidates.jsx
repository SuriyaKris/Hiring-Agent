import React, { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import axios from 'axios'
import toast from 'react-hot-toast'

const VERDICT_COLORS = {
  shortlist: 'bg-green-50 text-green-700 border-green-100',
  reject: 'bg-red-50 text-red-700 border-red-100 opacity-60',
  maybe: 'bg-amber-50 text-amber-700 border-amber-100',
  pending: 'bg-slate-50 text-slate-500 border-slate-200',
}

function buildOutreachEmail(candidate, roleNameParam, companyNameParam, recruiterNameParam) {
  if (!candidate) return { subject: '', body: '' }
  const role = roleNameParam || candidate.role_name || 'Inside Sales – US Region'
  const company = companyNameParam || '4CECloud Labs'
  const recruiter = recruiterNameParam || 'Meghana'
  const name = candidate.full_name || 'there'
  const title = candidate.current_title || 'Sales Professional'
  const companyPhrase = candidate.current_company ? ` at ${candidate.current_company}` : ''

  const subject = `Exciting Career Opportunity: ${role} role at ${company}`
  const body = `Hi ${name},\n\nI hope this email finds you well.\n\nI’m ${recruiter}, a recruiter at ${company}. I came across your profile and was very impressed by your background as ${title}${companyPhrase}.\n\nWe are currently expanding our team and looking for a driven professional to fill our ${role} role. Your track record suggests you could be a fantastic fit for our aggressive growth strategy over the next 12 months.\n\nWould you be open to a brief introductory call next week to discuss this opportunity further?\n\nBest regards,\n\n${recruiter}\n${company}`

  return { subject, body }
}

function normalizeCandidate(c, defaultRole = '') {
  if (!c) return null
  const profile = c.profile || c.profile_details || {}
  const basic = profile.basic_info || {}
  const expList = profile.experience || []
  const currentExp = expList[0] || {}

  const fullName = c.full_name || basic.full_name || 'Unknown'
  const currentTitle = c.current_title || currentExp.title || basic.headline || ''
  const currentCompany = c.current_company || currentExp.company_name || profile.company?.name || ''
  const location = c.location || basic.location || ''
  const linkedinUrl = c.linkedin_url || basic.linkedin_url || ''
  const email = c.email || basic.email || ''
  const phone = c.phone || basic.phone || ''
  const isOpen = c.is_open_to_work ?? (profile.metadata?.raw_data?.is_open_to_work || false)
  const score = c.fitment_score ?? 0
  const scoreReasoning = c.score_reasoning || ''
  const scoreBreakdown = c.score_breakdown || {}
  const recommendedAction = c.recommended_action || (score >= 75 ? 'Reach out now' : score >= 50 ? 'Consider' : 'Skip')
  const role = c.role_name || defaultRole || ''
  const verdict = c.recruiter_verdict || 'pending'

  return {
    ...c,
    id: c.id || linkedinUrl || fullName,
    full_name: fullName,
    current_title: currentTitle,
    current_company: currentCompany,
    location: location,
    linkedin_url: linkedinUrl,
    email: email,
    phone: phone,
    is_open_to_work: isOpen,
    fitment_score: score,
    score_reasoning: scoreReasoning,
    score_breakdown: scoreBreakdown,
    recommended_action: recommendedAction,
    role_name: role,
    recruiter_verdict: verdict,
    profile_details: {
      ...profile,
      basic_info: {
        ...basic,
        full_name: fullName,
        linkedin_url: linkedinUrl,
        email: email,
        phone: phone,
        location: location,
        headline: basic.headline || currentTitle,
      },
      experience: expList,
      skills: profile.skills || [],
      education: profile.education || [],
      certifications: profile.certifications || [],
      awards: profile.awards || [],
    }
  }
}

export default function Candidates({
  onGenerateOutreach,
  sessionId,
  roleName,
  initialCandidates,
  onClearSessionFilter
}) {
  const [candidates, setCandidates] = useState(() => {
    if (initialCandidates && initialCandidates.length > 0) {
      return initialCandidates.map(c => normalizeCandidate(c, roleName))
    }
    return []
  })
  const [loading, setLoading] = useState(!initialCandidates || initialCandidates.length === 0)
  const [filter, setFilter] = useState('all')
  const [roleFilter, setRoleFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const [useEngineered, setUseEngineered] = useState(true)
  const [expFilter, setExpFilter] = useState('all')
  const [topLimit, setTopLimit] = useState('all')
  const [queueModalOpen, setQueueModalOpen] = useState(false)
  const [queueList, setQueueList] = useState([])
  const [queueIndex, setQueueIndex] = useState(0)
  const [queueSubject, setQueueSubject] = useState('')
  const [queueBody, setQueueBody] = useState('')
  const [queueRecruiterName, setQueueRecruiterName] = useState('Meghana')
  const [queueCompanyName, setQueueCompanyName] = useState('4CECloud Labs')
  const [activeSessionId, setActiveSessionId] = useState(sessionId || null)
  const [bulkPhoneModalOpen, setBulkPhoneModalOpen] = useState(false)
  const [bulkPhoneLoading, setBulkPhoneLoading] = useState(false)
  const [enrichingUrl, setEnrichingUrl] = useState(null)

  const shortlistedCandidates = candidates.filter(c => c.recruiter_verdict?.toLowerCase() === 'shortlist')
  const shortlistedWithoutPhone = shortlistedCandidates.filter(c => !c.phone || !c.phone.trim())

  const startBulkOutreachQueue = () => {
    const shortlisted = shortlistedCandidates
    if (shortlisted.length === 0) {
      toast.error('No shortlisted candidates found. Please mark candidates as "Shortlist" first.')
      return
    }

    const withEmail = shortlisted.filter(c => (c.email || c.profile_details?.basic_info?.email || c.profile_details?.email || '').trim())
    if (withEmail.length === 0) {
      toast.error('None of the shortlisted candidates have email addresses. Please enrich profiles first.')
      return
    }

    if (withEmail.length < shortlisted.length) {
      const skipped = shortlisted.length - withEmail.length
      toast(`${withEmail.length} shortlisted candidates queued (${skipped} skipped without email).`, { icon: 'ℹ️' })
    }

    setQueueList(withEmail)
    setQueueIndex(0)
    const initialTpl = buildOutreachEmail(withEmail[0], roleName || withEmail[0].role_name, queueCompanyName, queueRecruiterName)
    setQueueSubject(initialTpl.subject)
    setQueueBody(initialTpl.body)
    setQueueModalOpen(true)
  }

  const processQueueNext = async () => {
    if (queueIndex >= queueList.length) return
    const curr = queueList[queueIndex]
    const email = (curr.email || curr.profile_details?.basic_info?.email || curr.profile_details?.email || '').trim()

    if (!email) {
      toast.error(`No email address available for ${curr.full_name}`)
      return
    }

    const targetRole = curr.role_name || roleName || 'Inside Sales – US Region'
    const subject = queueSubject || `Exciting Career Opportunity: ${targetRole} role at ${queueCompanyName}`
    const body = queueBody || `Hi ${curr.full_name},\n\nWould you be open to connecting regarding an opportunity at ${queueCompanyName}?`

    // Open Gmail web compose in a new tab
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(email)}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    const newWin = window.open(gmailUrl, '_blank')
    if (!newWin || newWin.closed || typeof newWin.closed === 'undefined') {
      toast('Popup blocked by browser. Please allow popups to open Gmail automatically.', { icon: '⚠️', duration: 4000 })
    }

    // Save sent outreach record to backend
    try {
      await axios.post('/api/outreach/save', {
        candidate_linkedin_url: curr.linkedin_url || '',
        candidate_name: curr.full_name,
        role_name: targetRole,
        channel: 'email',
        message_sent: body,
      })
    } catch (err) {
      console.warn('Failed to record outreach history:', err)
    }

    if (queueIndex + 1 < queueList.length) {
      const nextIdx = queueIndex + 1
      setQueueIndex(nextIdx)
      const nextCandidate = queueList[nextIdx]
      const nextTpl = buildOutreachEmail(nextCandidate, roleName || nextCandidate.role_name, queueCompanyName, queueRecruiterName)
      setQueueSubject(nextTpl.subject)
      setQueueBody(nextTpl.body)
      toast.success(`Opened Gmail for ${curr.full_name}. Candidate ${nextIdx + 1} of ${queueList.length} ready!`)
    } else {
      toast.success(`Completed outreach for all ${queueList.length} shortlisted candidates! 🎉`)
      setQueueModalOpen(false)
    }
  }

  const skipQueueCandidate = () => {
    if (queueIndex + 1 < queueList.length) {
      const nextIdx = queueIndex + 1
      setQueueIndex(nextIdx)
      const nextCandidate = queueList[nextIdx]
      const nextTpl = buildOutreachEmail(nextCandidate, roleName || nextCandidate.role_name, queueCompanyName, queueRecruiterName)
      setQueueSubject(nextTpl.subject)
      setQueueBody(nextTpl.body)
      toast('Skipped to next candidate', { icon: '⏭️' })
    } else {
      toast.success('Queue completed.')
      setQueueModalOpen(false)
    }
  }

  const copyQueueEmailContent = () => {
    const fullText = `Subject: ${queueSubject}\n\n${queueBody}`
    navigator.clipboard.writeText(fullText)
    toast.success('Email draft copied to clipboard!')
  }

  const openCurrentInOutreachPage = () => {
    if (!queueList[queueIndex]) return
    const curr = queueList[queueIndex]
    setQueueModalOpen(false)
    onGenerateOutreach?.({
      profile: curr.profile_details || {
        basic_info: {
          full_name: curr.full_name,
          linkedin_url: curr.linkedin_url,
          email: curr.email || '',
          phone: curr.phone || '',
          headline: curr.headline || '',
          location: curr.location || '',
        },
        experience: [],
        skills: [],
        education: [],
      },
      fitment_score: curr.fitment_score,
      score_breakdown: curr.score_breakdown || {},
      score_reasoning: curr.score_reasoning,
      recommended_action: curr.recommended_action,
    })
  }

  useEffect(() => {
    if (initialCandidates && initialCandidates.length > 0) {
      setCandidates(initialCandidates.map(c => normalizeCandidate(c, roleName)))
      setLoading(false)
      setActiveSessionId(sessionId || null)
    } else {
      setActiveSessionId(sessionId || null)
    }
  }, [sessionId, initialCandidates, roleName])

  const load = async () => {
    // If initialCandidates is active for this session, avoid overriding with global fetch
    if (initialCandidates && initialCandidates.length > 0 && activeSessionId === sessionId) {
      return
    }
    try {
      setLoading(true)
      const url = activeSessionId
        ? `/api/candidates?session_id=${encodeURIComponent(activeSessionId)}`
        : '/api/candidates'
      const { data } = await axios.get(url)
      setCandidates(data.map(c => normalizeCandidate(c, roleName)))
    } catch { toast.error('Failed to load candidates.') }
    finally { setLoading(false) }
  }

  useEffect(() => {
    if (!initialCandidates || initialCandidates.length === 0 || activeSessionId !== sessionId) {
      load()
    }
  }, [activeSessionId])

  const handleExport = () => {
    let exportUrl = '/api/candidates/export'
    const params = new URLSearchParams()
    if (activeSessionId) {
      params.append('session_id', activeSessionId)
    } else if (roleFilter && roleFilter !== 'all') {
      params.append('role_name', roleFilter)
    }
    const queryString = params.toString()
    if (queryString) {
      exportUrl += `?${queryString}`
    }
    window.open(exportUrl, '_blank')
  }

  const setVerdict = async (linkedinUrl, verdict) => {
    try {
      await axios.patch('/api/candidates/verdict', { candidate_linkedin_url: linkedinUrl, verdict })
      setCandidates(prev => prev.map(c => c.linkedin_url === linkedinUrl ? { ...c, recruiter_verdict: verdict } : c))
      toast.success(`Marked as ${verdict}`)
    } catch { toast.error('Update failed.') }
  }

  const enrichCandidate = async (linkedinUrl) => {
    setEnrichingUrl(linkedinUrl)
    const toastId = toast.loading('Looking up contact & mobile number via Apollo...')
    try {
      const { data } = await axios.post('/api/candidates/enrich', { candidate_linkedin_url: linkedinUrl })
      await load()
      if (data.basic_info?.phone) {
        toast.success(`Mobile found: ${data.basic_info.phone}`, { id: toastId, duration: 4000 })
      } else if (data.basic_info?.email) {
        toast.success(`Email verified (${data.basic_info.email}), no direct mobile on file in Apollo.`, { id: toastId, duration: 5000 })
      } else {
        toast.success('Profile details refreshed from Apollo.', { id: toastId })
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Enrichment failed.'
      toast.error(errorMsg, { id: toastId })
    } finally {
      setEnrichingUrl(null)
    }
  }

  const handleBulkEnrichPhones = async () => {
    setBulkPhoneLoading(true)
    const toastId = toast.loading('Looking up mobile numbers from Apollo for shortlisted candidates...')
    try {
      const payload = {
        session_id: activeSessionId || null,
        target_verdict: 'shortlist'
      }
      const { data } = await axios.post('/api/candidates/bulk-enrich-phone', payload)
      await load()
      toast.success(
        `Completed! Found ${data.phones_found} mobile number(s) across ${data.total_candidates} shortlisted candidate(s).`,
        { id: toastId, duration: 6000 }
      )
      setBulkPhoneModalOpen(false)
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Bulk phone enrichment failed.'
      toast.error(errorMsg, { id: toastId })
    } finally {
      setBulkPhoneLoading(false)
    }
  }

  const availableRoles = Array.from(new Set(candidates.map(c => c.role_name).filter(Boolean)))

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
    .filter(c => roleFilter === 'all' || c.role_name === roleFilter)
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
      {/* Active Session Context Banner */}
      {activeSessionId && (
        <div className="bg-gradient-to-r from-blue-50/90 via-indigo-50/40 to-slate-50 border border-blue-200 rounded-2xl p-4.5 flex items-center justify-between shadow-sm animate-fade-in">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-[#0B57D0] text-white flex items-center justify-center font-extrabold text-base shadow-sm">
              ⚡
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-extrabold uppercase tracking-wider bg-blue-100/80 text-[#0B57D0] px-2.5 py-0.5 rounded-lg border border-blue-200">
                  Search Session View
                </span>
                <h3 className="text-[15px] font-bold text-slate-800 leading-tight">
                  {roleName || candidates[0]?.role_name || 'Active Search Run'}
                </h3>
              </div>
              <p className="text-xs text-slate-500 font-medium mt-1">
                Showing {filtered.length} candidates isolated to this specific search session and sourcing criteria.
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              setActiveSessionId(null);
              onClearSessionFilter?.();
            }}
            className="bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 px-4 py-2 rounded-xl text-xs font-bold transition-all border border-slate-200 shadow-sm flex items-center gap-2 outline-none cursor-pointer active:scale-95"
          >
            <span>✕</span> View All Candidates Database
          </button>
        </div>
      )}

      {/* Controls row */}
      <div className="flex items-center gap-3">
        <input 
          value={search} 
          onChange={e => setSearch(e.target.value)}
          placeholder="Search name, company, title..."
          className="flex-1 bg-[#edf2fa] border border-slate-200/75 rounded-xl px-4.5 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:bg-white text-slate-800 transition-all font-semibold" 
        />
        {availableRoles.length > 1 && (
          <select
            value={roleFilter}
            onChange={e => setRoleFilter(e.target.value)}
            className="border border-slate-200 bg-[#edf2fa] text-slate-800 font-bold rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
          >
            <option value="all">All Roles ({candidates.length})</option>
            {availableRoles.map(r => (
              <option key={r} value={r}>{r} ({candidates.filter(c => c.role_name === r).length})</option>
            ))}
          </select>
        )}
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
          onClick={startBulkOutreachQueue} 
          className="bg-green-600 hover:bg-green-700 text-white px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm outline-none cursor-pointer"
          title="Bulk Outreach Queue for Shortlisted Candidates"
        >
          ✉️ Send to Shortlisted ({shortlistedCandidates.length})
        </button>
        <button 
          onClick={() => {
            if (shortlistedCandidates.length === 0) {
              toast.error('No shortlisted candidates found. Please mark candidates as "Shortlist" first.')
              return
            }
            setBulkPhoneModalOpen(true)
          }}
          className="bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm outline-none cursor-pointer"
          title="Look up mobile numbers for shortlisted candidates via Apollo"
        >
          📞 Fetch Mobile ({shortlistedWithoutPhone.length})
        </button>
        <button 
          onClick={handleExport} 
          className="bg-[#0B57D0] hover:bg-[#0842a0] text-white px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm outline-none cursor-pointer"
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
            { label: 'Recommended Candidates', val: candidates.filter(c => c.recommended_action === 'Reach out now').length, color: 'text-green-700' },
            { label: 'Shortlisted Candidates', val: candidates.filter(c => c.recruiter_verdict === 'shortlist').length, color: 'text-blue-700' },
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
                    {c.location && c.location.trim() && (
                      <p className="text-xs text-slate-400 font-medium mt-0.5">{c.location}</p>
                    )}
                    {c.score_reasoning && c.score_reasoning.trim() && !c.score_reasoning.includes('0 matched skills') && (
                      <p className="text-xs text-slate-500 font-medium mt-2 leading-relaxed bg-[#f8fafc] border border-slate-100 rounded-xl p-3">{c.score_reasoning}</p>
                    )}

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
                    <div className="flex flex-col items-end gap-1.5">
                      {c.email && (
                        <span className="text-[10px] text-green-700 font-bold bg-green-50 px-2.5 py-1 rounded-lg border border-green-100 inline-flex items-center gap-1" title={c.email}>
                          ✉️ {c.email}
                        </span>
                      )}
                      {c.phone ? (
                        <a 
                          href={`tel:${c.phone}`}
                          className="text-[10px] text-emerald-700 font-bold bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 rounded-lg border border-emerald-200 inline-flex items-center gap-1 transition-colors" 
                          title={`Click to call ${c.phone}`}
                        >
                          📞 {c.phone}
                        </a>
                      ) : c.email ? (
                        <button
                          onClick={() => enrichCandidate(c.linkedin_url)}
                          disabled={enrichingUrl === c.linkedin_url}
                          className="text-[10px] bg-slate-50 hover:bg-slate-100 text-slate-500 hover:text-slate-700 px-2.5 py-1 rounded-lg font-bold border border-slate-200 transition-all outline-none flex items-center gap-1 cursor-pointer"
                          title="Apollo verified the work email, but has no direct mobile on file for this candidate. Click to retry lookup."
                        >
                          {enrichingUrl === c.linkedin_url ? '↻ Checking...' : '📞 No mobile on file'}
                        </button>
                      ) : (
                        <button
                          onClick={() => enrichCandidate(c.linkedin_url)}
                          disabled={enrichingUrl === c.linkedin_url}
                          className="text-[10px] bg-blue-50 hover:bg-blue-100 text-[#0B57D0] px-2.5 py-1 rounded-lg font-bold border border-blue-200 transition-all outline-none flex items-center gap-1 cursor-pointer active:scale-95"
                          title="Look up verified contact details and mobile number via Apollo"
                        >
                          {enrichingUrl === c.linkedin_url ? '↻ Revealing...' : '📞 Reveal Mobile'}
                        </button>
                      )}
                    </div>

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
                      <div>
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Email Address</span>
                        <p className="font-bold text-slate-800 mt-1 truncate" title={c.email}>{c.email || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Mobile / Phone</span>
                        <p className="font-bold text-slate-800 mt-1 truncate" title={c.phone}>
                          {c.phone ? (
                            <a href={`tel:${c.phone}`} className="text-emerald-700 hover:underline">
                              {c.phone}
                            </a>
                          ) : (c.email ? 'Unavailable on Apollo' : 'Not revealed')}
                        </p>
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

      {/* Outreach Queue Modal (Rendered in React Portal to prevent CSS containing-block issues) */}
      {queueModalOpen && queueList.length > 0 && typeof document !== 'undefined' && createPortal(
        <div className="fixed inset-0 z-[9999] bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl border border-slate-200 overflow-hidden">
            {/* Header */}
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-green-50 text-green-700 border border-green-200 flex items-center justify-center font-bold text-sm">
                  ✉️
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-slate-900">Bulk Outreach Queue</h3>
                    <span className="text-[10px] font-extrabold uppercase tracking-wide bg-blue-50 text-[#0B57D0] px-2 py-0.5 rounded border border-blue-100">
                      Candidate {queueIndex + 1} of {queueList.length}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 font-semibold mt-0.5">
                    Review and personalize email draft before opening in Gmail.
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setQueueModalOpen(false)}
                className="w-8 h-8 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 flex items-center justify-center text-sm font-bold transition-all outline-none cursor-pointer"
                title="Close"
              >
                ✕
              </button>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
              <div 
                className="bg-[#0B57D0] h-full transition-all duration-300 rounded-full"
                style={{ width: `${((queueIndex + 1) / queueList.length) * 100}%` }}
              />
            </div>

            {/* Candidate Card Summary */}
            <div className="bg-[#f8fafc] border border-slate-200/80 rounded-xl p-3.5 space-y-2">
              <div className="flex justify-between items-start">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-bold text-slate-900 text-sm">{queueList[queueIndex]?.full_name}</p>
                    {queueList[queueIndex]?.linkedin_url && (
                      <a 
                        href={queueList[queueIndex].linkedin_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-[10px] text-blue-600 hover:underline font-bold inline-flex items-center gap-0.5"
                      >
                        LinkedIn 🔗
                      </a>
                    )}
                  </div>
                  <p className="text-xs text-slate-600 font-medium mt-0.5">
                    {queueList[queueIndex]?.current_title} · {queueList[queueIndex]?.current_company}
                  </p>
                  {queueList[queueIndex]?.location && (
                    <p className="text-[11px] text-slate-400 font-medium">{queueList[queueIndex].location}</p>
                  )}
                </div>
                <div className="shrink-0">
                  <span className="text-xs font-bold text-green-700 bg-green-50 px-2.5 py-1 rounded-lg border border-green-200 inline-flex items-center gap-1.5">
                    <span>✉️</span> {queueList[queueIndex]?.email}
                  </span>
                </div>
              </div>
            </div>

            {/* Email Subject Input */}
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                Email Subject
              </label>
              <input 
                value={queueSubject}
                onChange={e => setQueueSubject(e.target.value)}
                className="w-full bg-[#edf2fa] border border-slate-200/80 rounded-xl px-3.5 py-2 text-xs font-semibold text-slate-800 focus:outline-none focus:bg-white focus:border-blue-500 transition-all"
                placeholder="Subject..."
              />
            </div>

            {/* Email Body Content */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  Email Body (Editable)
                </label>
                <button
                  type="button"
                  onClick={copyQueueEmailContent}
                  className="text-[10px] text-[#0B57D0] hover:underline font-bold transition-all outline-none cursor-pointer"
                >
                  📋 Copy Content
                </button>
              </div>
              <textarea 
                value={queueBody}
                onChange={e => setQueueBody(e.target.value)}
                rows={6}
                className="w-full bg-[#f8fafc] border border-slate-200/80 rounded-xl p-3.5 text-xs text-slate-750 font-normal leading-relaxed focus:outline-none focus:bg-white focus:border-blue-500 resize-none transition-all"
              />
            </div>

            {/* Modal Controls */}
            <div className="flex justify-between items-center pt-2 border-t border-slate-100">
              <div className="flex items-center gap-2">
                <button 
                  type="button"
                  onClick={() => setQueueModalOpen(false)}
                  className="px-3.5 py-2 text-xs font-bold text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-all outline-none cursor-pointer"
                >
                  Cancel Queue
                </button>
                <button 
                  type="button"
                  onClick={openCurrentInOutreachPage}
                  className="px-3 py-2 text-xs font-bold text-[#0B57D0] hover:bg-blue-50 rounded-xl transition-all outline-none cursor-pointer border border-blue-200"
                  title="Open this candidate in full Outreach editor"
                >
                  Open in Outreach Tab ↗
                </button>
                {queueIndex + 1 < queueList.length && (
                  <button 
                    type="button"
                    onClick={skipQueueCandidate}
                    className="px-3.5 py-2 text-xs font-bold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-xl transition-all outline-none cursor-pointer"
                  >
                    Skip to Next ⏭️
                  </button>
                )}
              </div>

              <button 
                type="button"
                onClick={processQueueNext}
                className="bg-[#0B57D0] hover:bg-[#0842a0] text-white px-5 py-2.5 rounded-xl text-xs font-bold transition-all shadow-md hover:shadow-lg flex items-center gap-2 outline-none cursor-pointer active:scale-95"
              >
                <span>✉️</span>
                <span>
                  {queueIndex + 1 < queueList.length 
                    ? `Open in Gmail & Next (${queueIndex + 1}/${queueList.length}) →` 
                    : `Open in Gmail & Finish (${queueIndex + 1}/${queueList.length}) ✓`}
                </span>
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Bulk Phone Enrichment Modal */}
      {bulkPhoneModalOpen && createPortal(
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl border border-slate-200">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">📞</span>
                <h3 className="text-base font-bold text-slate-900">Fetch Mobile Numbers</h3>
              </div>
              <button 
                type="button"
                disabled={bulkPhoneLoading}
                onClick={() => setBulkPhoneModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 text-sm font-bold outline-none cursor-pointer p-1"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs text-slate-650 leading-relaxed">
              <p>
                You are about to look up mobile phone numbers from Apollo for{' '}
                <strong className="text-slate-900">{shortlistedWithoutPhone.length} shortlisted candidate(s)</strong> who currently don't have a phone on file.
              </p>
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-amber-800 flex items-start gap-2.5">
                <span className="text-base shrink-0">⚠️</span>
                <div>
                  <p className="font-bold text-[11px]">Apollo Credit Information</p>
                  <p className="text-[11px] mt-0.5 leading-relaxed text-amber-750">
                    Apollo consumes Phone / Mobile Credits for each candidate contact revealed. Uncovered numbers will be saved in PostgreSQL and displayed on the candidate cards.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex justify-end items-center gap-2 pt-3 border-t border-slate-100">
              <button 
                type="button"
                disabled={bulkPhoneLoading}
                onClick={() => setBulkPhoneModalOpen(false)}
                className="px-4 py-2 text-xs font-bold text-slate-500 hover:text-slate-800 rounded-xl transition-all outline-none cursor-pointer"
              >
                Cancel
              </button>
              <button 
                type="button"
                disabled={bulkPhoneLoading || shortlistedWithoutPhone.length === 0}
                onClick={handleBulkEnrichPhones}
                className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl text-xs font-bold transition-all shadow-md flex items-center gap-2 outline-none cursor-pointer active:scale-95"
              >
                {bulkPhoneLoading ? (
                  <>
                    <span className="animate-spin text-sm">↻</span>
                    <span>Fetching from Apollo...</span>
                  </>
                ) : (
                  <>
                    <span>📞</span>
                    <span>Confirm & Fetch Numbers ({shortlistedWithoutPhone.length})</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  )
}
