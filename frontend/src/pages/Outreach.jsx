import React, { useState, useEffect } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

export default function Outreach({ candidate }) {
  const [draft, setDraft] = useState(null)
  const [loading, setLoading] = useState(false)
  const [roleName, setRoleName] = useState('Inside Sales – US Region')
  const [recruiterName, setRecruiterName] = useState('Meghana')
  const [companyName, setCompanyName] = useState('4CECloud Labs')
  const [history, setHistory] = useState([])
  const [showHistory, setShowHistory] = useState(false)

  // Manual input states for general template (pre-populated if candidate exists)
  const [manualName, setManualName] = useState('')
  const [manualEmail, setManualEmail] = useState('')

  const profile = candidate?.profile || candidate

  // Update states whenever candidate changes
  useEffect(() => {
    if (candidate) {
      const name = profile?.basic_info?.full_name || profile?.full_name || ''
      const email = profile?.basic_info?.personal_email || profile?.personal_email || profile?.basic_info?.email || profile?.email || ''
      setManualName(name)
      setManualEmail(email)
    } else {
      setManualName('')
      setManualEmail('')
      setDraft(null)
    }
    loadHistory()
  }, [candidate])

  const loadHistory = async () => {
    try {
      const { data } = await axios.get('/api/outreach/history')
      setHistory(data)
    } catch {}
  }

  // General template interpolation logic
  const generalSubject = `Exciting Career Opportunity: ${roleName} role at ${companyName}`
  const generalEmailBody = `Hi ${manualName || 'there'},\n\nI hope this email finds you well.\n\nI’m ${recruiterName}, a recruiter at ${companyName}. I came across your profile and was very impressed by your background in driving revenue and scaling operations within the technology sector.\n\nWe are currently expanding our team and looking for a driven professional to fill our ${roleName} role. Your track record suggests you could be a fantastic fit for our aggressive growth strategy over the next 12 months.\n\nWould you be open to a brief introductory call next week to discuss this opportunity further?\n\nBest regards,\n\n${recruiterName}\n${companyName}`

  const handleMarkSent = async () => {
    const name = manualName || 'Manual Candidate'
    const linkedinUrl = profile?.basic_info?.linkedin_url || profile?.linkedin_url || ''
    
    try {
      await axios.post('/api/outreach/save', {
        candidate_linkedin_url: linkedinUrl,
        candidate_name: name,
        role_name: roleName,
        channel: 'email',
        message_sent: generalEmailBody,
      })
      toast.success(`Recorded outreach as sent to ${name}`)
      loadHistory()
    } catch { 
      toast.error('Could not save.') 
    }
  }

  const handleCopyLink = () => {
    const fullText = `Subject: ${generalSubject}\n\n${generalEmailBody}`
    navigator.clipboard.writeText(fullText)
    toast.success('Email content copied to clipboard!')
  }

  const handleOpenInGmail = async () => {
    if (!manualEmail) {
      toast.error('Please specify a candidate email address first.')
      return
    }
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(manualEmail)}&su=${encodeURIComponent(generalSubject)}&body=${encodeURIComponent(generalEmailBody)}`
    window.open(gmailUrl, '_blank')
    await handleMarkSent()
  }

  return (
    <div className="space-y-6 animate-fade-in-up select-text">
      {/* Title Header */}
      <div className="flex justify-between items-center px-1">
        <div>
          <h2 className="text-xl font-bold text-slate-900 leading-tight">Candidate Outreach</h2>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-xs font-bold text-slate-700 leading-tight">Meghana</p>
            <p className="text-[10px] text-slate-400 font-semibold leading-tight mt-0.5">4CECloud Labs</p>
          </div>
          <div className="w-9 h-9 rounded-full bg-[#0B57D0] text-white flex items-center justify-center font-bold text-sm shadow-sm">
            M
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column (Job Context & Manual Override) */}
        <div className="space-y-6">
          {/* Job Context card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-800 flex items-center gap-2">
              <span className="text-[#0B57D0]">💼</span> Job Context
            </h3>
            
            <div className="space-y-3">
              <div>
                <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Role Name</label>
                <input 
                  value={roleName} 
                  onChange={e => setRoleName(e.target.value)}
                  className="w-full bg-[#edf2fa] border border-slate-200/60 rounded-xl px-3 py-2 text-xs font-bold text-slate-750 focus:outline-none focus:bg-white transition-all" 
                />
              </div>
              <div>
                <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Company Name</label>
                <input 
                  value={companyName} 
                  onChange={e => setCompanyName(e.target.value)}
                  className="w-full bg-[#edf2fa] border border-slate-200/60 rounded-xl px-3 py-2 text-xs font-bold text-slate-750 focus:outline-none focus:bg-white transition-all" 
                />
              </div>
              <div>
                <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Recruiter Name</label>
                <input 
                  value={recruiterName} 
                  onChange={e => setRecruiterName(e.target.value)}
                  className="w-full bg-[#edf2fa] border border-slate-200/60 rounded-xl px-3 py-2 text-xs font-bold text-slate-750 focus:outline-none focus:bg-white transition-all" 
                />
              </div>
            </div>
          </div>

          {/* Manual Override card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-800 flex items-center gap-2">
              <span className="text-[#0B57D0]">👤</span> Manual Override
            </h3>
            <p className="text-[10px] text-slate-450 font-semibold leading-relaxed">Test template rendering with specific candidate details.</p>

            <div className="space-y-3 mt-1">
              <div>
                <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Candidate Name</label>
                <input 
                  value={manualName} 
                  onChange={e => setManualName(e.target.value)}
                  placeholder="e.g. Addie Lyon"
                  className="w-full bg-[#edf2fa] border border-slate-200/60 rounded-xl px-3 py-2 text-xs font-bold text-slate-750 focus:outline-none focus:bg-white transition-all" 
                />
              </div>
              <div>
                <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Candidate Email</label>
                <input 
                  value={manualEmail} 
                  onChange={e => setManualEmail(e.target.value)}
                  placeholder="e.g. candidate@domain.com"
                  className="w-full bg-[#edf2fa] border border-slate-200/60 rounded-xl px-3 py-2 text-xs font-bold text-slate-750 focus:outline-none focus:bg-white transition-all" 
                />
              </div>
            </div>
          </div>

        </div>

        {/* Right column (Email Editor Card) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between min-h-[500px]">
            <div className="space-y-5">
              {/* Header bar controls */}
              <div className="flex justify-between items-center border-b border-slate-100 pb-4">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-850 font-bold flex items-center gap-1.5">
                    <span className="text-slate-400">✉️</span> General Email Template
                  </span>
                  <span className="text-[9px] font-extrabold text-[#0B57D0] bg-blue-50 px-2 py-0.5 rounded-lg border border-blue-100 uppercase tracking-wider">
                    Default
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <button 
                    onClick={() => setShowHistory(!showHistory)} 
                    className="text-[11px] text-slate-400 hover:text-slate-700 font-bold transition-all outline-none"
                  >
                    Show sent history ({history.length})
                  </button>
                  <button 
                    onClick={handleCopyLink} 
                    className="text-[11px] text-[#0B57D0] hover:underline font-bold transition-all outline-none flex items-center gap-1"
                  >
                    🔗 Copy Link
                  </button>
                </div>
              </div>

              {/* Subject Input */}
              <div>
                <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Subject</label>
                <input 
                  value={generalSubject} 
                  readOnly
                  className="w-full bg-[#edf2fa] border border-slate-200/60 rounded-xl px-4 py-2.5 text-xs font-semibold text-slate-750 focus:outline-none" 
                />
              </div>

              {/* Editor Block */}
              <div>
                <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Body Content</label>
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  {/* Fake rich-text formatting toolbar */}
                  <div className="bg-[#f8fafc] border-b border-slate-150 px-4 py-2 flex items-center justify-between text-slate-500 text-xs">
                    <div className="flex items-center gap-4.5 font-bold">
                      <button className="hover:text-slate-800 transition-all outline-none">B</button>
                      <button className="hover:text-slate-800 transition-all outline-none italic">I</button>
                      <button className="hover:text-slate-800 transition-all outline-none font-mono">≡</button>
                    </div>
                    <button className="hover:text-slate-800 font-extrabold text-[10px] text-[#0B57D0] transition-all outline-none">
                      {`{ }`} INSERT VARIABLE
                    </button>
                  </div>
                  {/* Rich text area */}
                  <textarea 
                    value={generalEmailBody} 
                    readOnly
                    className="w-full bg-white px-5 py-4 text-xs text-slate-700 font-medium leading-relaxed h-80 focus:outline-none resize-none" 
                  />
                </div>
              </div>
            </div>

            {/* Bottom Actions */}
            <div className="flex justify-end items-center gap-3 pt-5 border-t border-slate-150 mt-6">
              <button 
                onClick={() => toast.success('Draft saved successfully!')} 
                className="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl px-5 py-2.5 text-xs font-bold shadow-sm transition-all outline-none"
              >
                Save Draft
              </button>
              <button 
                onClick={handleMarkSent} 
                className="bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl px-5 py-2.5 text-xs font-bold shadow-sm transition-all flex items-center gap-1.5 outline-none border border-slate-200"
              >
                ✓ Mark Sent
              </button>
              <button 
                onClick={handleOpenInGmail} 
                className="bg-[#0B57D0] hover:bg-[#0842a0] text-white rounded-xl px-5 py-2.5 text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center gap-1.5 outline-none"
              >
                ✉️ Open in Gmail
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Outreach history panel */}
      {showHistory && history.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
          <h3 className="text-xs font-bold text-slate-800">Sent Outreach History Log</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-slate-400 font-bold uppercase tracking-wider border-b border-slate-100 text-[10px]">
                  <th className="text-left py-3 px-2">Candidate</th>
                  <th className="text-left py-3 px-2">Channel</th>
                  <th className="text-left py-3 px-2">Role Title</th>
                  <th className="text-left py-3 px-2">Date Sent</th>
                  <th className="text-left py-3 px-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {history.map(r => (
                  <tr key={r.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-2 text-slate-750 font-bold">{r.candidate_name}</td>
                    <td className="py-3 px-2 text-slate-500 font-semibold capitalize">{r.channel}</td>
                    <td className="py-3 px-2 text-slate-500 font-semibold">{r.role_name}</td>
                    <td className="py-3 px-2 text-slate-400 font-medium">{r.sent_at ? new Date(r.sent_at).toLocaleDateString() : '-'}</td>
                    <td className="py-3 px-2">
                      <span className={`px-2 py-0.5 rounded-full font-bold text-[9px] uppercase tracking-wide border ${
                        r.status === 'replied' || r.status === 'interested'
                          ? 'bg-green-50 text-green-700 border-green-150'
                          : r.status === 'no_response'
                          ? 'bg-red-55 text-red-650 border-red-150'
                          : 'bg-slate-50 text-slate-550 border-slate-200'
                      }`}>{r.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
