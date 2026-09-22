import React, { useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

export default function Auth({ onLoginSuccess }) {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)

  const handleDemoLogin = async () => {
    setEmail('recruiter@4cecloud.com')
    setPassword('password123')
    setLoading(true)
    try {
      // First try login
      try {
        const { data } = await axios.post('/api/auth/login', {
          email: 'recruiter@4cecloud.com',
          password: 'password123'
        })
        localStorage.setItem('token', data.access_token)
        localStorage.setItem('user', JSON.stringify(data.user))
        axios.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
        toast.success(`Welcome, ${data.user.full_name}!`)
        onLoginSuccess(data.access_token)
        return
      } catch (loginErr) {
        // If demo user doesn't exist yet, auto-register it
        const { data } = await axios.post('/api/auth/signup', {
          email: 'recruiter@4cecloud.com',
          password: 'password123',
          full_name: 'Meghana (Recruiter)'
        })
        localStorage.setItem('token', data.access_token)
        localStorage.setItem('user', JSON.stringify(data.user))
        axios.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
        toast.success(`Welcome, ${data.user.full_name}!`)
        onLoginSuccess(data.access_token)
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Demo login failed.')
    } finally {
      setLoading(false)
    }
  }

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
      const errorDetail = err.response?.data?.detail
      if (err.response?.status === 401) {
        toast.error('Incorrect email or password. If new, click "Register" or use "Quick Demo Login".')
      } else {
        toast.error(errorDetail || 'Authentication failed. Please check your credentials.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 select-none animate-fade-in-up">
      <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.03)] p-8 space-y-6">
        {/* Header Title */}
        <div className="text-center">
          <div className="w-12 h-12 bg-blue-50 text-[#0B57D0] rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-inner">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h2 className="text-xl font-extrabold text-slate-800">
            {isLogin ? 'Sign In to Your Account' : 'Create Recruiter Account'}
          </h2>
          <p className="text-xs text-slate-400 font-medium mt-2">
            {isLogin ? 'Access your sourcing results and pipelines history' : 'Register to save searches and filter duplicate candidates'}
          </p>
        </div>

        {/* Quick Demo Login Option */}
        <button
          type="button"
          onClick={handleDemoLogin}
          disabled={loading}
          className="w-full py-2.5 bg-blue-50 hover:bg-blue-100 text-[#0B57D0] border border-blue-200/80 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 outline-none shadow-sm"
        >
          <span>⚡</span> Quick Demo Login (recruiter@4cecloud.com)
        </button>

        <div className="flex items-center gap-3">
          <div className="flex-1 border-t border-slate-200"></div>
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">or credentials</span>
          <div className="flex-1 border-t border-slate-200"></div>
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
                placeholder="Meghana"
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
