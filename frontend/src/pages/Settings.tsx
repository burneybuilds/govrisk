import { useState, useEffect } from 'react';
import { Bell, Monitor, User, KeyRound, Save, Check, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { updateProfile, changePassword } from '../services/api';

const roleLabels: Record<string, string> = {
  admin: 'Administrator',
  officer: 'Project Officer',
  analyst: 'Risk Analyst',
  viewer: 'Viewer',
};

function formatDate(iso?: string) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function Settings() {
  const { user, setUser } = useAuth();

  const [emailAlerts, setEmailAlerts] = useState(true);
  const [dailySummary, setDailySummary] = useState(true);
  const [weeklyReport, setWeeklyReport] = useState(false);
  const [defaultView, setDefaultView] = useState('grid');
  const [perPage, setPerPage] = useState('10');

  const [fullName, setFullName] = useState(user?.fullName ?? '');
  const [department, setDepartment] = useState(user?.department ?? '');
  const [designation, setDesignation] = useState(user?.designation ?? '');
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState('');
  const [profileError, setProfileError] = useState('');

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [passwordError, setPasswordError] = useState('');

  useEffect(() => {
    if (user) {
      setFullName(user.fullName);
      setDepartment(user.department ?? '');
      setDesignation(user.designation ?? '');
    }
  }, [user]);

  async function handleProfileSave() {
    setProfileError('');
    setProfileSuccess('');
    setProfileSaving(true);
    try {
      const updated = await updateProfile({ fullName, department, designation });
      setUser(updated);
      setProfileSuccess('Profile updated');
    } catch (e: any) {
      setProfileError(e.message || 'Failed to update profile');
    } finally {
      setProfileSaving(false);
    }
  }

  async function handlePasswordChange() {
    setPasswordError('');
    setPasswordSuccess('');
    if (newPassword.length < 6) {
      setPasswordError('New password must be at least 6 characters');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match');
      return;
    }
    setPasswordSaving(true);
    try {
      await changePassword({ currentPassword, newPassword });
      setPasswordSuccess('Password changed successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (e: any) {
      setPasswordError(e.message || 'Failed to change password');
    } finally {
      setPasswordSaving(false);
    }
  }

  const inputClass =
    'h-11 w-full rounded-lg border border-gray-200 bg-white px-3.5 text-sm text-gray-700 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20';

  return (
    <div className="mx-auto min-w-0 max-w-[800px]">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">Settings</h1>
          <p className="mt-1 text-sm text-gray-500 lg:text-base">Profile, security, and application preferences</p>
        </div>
      </div>

      <div className="space-y-6">
        <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
          <div className="mb-4 flex items-center gap-3 border-b border-gray-100 pb-4">
            <span className="rounded-lg bg-blue-50 p-2">
              <User className="h-5 w-5 text-blue-600" />
            </span>
            <h2 className="text-base font-semibold text-navy-900 lg:text-lg">Profile</h2>
          </div>
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">User ID</span>
              <span className="text-sm font-medium text-navy-900">{user?.userId}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Name</span>
              <span className="text-sm font-medium text-navy-900">{user?.fullName}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Role</span>
              <span className="text-sm font-medium text-navy-900">{roleLabels[user?.role ?? 'viewer']}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Email</span>
              <span className="text-sm font-medium text-navy-900">{user?.email}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Account created</span>
              <span className="text-sm font-medium text-navy-900">{formatDate(user?.createdAt)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Last login</span>
              <span className="text-sm font-medium text-navy-900">{formatDate(user?.lastLogin)}</span>
            </div>
          </div>

          {profileError && (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3">
              <AlertCircle size={16} className="mt-0.5 shrink-0 text-red-500" />
              <p className="text-sm text-red-600">{profileError}</p>
            </div>
          )}
          {profileSuccess && (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 p-3">
              <Check size={16} className="mt-0.5 shrink-0 text-green-600" />
              <p className="text-sm text-green-700">{profileSuccess}</p>
            </div>
          )}

          <div className="mt-5 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-gray-500">Full Name</label>
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} className={inputClass} />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">Department</label>
                <input value={department} onChange={(e) => setDepartment(e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">Designation</label>
                <input value={designation} onChange={(e) => setDesignation(e.target.value)} className={inputClass} />
              </div>
            </div>
            <button
              onClick={handleProfileSave}
              disabled={profileSaving}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Save size={16} />
              {profileSaving ? 'Saving...' : 'Save changes'}
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
          <div className="mb-4 flex items-center gap-3 border-b border-gray-100 pb-4">
            <span className="rounded-lg bg-blue-50 p-2">
              <KeyRound className="h-5 w-5 text-blue-600" />
            </span>
            <h2 className="text-base font-semibold text-navy-900 lg:text-lg">Change Password</h2>
          </div>

          {passwordError && (
            <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3">
              <AlertCircle size={16} className="mt-0.5 shrink-0 text-red-500" />
              <p className="text-sm text-red-600">{passwordError}</p>
            </div>
          )}
          {passwordSuccess && (
            <div className="mb-4 flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 p-3">
              <Check size={16} className="mt-0.5 shrink-0 text-green-600" />
              <p className="text-sm text-green-700">{passwordSuccess}</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-gray-500">Current Password</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className={inputClass}
              />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">Confirm New Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
            <button
              onClick={handlePasswordChange}
              disabled={passwordSaving}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-navy-900 px-4 text-sm font-semibold text-white transition-colors hover:bg-navy-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <KeyRound size={16} />
              {passwordSaving ? 'Updating...' : 'Update password'}
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
          <div className="mb-4 flex items-center gap-3 border-b border-gray-100 pb-4">
            <span className="rounded-lg bg-blue-50 p-2">
              <Bell className="h-5 w-5 text-blue-600" />
            </span>
            <h2 className="text-base font-semibold text-navy-900 lg:text-lg">Notification Preferences</h2>
          </div>
          <div className="space-y-4">
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-700">Email alerts for critical risks</span>
              <input
                type="checkbox"
                checked={emailAlerts}
                onChange={(e) => setEmailAlerts(e.target.checked)}
                className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-700">Daily portfolio summary</span>
              <input
                type="checkbox"
                checked={dailySummary}
                onChange={(e) => setDailySummary(e.target.checked)}
                className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-gray-700">Weekly report generation</span>
              <input
                type="checkbox"
                checked={weeklyReport}
                onChange={(e) => setWeeklyReport(e.target.checked)}
                className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </label>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
          <div className="mb-4 flex items-center gap-3 border-b border-gray-100 pb-4">
            <span className="rounded-lg bg-blue-50 p-2">
              <Monitor className="h-5 w-5 text-blue-600" />
            </span>
            <h2 className="text-base font-semibold text-navy-900 lg:text-lg">Display Settings</h2>
          </div>
          <div className="space-y-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Default risk view</label>
              <select
                value={defaultView}
                onChange={(e) => setDefaultView(e.target.value)}
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="grid">Grid</option>
                <option value="table">Table</option>
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-500">Projects per page</label>
              <select
                value={perPage}
                onChange={(e) => setPerPage(e.target.value)}
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}