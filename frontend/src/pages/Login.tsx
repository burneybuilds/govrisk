import { useState, FormEvent } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, AlertCircle, BarChart3 } from 'lucide-react';
import { login } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setUser } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email.trim() || !password) {
      setError('Please enter both email and password.');
      return;
    }
    setLoading(true);
    try {
      const data = await login(email.trim(), password);
      setUser(data.user);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-navy-950">
      <div className="hidden w-1/2 lg:block">
        <div className="flex h-full flex-col justify-between bg-gradient-to-br from-navy-900 via-navy-900 to-navy-800 p-12">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-base font-bold text-white">
              GR
            </div>
            <div>
              <h1 className="text-xl font-bold uppercase tracking-wide text-white">GovRisk</h1>
              <p className="text-xs text-navy-300">AI Infrastructure Intelligence</p>
            </div>
          </div>
          <div className="max-w-md">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-blue-600/20 text-blue-400">
              <BarChart3 size={28} />
            </div>
            <h2 className="text-3xl font-bold leading-tight text-white">
              Centralized risk intelligence for India's infrastructure portfolio.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-navy-300">
              Monitor 1,000+ projects across ministries with AI-powered early warnings,
              predictive cost and schedule analytics, and actionable risk intelligence.
            </p>
          </div>
          <p className="text-xs text-navy-500">
            Ministry of Electronics &amp; Information Technology · SIH 2026
          </p>
        </div>
      </div>

      <div className="flex w-full items-center justify-center px-6 py-12 lg:w-1/2">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600 text-sm font-bold text-white">
              GR
            </div>
            <div>
              <h1 className="text-lg font-bold uppercase tracking-wide text-white">GovRisk</h1>
              <p className="text-xs text-navy-300">AI Infrastructure Intelligence</p>
            </div>
          </div>

          <div className="rounded-2xl border border-navy-800 bg-navy-900 p-8 shadow-2xl">
            <h2 className="text-2xl font-bold text-white">Sign in</h2>
            <p className="mt-1.5 text-sm text-navy-300">
              Access the GovRisk monitoring platform
            </p>

            {error && (
              <div className="mt-5 flex items-start gap-2.5 rounded-lg border border-red-500/30 bg-red-500/10 p-3">
                <AlertCircle size={16} className="mt-0.5 shrink-0 text-red-400" />
                <p className="text-sm text-red-300">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-6 space-y-5">
              <div>
                <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-navy-100">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@govrisk.gov.in"
                  className="h-11 w-full rounded-lg border border-navy-700 bg-navy-800 px-4 text-sm text-white outline-none transition-all placeholder:text-navy-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                />
              </div>

              <div>
                <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-navy-100">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="h-11 w-full rounded-lg border border-navy-700 bg-navy-800 px-4 pr-11 text-sm text-white outline-none transition-all placeholder:text-navy-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((s) => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-navy-400 hover:text-navy-200"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="h-11 w-full rounded-lg bg-blue-600 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>
          </div>

          <p className="mt-6 text-center text-sm text-navy-300">
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold text-blue-400 hover:text-blue-300">
              Create one
            </Link>
          </p>

          <div className="mt-8 rounded-lg border border-navy-800 bg-navy-900/60 p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-navy-400">
              Demo accounts
            </p>
            <div className="grid grid-cols-1 gap-1 text-xs text-navy-300 sm:grid-cols-2">
              <span>admin@govrisk.gov.in / admin123</span>
              <span>officer@govrisk.gov.in / officer123</span>
              <span>analyst@govrisk.gov.in / analyst123</span>
              <span>viewer@govrisk.gov.in / viewer123</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}