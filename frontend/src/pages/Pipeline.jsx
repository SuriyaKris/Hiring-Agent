import React, { useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

const SAMPLE_JD = `We are looking for a Senior Python Developer / Backend Engineer to join our core engineering team in Bangalore.

Role: Senior Python Developer
Location: Bangalore, Karnataka, India (Hybrid)

Responsibilities:
- Design, develop, and maintain high-performance microservices using Python, FastAPI, and Django
- Architect robust REST and GraphQL APIs for enterprise client applications
- Optimize relational database queries in PostgreSQL and manage caching with Redis
- Deploy, monitor, and scale backend services on AWS (ECS, Lambda, S3, RDS)
- Collaborate with frontend engineers, product managers, and QA teams in an agile environment
- Write comprehensive unit, integration, and end-to-end tests

Requirements:
- 4-8 years of professional software engineering experience in Python
- Deep expertise with modern Python frameworks (FastAPI, Django, Flask, or AsyncIO)
- Strong experience with relational databases (PostgreSQL, MySQL) and database schema design
- Proficiency in containerization with Docker and CI/CD automation pipelines
- Hands-on experience with cloud infrastructure (AWS or GCP)
- Solid understanding of data structures, algorithms, and microservice architectures

Nice to Have:
- Experience with Apache Kafka, Celery, or RabbitMQ event streaming
- Familiarity with Kubernetes and Helm
- Experience with GraphQL and Elasticsearch

Location: Bangalore, India`

export default function Pipeline({ onCandidatesReady }) {
  const [step, setStep] = useState('input') // 'input' | 'review'
  const [jdText, setJdText] = useState('')
  const [roleName, setRoleName] = useState('')
  const [maxCandidates, setMaxCandidates] = useState(20)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [uploading, setUploading] = useState(false)

  // Sourcing spec states
  const [spec, setSpec] = useState(null)
  const [newTitle, setNewTitle] = useState('')
  const [newSkill, setNewSkill] = useState('')
  const [newGeo, setNewGeo] = useState('')
  const [newTech, setNewTech] = useState('')
  const [newSeniority, setNewSeniority] = useState('')

  const loadExampleJd = () => {
    setJdText(SAMPLE_JD)
    setRoleName('Senior Python Developer')
    toast.success('Loaded example Python Developer JD')
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    
    try {
      const { data } = await axios.post('/api/pipeline/upload-jd', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      if (data.jd_text) {
        setJdText(data.jd_text)
        toast.success(`Successfully loaded ${file.name}! Click 'Extract Sourcing Criteria' to analyze.`)
      } else {
        toast.error('No text could be extracted from this file.')
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'File parsing failed.')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const extractCriteria = async () => {
    if (!jdText.trim()) { toast.error('Paste a job description first.'); return }
    setLoading(true)
    setResult(null)
    try {
      const { data } = await axios.post('/api/pipeline/parse', {
        text: jdText,
        role_name: roleName
      })
      if (!data.currently_using_technology_uids) {
        data.currently_using_technology_uids = []
      }
      // Ensure primary_titles and required_skills are present
      if (!data.primary_titles) data.primary_titles = []
      if (!data.required_skills) data.required_skills = []
      if (!data.geo_keywords) data.geo_keywords = []
      if (!data.seniority_levels) data.seniority_levels = []

      // Auto-populate role name from extracted title only if roleName is empty
      if (!roleName.trim()) {
        if (data.role_name || (data.primary_titles && data.primary_titles.length > 0)) {
          setRoleName(data.role_name || data.primary_titles[0])
        }
      }

      setSpec(data)
      setStep('review')
      toast.success('Successfully extracted search criteria!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Extraction failed.')
    } finally {
      setLoading(false)
    }
  }

  const addPill = (field, value, setter) => {
    const trimmed = value.trim()
    if (!trimmed) return
    // Prevent duplicate entries
    if (spec[field].map(s => s.toLowerCase()).includes(trimmed.toLowerCase())) {
      toast.error('Value already exists!')
      return
    }
    setSpec(prev => ({
      ...prev,
      [field]: [...prev[field], trimmed]
    }))
    setter('')
  }

  const removePill = (field, index) => {
    setSpec(prev => ({
      ...prev,
      [field]: prev[field].filter((_, idx) => idx !== index)
    }))
  }

  const runPipeline = async () => {
    setLoading(true)
    setResult(null)
    try {
      const activeRole = roleName || (spec?.primary_titles?.[0] || 'Target Role')
      const payloadSpec = spec ? { ...spec, role_name: activeRole } : null
      const { data } = await axios.post('/api/pipeline/run', {
        jd_text: jdText,
        role_name: activeRole,
        recruiter_name: 'Meghana',
        company_name: '4CECloud Labs',
        max_candidates: maxCandidates,
        data_source: 'apollo',
        spec: payloadSpec,
      }, {
        timeout: 300000 // 5-minute timeout for LangGraph candidate search & scoring
      })
      setResult(data)
      setStep('input')
      toast.success(`Pipeline complete! ${data.total_sourced} candidates scored.`)
      if (onCandidatesReady) {
        onCandidatesReady({
          sessionId: data.run_id,
          roleName: data.role_name || activeRole,
          candidates: data.candidates || []
        })
      }
    } catch (err) {
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        toast.error('Search request timed out. Please try searching with fewer candidates or check backend.')
      } else {
        const detail = err.response?.data?.detail
        if (Array.isArray(detail)) {
          const msg = detail.map(d => d.msg || (d.loc ? `${d.loc.slice(-1)}: ${d.msg}` : '')).filter(Boolean).join(', ')
          toast.error(msg || 'Invalid criteria parameters.')
        } else if (typeof detail === 'string') {
          toast.error(detail)
        } else {
          toast.error(err.response?.data?.message || err.message || 'Pipeline failed.')
        }
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in-up select-text">
      {/* Step Indicators */}
      <div className="flex items-center gap-2 px-1">
        <span className={`text-[11px] font-bold px-3 py-1 rounded-lg border transition-all ${
          step === 'input' 
            ? 'bg-blue-50 text-blue-700 border-blue-200' 
            : 'bg-slate-100 text-slate-400 border-slate-200/50'
        }`}>1. Input Job Description</span>
        <span className="text-slate-350 text-xs font-semibold">→</span>
        <span className={`text-[11px] font-bold px-3 py-1 rounded-lg border transition-all ${
          step === 'review' 
            ? 'bg-blue-50 text-blue-700 border-blue-200' 
            : 'bg-slate-100 text-slate-400 border-slate-200/50'
        }`}>2. Review Sourcing Criteria</span>
      </div>

      {step === 'input' ? (
        /* Config row */
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-[15px] font-bold text-slate-800">Fully Automated AI Pipeline</h2>
              <p className="text-xs text-slate-400 font-medium mt-1">Paste or upload any Job Description to automatically extract role titles, skills, and target locations.</p>
            </div>
            <button
              onClick={loadExampleJd}
              className="text-xs text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 font-bold px-3 py-1.5 rounded-lg border border-blue-200 transition-all outline-none"
            >
              Load Example JD
            </button>
          </div>
          
          <div className="grid grid-cols-2 gap-5">
            <div>
              <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Role Name (Optional — Auto-detected from JD)</label>
              <input 
                value={roleName} 
                onChange={e => setRoleName(e.target.value)}
                placeholder="e.g. Senior Python Developer (or leave blank to auto-detect)"
                className="w-full bg-[#edf2fa] border border-slate-200/70 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:bg-white text-slate-800 transition-all font-semibold" 
              />
            </div>
            <div>
              <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Max Candidates to Source</label>
              <select 
                value={maxCandidates} 
                onChange={e => setMaxCandidates(Number(e.target.value))}
                className="w-full bg-[#edf2fa] border border-slate-200/70 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 focus:bg-white text-slate-800 transition-all font-semibold cursor-pointer"
              >
                <option value={10}>10 candidates</option>
                <option value={20}>20 candidates</option>
                <option value={30}>30 candidates</option>
                <option value={50}>50 candidates</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Job Description Text</label>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Upload File (PDF/DOCX):</span>
                <input 
                  type="file" 
                  accept=".pdf,.docx,.doc,.txt" 
                  onChange={handleFileUpload} 
                  disabled={uploading}
                  className="text-xs text-slate-500 file:mr-2 file:py-1 file:px-2.5 file:rounded-lg file:border-0 file:text-[10px] file:font-bold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer disabled:opacity-50 outline-none"
                />
              </div>
            </div>
            <textarea 
              value={jdText} 
              onChange={e => setJdText(e.target.value)}
              placeholder="Paste the full job description here (including role title, responsibilities, technical requirements, and location)..."
              className="w-full bg-[#edf2fa] border border-slate-200/70 rounded-xl px-4 py-3 text-sm h-52 resize-none focus:outline-none focus:border-blue-500 focus:bg-white text-slate-700 leading-relaxed transition-all font-medium" 
            />
          </div>

          <div className="flex items-center justify-end pt-2 border-t border-slate-100">
            <button 
              onClick={extractCriteria} 
              disabled={loading}
              className="bg-[#0B57D0] hover:bg-[#0842a0] text-white rounded-xl px-6 py-3 text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center gap-2 outline-none"
            >
              {loading ? (
                <><span className="animate-spin text-sm">⟳</span> Analyzing JD...</>
              ) : (
                <>🔍 Extract Sourcing Criteria →</>
              )}
            </button>
          </div>
        </div>
      ) : (
        /* Sourcing Review Panel */
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-150 pb-4">
            <div>
              <h2 className="text-[15px] font-bold text-slate-800">Review Sourcing Criteria</h2>
              <p className="text-xs text-slate-400 font-medium mt-1">Review, add, or remove target keywords, job titles, and location filters extracted from the JD.</p>
            </div>
            <button 
              onClick={() => setStep('input')} 
              className="text-xs text-slate-500 hover:text-slate-850 font-bold px-3 py-1.5 rounded-lg border border-slate-200 bg-[#f8fafc] hover:bg-slate-100 shadow-sm transition-all outline-none"
            >
              ← Edit Raw JD
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Target Job Titles */}
            <div className="border border-slate-200/80 rounded-2xl p-5 bg-[#f8fafc]/50">
              <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-3">Target Job Titles</label>
              <div className="flex flex-wrap gap-1.5 mb-4 min-h-[40px] items-center">
                {spec.primary_titles.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No job titles added.</p>
                ) : (
                  spec.primary_titles.map((t, idx) => (
                    <span key={idx} className="inline-flex items-center gap-1.5 text-xs font-semibold bg-blue-50 text-blue-700 px-2.5 py-0.5 rounded-full border border-blue-100">
                      {t}
                      <button onClick={() => removePill('primary_titles', idx)} className="hover:text-red-500 font-bold text-sm leading-none">×</button>
                    </span>
                  ))
                )}
              </div>
              <div className="flex gap-2">
                <input 
                  value={newTitle} 
                  onChange={e => setNewTitle(e.target.value)} 
                  placeholder="Add custom title..." 
                  onKeyDown={e => e.key === 'Enter' && addPill('primary_titles', newTitle, setNewTitle)}
                  className="bg-[#edf2fa] border border-slate-200/60 rounded-lg px-3 py-1.5 text-xs w-full focus:outline-none focus:bg-white text-slate-700 font-medium transition-all" 
                />
                <button onClick={() => addPill('primary_titles', newTitle, setNewTitle)} className="bg-blue-50 hover:bg-blue-100 text-blue-700 px-3 rounded-lg text-xs font-bold outline-none">+</button>
              </div>
            </div>

            {/* Sourcing Keywords & Skills */}
            <div className="border border-slate-200/80 rounded-2xl p-5 bg-[#f8fafc]/50">
              <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-3">Search Keywords & Skills</label>
              <div className="flex flex-wrap gap-1.5 mb-4 min-h-[40px] items-center">
                {spec.required_skills.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No keywords added.</p>
                ) : (
                  spec.required_skills.map((s, idx) => (
                    <span key={idx} className="inline-flex items-center gap-1.5 text-xs font-semibold bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded-full border border-emerald-100">
                      {s}
                      <button onClick={() => removePill('required_skills', idx)} className="hover:text-red-500 font-bold text-sm leading-none">×</button>
                    </span>
                  ))
                )}
              </div>
              <div className="flex gap-2">
                <input 
                  value={newSkill} 
                  onChange={e => setNewSkill(e.target.value)} 
                  placeholder="Add custom keyword..." 
                  onKeyDown={e => e.key === 'Enter' && addPill('required_skills', newSkill, setNewSkill)}
                  className="bg-[#edf2fa] border border-slate-200/60 rounded-lg px-3 py-1.5 text-xs w-full focus:outline-none focus:bg-white text-slate-700 font-medium transition-all" 
                />
                <button onClick={() => addPill('required_skills', newSkill, setNewSkill)} className="bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-3 rounded-lg text-xs font-bold outline-none">+</button>
              </div>
            </div>

            {/* Locations / Geographies */}
            <div className="border border-slate-200/80 rounded-2xl p-5 bg-[#f8fafc]/50">
              <div className="flex items-center justify-between mb-3">
                <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase">Target Locations & Cities</label>
                {spec.target_territory && (
                  <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">Territory: {spec.target_territory}</span>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5 mb-4 min-h-[40px] items-center">
                {spec.geo_keywords.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No location restrictions (Global search).</p>
                ) : (
                  spec.geo_keywords.map((g, idx) => (
                    <span key={idx} className="inline-flex items-center gap-1.5 text-xs font-semibold bg-slate-100 text-slate-750 px-2.5 py-0.5 rounded-full border border-slate-200">
                      {g}
                      <button onClick={() => removePill('geo_keywords', idx)} className="hover:text-red-500 font-bold text-sm leading-none">×</button>
                    </span>
                  ))
                )}
              </div>
              <div className="flex gap-2">
                <input 
                  value={newGeo} 
                  onChange={e => setNewGeo(e.target.value)} 
                  placeholder="Add location (e.g. Bangalore, London, India)..." 
                  onKeyDown={e => e.key === 'Enter' && addPill('geo_keywords', newGeo, setNewGeo)}
                  className="bg-[#edf2fa] border border-slate-200/60 rounded-lg px-3 py-1.5 text-xs w-full focus:outline-none focus:bg-white text-slate-700 font-medium transition-all" 
                />
                <button onClick={() => addPill('geo_keywords', newGeo, setNewGeo)} className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 rounded-lg text-xs font-bold outline-none">+</button>
              </div>
            </div>

            {/* Technology Stack Filter */}
            <div className="border border-slate-200/80 rounded-2xl p-5 bg-[#f8fafc]/50">
              <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-3">Employer Technology Filter</label>
              <div className="flex flex-wrap gap-1.5 mb-4 min-h-[40px] items-center">
                {spec.currently_using_technology_uids.length === 0 ? (
                  <p className="text-xs text-slate-400 italic font-medium leading-relaxed">Sourcing candidates regardless of employer tech stack.</p>
                ) : (
                  spec.currently_using_technology_uids.map((tech, idx) => (
                    <span key={idx} className="inline-flex items-center gap-1.5 text-xs font-semibold bg-amber-50 text-amber-800 px-2.5 py-0.5 rounded-full border border-amber-200">
                      {tech}
                      <button onClick={() => removePill('currently_using_technology_uids', idx)} className="hover:text-red-500 font-bold text-sm leading-none">×</button>
                    </span>
                  ))
                )}
              </div>
              <div className="flex gap-2">
                <input 
                  value={newTech} 
                  onChange={e => setNewTech(e.target.value)} 
                  placeholder="Add tech filter (e.g. salesforce, hubspot, aws)..." 
                  onKeyDown={e => e.key === 'Enter' && addPill('currently_using_technology_uids', newTech, setNewTech)}
                  className="bg-[#edf2fa] border border-slate-200/60 rounded-lg px-3 py-1.5 text-xs w-full focus:outline-none focus:bg-white text-slate-700 font-medium transition-all" 
                />
                <button onClick={() => addPill('currently_using_technology_uids', newTech, setNewTech)} className="bg-amber-50 hover:bg-amber-100 text-amber-700 px-3 rounded-lg text-xs font-bold outline-none">+</button>
              </div>
            </div>

            {/* Seniority Levels */}
            <div className="border border-slate-200/80 rounded-2xl p-5 bg-[#f8fafc]/50">
              <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-3">Seniority Levels</label>
              <div className="flex flex-wrap gap-1.5 mb-4 min-h-[40px] items-center">
                {spec.seniority_levels.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No seniority levels added.</p>
                ) : (
                  spec.seniority_levels.map((s, idx) => (
                    <span key={idx} className="inline-flex items-center gap-1.5 text-xs font-semibold bg-purple-50 text-purple-700 px-2.5 py-0.5 rounded-full border border-purple-100">
                      {s}
                      <button onClick={() => removePill('seniority_levels', idx)} className="hover:text-red-500 font-bold text-sm leading-none">×</button>
                    </span>
                  ))
                )}
              </div>
              <div className="flex gap-2">
                <input 
                  value={newSeniority} 
                  onChange={e => setNewSeniority(e.target.value)} 
                  placeholder="Add custom seniority (e.g. senior, mid)..." 
                  onKeyDown={e => e.key === 'Enter' && addPill('seniority_levels', newSeniority, setNewSeniority)}
                  className="bg-[#edf2fa] border border-slate-200/60 rounded-lg px-3 py-1.5 text-xs w-full focus:outline-none focus:bg-white text-slate-700 font-medium transition-all" 
                />
                <button onClick={() => addPill('seniority_levels', newSeniority, setNewSeniority)} className="bg-purple-50 hover:bg-purple-100 text-purple-700 px-3 rounded-lg text-xs font-bold outline-none">+</button>
              </div>
            </div>
          </div>

          {/* Sourcing Launch Action */}
          <div className="flex items-center justify-between border-t border-slate-150 pt-5">
            <div>
              <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase">Max Sourced Candidates</label>
              <select 
                value={maxCandidates} 
                onChange={e => setMaxCandidates(Number(e.target.value))}
                className="border border-slate-200 bg-[#edf2fa] text-slate-750 font-bold rounded-lg px-3 py-1.5 text-xs mt-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
              >
                <option value={10}>10 candidates</option>
                <option value={20}>20 candidates</option>
                <option value={30}>30 candidates</option>
                <option value={50}>50 candidates</option>
              </select>
            </div>
            
            <button 
              onClick={runPipeline} 
              disabled={loading}
              className="bg-[#0B57D0] hover:bg-[#0842a0] text-white rounded-xl px-6 py-3 text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center gap-2 outline-none"
            >
              {loading ? (
                <><span className="animate-spin text-sm">⟳</span> Sourcing & Scoring...</>
              ) : (
                <>⚡ Launch Search with Criteria →</>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Loading steps */}
      {loading && (
        <div className="bg-blue-50/50 border border-blue-200/60 rounded-2xl p-6 space-y-4">
          <p className="text-xs font-bold text-blue-800 uppercase tracking-wider">Pipeline Execution in Progress</p>
          <div className="space-y-2">
            {[
              'Parsing JD and building search specifications...',
              'Querying Apollo People search APIs for targeted locations...',
              'Resolving candidate identities and validating contact data...',
              'Evaluating AI fitment scorecards against requirements...',
              'Ranking and formatting candidate recommendations...'
            ].map((step, i) => (
              <div key={i} className="flex items-center gap-3 text-xs text-blue-700/80 font-bold">
                <span className="animate-pulse text-blue-600 text-[10px]">◉</span> {step}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Summary alert banner */}
          <div className="bg-emerald-50/40 border border-emerald-200/60 rounded-2xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-emerald-800 uppercase tracking-wider">Pipeline complete — run {result.run_id}</p>
                <p className="text-xs text-slate-500 font-medium mt-1">
                  Sourced {result.total_sourced} candidates from <strong>{result.data_source}</strong>.
                </p>
              </div>
              <button 
                onClick={onCandidatesReady}
                className="bg-[#0B57D0] hover:bg-[#0842a0] text-white rounded-xl px-4 py-2.5 text-xs font-bold shadow-sm transition-colors outline-none"
              >
                View all candidates →
              </button>
            </div>
          </div>

          {/* Spec summary */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3 shadow-sm">
            <p className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Parsed Sourcing Specification</p>
            <p className="text-xs text-slate-650 font-medium leading-relaxed">{result.spec?.summary}</p>
            <div className="flex flex-wrap gap-1.5 pt-2">
              {result.spec?.primary_titles?.map(t => (
                <span key={t} className="text-[10px] font-bold bg-blue-50 text-blue-700 px-2.5 py-0.5 rounded-lg border border-blue-100">{t}</span>
              ))}
              {result.spec?.geo_keywords?.slice(0,4).map(g => (
                <span key={g} className="text-[10px] font-bold bg-slate-100 text-slate-650 px-2.5 py-0.5 rounded-lg border border-slate-200">{g}</span>
              ))}
              {result.spec?.currently_using_technology_uids?.map(t => (
                <span key={t} className="text-[10px] font-bold bg-amber-50 text-amber-800 px-2.5 py-0.5 rounded-lg border border-amber-200">{t}</span>
              ))}
            </div>
          </div>

          {/* Top 3 preview */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <p className="text-[9px] font-bold text-slate-400 tracking-wider uppercase">Top 3 Candidates Recommendation Preview</p>
            {result.candidates && result.candidates.length > 0 ? (
              <div className="divide-y divide-slate-100">
                {result.candidates?.slice(0,3).map((c, i) => (
                  <div key={i} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                    <div>
                      {(c.profile.basic_info?.linkedin_url || c.profile.linkedin_url) ? (
                        <a href={c.profile.basic_info?.linkedin_url || c.profile.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1">
                          {c.profile.basic_info?.full_name || c.profile.full_name}
                          <span className="text-[10px] opacity-60">🔗</span>
                        </a>
                      ) : (
                        <p className="text-xs font-bold text-slate-800">{c.profile.basic_info?.full_name || c.profile.full_name}</p>
                      )}
                      <p className="text-[11px] text-slate-500 font-medium mt-0.5">
                        {(c.profile.experience?.[0]?.title || c.profile.basic_info?.headline || c.profile.current_title || "")} · {(c.profile.experience?.[0]?.company_name || c.profile.company?.name || c.profile.current_company || "")}
                      </p>
                      {c.profile.basic_info?.location && c.profile.basic_info.location.trim() && (
                        <p className="text-[10px] text-slate-400 font-medium">📍 {c.profile.basic_info.location}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <span className={`text-xs font-extrabold ${c.fitment_score >= 75 ? 'text-green-600' : c.fitment_score >= 50 ? 'text-amber-600' : 'text-red-500'}`}>
                        {Math.round(c.fitment_score)}/100
                      </span>
                      <p className="text-[10px] text-slate-400 font-bold mt-0.5 uppercase tracking-wider">{c.recommended_action}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic py-2">No candidate profiles were returned for this search.</p>
            )}
            <button 
              onClick={() => onCandidatesReady?.({
                sessionId: result.run_id,
                roleName: result.role_name || spec?.primary_titles?.[0] || roleName || 'Search Run',
                candidates: result.candidates || [],
              })} 
              className="block text-xs text-[#0B57D0] hover:text-[#0842a0] font-bold outline-none cursor-pointer transition-colors"
            >
              See all {result.total_sourced} candidates →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
