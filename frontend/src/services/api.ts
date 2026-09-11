const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function getAccessToken(): string | null {
  return localStorage.getItem('govrisk_access_token');
}

function getRefreshToken(): string | null {
  return localStorage.getItem('govrisk_refresh_token');
}

function setTokens(access: string, refresh: string) {
  localStorage.setItem('govrisk_access_token', access);
  localStorage.setItem('govrisk_refresh_token', refresh);
}

function clearTokens() {
  localStorage.removeItem('govrisk_access_token');
  localStorage.removeItem('govrisk_refresh_token');
}

let isRefreshing = false;
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refresh = getRefreshToken();
  if (!refresh) throw new Error('No refresh token');
  const res = await fetch(`${API_BASE}/api/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refreshToken: refresh }),
  });
  if (!res.ok) {
    clearTokens();
    throw new Error('Refresh failed');
  }
  const data = await res.json();
  setTokens(data.accessToken, data.refreshToken);
  return data.accessToken;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options?.headers as Record<string, string> || {}),
  };

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && !path.includes('/api/auth/')) {
    if (!isRefreshing) {
      isRefreshing = true;
      refreshPromise = refreshAccessToken().finally(() => {
        isRefreshing = false;
        refreshPromise = null;
      });
    }
    try {
      const newToken = await refreshPromise!;
      headers.Authorization = `Bearer ${newToken}`;
      res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    } catch {
      clearTokens();
      window.location.href = '/login';
      throw new Error('Session expired');
    }
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    const rawDetail = errorData?.detail;
    const message = Array.isArray(rawDetail)
      ? rawDetail.map((d: any) => d.msg || String(d)).join('; ')
      : rawDetail || `API error: ${res.status}`;
    throw new Error(message);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

// Auth API
export async function login(email: string, password: string) {
  const data = await apiFetch<{ accessToken: string; refreshToken: string; user: any }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setTokens(data.accessToken, data.refreshToken);
  return data;
}

export async function register(payload: {
  fullName: string;
  email: string;
  password: string;
  department?: string;
  designation?: string;
}) {
  const data = await apiFetch<{ accessToken: string; refreshToken: string; user: any }>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  setTokens(data.accessToken, data.refreshToken);
  return data;
}

export async function getMe() {
  return apiFetch<any>('/api/auth/me');
}

export async function logout() {
  try {
    await apiFetch('/api/auth/logout', { method: 'POST' });
  } finally {
    clearTokens();
  }
}

export function logoutLocal() {
  clearTokens();
}

// Profile API
export async function updateProfile(data: { fullName?: string; department?: string; designation?: string }) {
  return apiFetch<any>('/api/users/me', { method: 'PUT', body: JSON.stringify(data) });
}

export async function changePassword(data: { currentPassword: string; newPassword: string }) {
  return apiFetch<any>('/api/users/me/password', { method: 'PUT', body: JSON.stringify(data) });
}

// Admin API
export interface UserListParams {
  search?: string;
  role?: string;
  status?: string;
  department?: string;
  page?: number;
  limit?: number;
}

export interface UserListResponse {
  items: any[];
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export function getUsers(params: UserListParams = {}) {
  const query = new URLSearchParams();
  if (params.search) query.set('search', params.search);
  if (params.role) query.set('role', params.role);
  if (params.status) query.set('status', params.status);
  if (params.department) query.set('department', params.department);
  if (params.page) query.set('page', String(params.page));
  if (params.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return apiFetch<UserListResponse>(`/api/users${qs ? `?${qs}` : ''}`);
}

export async function getUserById(id: string) {
  return apiFetch<any>(`/api/users/${id}`);
}

export function createUser(data: {
  fullName: string;
  email: string;
  role: string;
  department?: string;
  designation?: string;
  temporaryPassword: string;
  isActive: boolean;
}) {
  return apiFetch<any>('/api/users', { method: 'POST', body: JSON.stringify(data) });
}

export function adminUpdateUser(id: string, data: { fullName?: string; email?: string; department?: string; designation?: string }) {
  return apiFetch<any>(`/api/users/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

export function updateUserRole(id: string, role: string) {
  return apiFetch<any>(`/api/users/${id}/role`, { method: 'PATCH', body: JSON.stringify({ role }) });
}

export function updateUserStatus(id: string, isActive: boolean) {
  return apiFetch<any>(`/api/users/${id}/status`, { method: 'PATCH', body: JSON.stringify({ isActive }) });
}

export function resetUserPassword(id: string) {
  return apiFetch<{ message: string; temporaryPassword: string }>(`/api/users/${id}/reset-password`, { method: 'POST' });
}

export function getUserStats() {
  return apiFetch<{
    total: number;
    active: number;
    inactive: number;
    admins: number;
    officers: number;
    analysts: number;
    viewers: number;
  }>('/api/users/stats');
}

export interface AuditLogParams {
  page?: number;
  limit?: number;
  action?: string;
  user_id?: string;
}

export function getAuditLogs(params: AuditLogParams = {}) {
  const query = new URLSearchParams();
  if (params.page) query.set('page', String(params.page));
  if (params.limit) query.set('limit', String(params.limit));
  if (params.action) query.set('action', params.action);
  if (params.user_id) query.set('user_id', params.user_id);
  const qs = query.toString();
  return apiFetch<{ items: any[]; page: number; limit: number; total: number; totalPages: number }>(
    `/api/admin/audit-logs${qs ? `?${qs}` : ''}`
  );
}

// Project API
export async function getProjects() {
  return apiFetch<any[]>('/api/projects');
}

export async function getProject(id: string) {
  return apiFetch<any>(`/api/projects/${id}`);
}

export async function getProjectRisk(id: string) {
  return apiFetch<any>(`/api/projects/${id}/risk`);
}

export interface ProjectCreateData {
  name: string;
  ministry: string;
  agency: string;
  sector: string;
  state: string;
  district?: string;
  originalCost: number;
  revisedCost?: number | null;
  expenditure?: number | null;
  physicalProgress: number;
  financialProgress?: number | null;
  startDate: string;
  completionDate: string;
  predictedCompletionDate?: string | null;
  description?: string;
  nodalOfficer?: string;
  contactInfo?: string;
  lat?: number | null;
  lng?: number | null;
  riskInputs?: Record<string, any>;
}

export function createProject(data: ProjectCreateData) {
  return apiFetch<any>('/api/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateProject(id: string, data: Partial<ProjectCreateData>) {
  return apiFetch<any>(`/api/projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export interface ProjectUpdateData {
  updateType: string;
  content: string;
}

export function getProjectUpdates(projectId: string) {
  return apiFetch<any[]>(`/api/projects/${projectId}/updates`);
}

export function addProjectUpdate(projectId: string, data: ProjectUpdateData) {
  return apiFetch<any>(`/api/projects/${projectId}/updates`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function updateProjectUpdate(
  projectId: string,
  updateId: number,
  data: ProjectUpdateData
) {
  return apiFetch<any>(`/api/projects/${projectId}/updates/${updateId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export function deleteProjectUpdate(projectId: string, updateId: number) {
  return apiFetch<any>(`/api/projects/${projectId}/updates/${updateId}`, {
    method: 'DELETE',
  });
}

export async function getAlerts() {
  return apiFetch<any[]>('/api/alerts');
}

export async function getDashboard() {
  return apiFetch<any>('/api/dashboard');
}

export async function getAnalytics() {
  return apiFetch<any>('/api/analytics');
}

export async function getRiskMapData() {
  return apiFetch<any[]>('/api/risk-map');
}

export async function sendAssistantMessage(query: string) {
  return apiFetch<{ reply: string }>('/api/assistant', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
}
