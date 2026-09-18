import { useState, FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';
import { register } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useI18n } from '../i18n';

export default function Register() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const { t } = useI18n();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [department, setDepartment] = useState('');
  const [designation, setDesignation] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (!fullName.trim() || !email.trim() || !password) {
      setError(t('register.required'));
      return;
    }
    if (password.length < 6) {
      setError(t('register.passwordShort'));
      return;
    }
    if (password !== confirmPassword) {
      setError(t('register.passwordMismatch'));
      return;
    }
    setLoading(true);
    try {
      const data = await register({
        fullName: fullName.trim(),
        email: email.trim(),
        password,
        department: department.trim() || undefined,
        designation: designation.trim() || undefined,
      });
      setUser(data.user);
      navigate('/', { replace: true });
    } catch (err: any) {
      setError(err.message || t('register.failed'));
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    'h-11 w-full rounded-lg border border-navy-700 bg-navy-800 px-4 text-sm text-white outline-none transition-all placeholder:text-navy-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30';

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
              <p className="text-xs text-navy-300">{t('register.platformTitle')}</p>
            </div>
          </div>
          <div className="max-w-md">
            <h2 className="text-3xl font-bold leading-tight text-white">
              {t('register.heroTitle')}
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-navy-300">
              {t('register.heroDesc')}
            </p>
          </div>
          <p className="text-xs text-navy-500">
            {t('register.footerLine')}
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
              <p className="text-xs text-navy-300">{t('register.platformTitle')}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-navy-800 bg-navy-900 p-8 shadow-2xl">
            <h2 className="text-2xl font-bold text-white">{t('register.title')}</h2>
            <p className="mt-1.5 text-sm text-navy-300">
              {t('register.subtitle')}
            </p>

            {error && (
              <div className="mt-5 flex items-start gap-2.5 rounded-lg border border-red-500/30 bg-red-500/10 p-3">
                <AlertCircle size={16} className="mt-0.5 shrink-0 text-red-400" />
                <p className="text-sm text-red-300">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <div>
                <label
                  htmlFor="fullName"
                  className="mb-1.5 block text-sm font-medium text-navy-100"
                >
                  {t('register.fullName')}
                </label>
                <input
                  id="fullName"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder={t('register.fullNamePh')}
                  className={inputClass}
                />
              </div>

              <div>
                <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-navy-100">
                  {t('register.email')}
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t('register.emailPh')}
                  className={inputClass}
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label
                    htmlFor="password"
                    className="mb-1.5 block text-sm font-medium text-navy-100"
                  >
                    {t('register.password')}
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={t('register.passwordPh')}
                      className="h-11 w-full rounded-lg border border-navy-700 bg-navy-800 px-4 pr-11 text-sm text-white outline-none transition-all placeholder:text-navy-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((s) => !s)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-navy-400 hover:text-navy-200"
                      aria-label={showPassword ? t('login.hidePassword') : t('login.showPassword')}
                    >
                      {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label
                    htmlFor="confirmPassword"
                    className="mb-1.5 block text-sm font-medium text-navy-100"
                  >
                    {t('register.confirmPassword')}
                  </label>
                  <input
                    id="confirmPassword"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder={t('register.confirmPasswordPh')}
                    className="h-11 w-full rounded-lg border border-navy-700 bg-navy-800 px-4 text-sm text-white outline-none transition-all placeholder:text-navy-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label
                    htmlFor="department"
                    className="mb-1.5 block text-sm font-medium text-navy-100"
                  >
                    {t('register.department')}{' '}
                    <span className="text-navy-500">({t('common.optional')})</span>
                  </label>
                  <input
                    id="department"
                    type="text"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    placeholder={t('register.departmentPh')}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label
                    htmlFor="designation"
                    className="mb-1.5 block text-sm font-medium text-navy-100"
                  >
                    {t('register.designation')}{' '}
                    <span className="text-navy-500">({t('common.optional')})</span>
                  </label>
                  <input
                    id="designation"
                    type="text"
                    value={designation}
                    onChange={(e) => setDesignation(e.target.value)}
                    placeholder={t('register.designationPh')}
                    className={inputClass}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="h-11 w-full rounded-lg bg-blue-600 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? t('register.creating') : t('register.create')}
              </button>
            </form>
          </div>

          <p className="mt-6 text-center text-sm text-navy-300">
            {t('register.hasAccount')}{' '}
            <Link to="/login" className="font-semibold text-blue-400 hover:text-blue-300">
              {t('register.signIn')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
