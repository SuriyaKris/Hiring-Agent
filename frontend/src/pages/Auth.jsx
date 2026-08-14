import React, { useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

export default function Auth({ onLoginSuccess }) {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email || !password || (!isLogin && !fullName)) {
      toast.error('Please fill in all fields.')
      return
    }

    setLoading(true)
    try {
      if (isLogin) {
        // Sign In
        const { data } = await axios.post('/api/auth/login', { email, password })
        localStorage.setItem('token', data.access_token)
        localStorage.setItem('user', JSON.stringify(data.user))
        axios.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
        toast.success(`Welcome back, ${data.user.full_name}!`)
        onLoginSuccess(data.access_token)
      } else {
        // Sign Up
        const { data } = await axios.post('/api/auth/signup', { email, password, full_name: fullName })
        localStorage.setItem('token', data.access_token)
        localStorage.setItem('user', JSON.stringify(data.user))
        axios.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
        toast.success(`Welcome, ${data.user.full_name}!`)
        onLoginSuccess(data.access_token)
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Authentication failed.'
      toast.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 select-none animate-fade-in-up">
      <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.03)] p-8 space-y-6">
        {/* Header Title */}
        <div className="text-center">
          <h2 className="text-xl font-extrabold text-slate-800">
            {isLogin ? 'Sign In to Your Account' : 'Create Recruiter Account'}
          </h2>
          <p className="text-xs text-slate-400 font-medium mt-2">
            {isLogin ? 'Access your sourcing results and pipelines history' : 'Register to save searches and filter duplicate candidates'}
          </p>
        </div>

        {/* Tab Selector */}
        <div className="flex bg-slate-100/80 p-1 rounded-xl">
          <button
            onClick={() => { setIsLogin(true); toast.dismiss(); }}
            className={`flex-1 py-2.5 text-xs font-bold rounded-lg transition-all outline-none ${
              isLogin ? 'bg-white text-slate-800 shadow-sm border border-slate-200/30' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => { setIsLogin(false); toast.dismiss(); }}
            className={`flex-1 py-2.5 text-xs font-bold rounded-lg transition-all outline-none ${
              !isLogin ? 'bg-white text-slate-800 shadow-sm border border-slate-200/30' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Register
          </button>
        </div>

        {/* Auth Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Full Name</label>
              <input
                type="text"
                placeholder="Sarah Connor"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-4 py-2.5 bg-[#edf2fa] border border-slate-200/70 rounded-xl text-sm focus:outline-none focus:border-blue-500 focus:bg-white transition-all text-slate-800"
              />
            </div>
          )}

          <div>
            <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Email Address</label>
            <input
              type="email"
              placeholder="recruiter@4cecloud.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2.5 bg-[#edf2fa] border border-slate-200/70 rounded-xl text-sm focus:outline-none focus:border-blue-500 focus:bg-white transition-all text-slate-800"
            />
          </div>

          <div>
            <label className="block text-[9px] font-bold text-slate-400 tracking-wider uppercase mb-1.5">Password</label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 bg-[#edf2fa] border border-slate-200/70 rounded-xl text-sm focus:outline-none focus:border-blue-500 focus:bg-white transition-all text-slate-800"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-[#0B57D0] hover:bg-[#0842a0] text-white rounded-xl text-xs font-bold shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-4 outline-none"
          >
            {loading ? 'Processing...' : isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  )
}
