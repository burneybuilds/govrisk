import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  AlertTriangle,
  DollarSign,
  ArrowLeft,
  Building,
  MapPin,
  Calendar,
  Target,
  TrendingDown,
  FileText,
  ShieldAlert,
  MessageSquare,
  Plus,
  PenSquare,
  Trash2,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { getProject, getProjectUpdates, deleteProjectUpdate } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { RiskBadge } from '../components/ui/RiskBadge';
import { RiskScore } from '../components/ui/RiskScore';
import { ProgressBar } from '../components/ui/ProgressBar';
import { LoadingState } from '../components/ui/LoadingState';
import { RiskFactorChart } from '../components/charts/RiskFactorChart';
import { ProjectTimeline } from '../components/project/ProjectTimeline';
import AddUpdateModal from '../components/project/AddUpdateModal';
import AddProjectModal from '../components/admin/AddProjectModal';
import { formatCurrency, formatDate, getRiskColor } from '../utils/helpers';

const UPDATE_TYPE_LABELS: Record<string, string> = {
  GENERAL: 'General',
  PROGRESS: 'Progress',
  RISK: 'Risk',
  FINANCIAL: 'Financial',
  MILESTONE: 'Milestone',
  FIELD_VISIT: 'Field Visit',
};

const UPDATE_TYPE_COLORS: Record<string, string> = {
  GENERAL: 'bg-gray-100 text-gray-600 ring-gray-200',
  PROGRESS: 'bg-blue-50 text-blue-700 ring-blue-200',
  RISK: 'bg-red-50 text-red-700 ring-red-200',
  FINANCIAL: 'bg-green-50 text-green-700 ring-green-200',
  MILESTONE: 'bg-amber-50 text-amber-700 ring-amber-200',
  FIELD_VISIT: 'bg-purple-50 text-purple-700 ring-purple-200',
};

function roleLabel(role: string) {
  switch (role) {
    case 'admin':
      return 'Admin';
    case 'officer':
      return 'Officer';
    case 'analyst':
      return 'Analyst';
    case 'viewer':
      return 'Viewer';
    default:
      return role;
  }
}

function formatUpdateTime(iso?: string) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const riskDriverData = [
  { name: 'Physical Progress Gap', value: 87 },
  { name: 'Milestone Delays', value: 81 },
  { name: 'Cost Escalation', value: 73 },
  { name: 'Expenditure Variance', value: 64 },
  { name: 'Historical Sector Risk', value: 58 },
];

function getBarColor(name: string) {
  switch (name) {
    case 'Original Cost':
      return '#3b82f6';
    case 'Current Cost':
      return '#f97316';
    case 'Predicted Final Cost':
      return '#ef4444';
    default:
      return '#3b82f6';
  }
}

function getMonthDifference(date1: string, date2: string) {
  const d1 = new Date(date1);
  const d2 = new Date(date2);
  const months = (d2.getFullYear() - d1.getFullYear()) * 12 + (d2.getMonth() - d1.getMonth());
  return Math.max(months, 0);
}

function getProgressColor(percentage: number): 'green' | 'yellow' | 'red' {
  if (percentage <= 50) return 'green';
  if (percentage <= 75) return 'yellow';
  return 'red';
}

function buildStatus(project: { riskLevel: string }) {
  if (!project) return '';
  return project.riskLevel;
}

export default function ProjectDetails() {
  const { id } = useParams<{ id: string }>();
  const { user: currentUser } = useAuth();
  const [project, setProject] = useState<Awaited<ReturnType<typeof getProject>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [updates, setUpdates] = useState<any[]>([]);
  const [updatesLoading, setUpdatesLoading] = useState(true);
  const [noteModal, setNoteModal] = useState<{ open: boolean; edit: any | null }>({
    open: false,
    edit: null,
  });
  const [noteToast, setNoteToast] = useState('');
  const [editProjectOpen, setEditProjectOpen] = useState(false);

  const canEditProject = currentUser?.role === 'admin' || currentUser?.role === 'officer';

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(false);
    getProject(id)
      .then((data) => {
        setProject(data);
      })
      .catch(() => {
        setError(true);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id]);

  const fetchUpdates = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getProjectUpdates(id);
      setUpdates(data);
    } catch {
      setUpdates([]);
    } finally {
      setUpdatesLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchUpdates();
  }, [fetchUpdates]);

  useEffect(() => {
    if (!noteToast) return;
    const t = setTimeout(() => setNoteToast(''), 4000);
    return () => clearTimeout(t);
  }, [noteToast]);

  function canModifyUpdate(u: any) {
    return currentUser?.role === 'admin' || u.userId === currentUser?.userId;
  }

  async function handleDeleteUpdate(u: any) {
    if (!id) return;
    const confirmed = window.confirm('Delete this update? This action cannot be undone.');
    if (!confirmed) return;
    try {
      await deleteProjectUpdate(id, u.id);
      fetchUpdates();
    } catch (e: any) {
      alert(e.message || 'Failed to delete update');
    }
  }

  if (loading) {
    return (
      <div className="mx-auto min-w-0 max-w-[1600px]">
        <LoadingState />
      </div>
    );
  }

  if (!project || error) {
    return (
      <div className="mx-auto min-w-0 max-w-[1600px]">
        <div className="flex flex-col items-center justify-center py-20">
          <AlertTriangle className="mb-4 h-12 w-12 text-red-500" />
          <h1 className="mb-2 text-2xl font-bold text-navy-900">Project not found</h1>
          <p className="mb-6 text-gray-500">The project you are looking for does not exist.</p>
          <Link
            to="/projects"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            <ArrowLeft size={16} />
            Back to Projects
          </Link>
        </div>
      </div>
    );
  }

  const predictedCost = Math.round(project.currentCost * 1.087);
  const costOverrunPercent = Math.round(((predictedCost - project.originalCost) / project.originalCost) * 100);
  const delayMonths = getMonthDifference(project.expectedCompletion, project.predictedCompletion);

  const projectCostData = [
    { name: 'Original Cost', value: project.originalCost },
    { name: 'Current Cost', value: project.currentCost },
    { name: 'Predicted Final Cost', value: predictedCost },
  ];

  const sectionLabel = 'text-xs font-semibold uppercase tracking-widest text-blue-600';

  return (
    <div className="mx-auto min-w-0 max-w-[1600px]">
      <Link
        to="/projects"
        className="mb-5 inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 transition-colors hover:text-navy-900"
      >
        <ArrowLeft size={16} />
        Back to Projects
      </Link>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">
            {project.name}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-gray-500">
            <span className="inline-flex items-center gap-1.5">
              <Building size={14} className="text-gray-400" />
              {project.ministry}
            </span>
            <span className="text-gray-300">•</span>
            <span className="inline-flex items-center gap-1.5">
              <FileText size={14} className="text-gray-400" />
              {project.sector}
            </span>
            <span className="text-gray-300">•</span>
            <span className="inline-flex items-center gap-1.5">
              <MapPin size={14} className="text-gray-400" />
              {project.state}
            </span>
            <span className="text-gray-300">•</span>
            <span className="inline-flex items-center gap-1.5">{project.agency}</span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <RiskBadge level={project.riskLevel} />
          {canEditProject && (
            <button
              onClick={() => setEditProjectOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3.5 py-2 text-sm font-semibold text-navy-900 transition-colors hover:bg-gray-50"
            >
              <PenSquare className="h-4 w-4" />
              Edit Project
            </button>
          )}
        </div>
      </div>

      <div className="mb-8">
        <p className={`${sectionLabel} mb-3`}>Project Overview</p>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="mb-2 flex items-center gap-2">
              <DollarSign size={16} className="text-blue-500" />
              <span className="text-xs font-medium text-gray-500">Original Cost</span>
            </div>
            <p className="text-base font-bold text-navy-900 lg:text-lg">{formatCurrency(project.originalCost)}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="mb-2 flex items-center gap-2">
              <DollarSign size={16} className="text-orange-500" />
              <span className="text-xs font-medium text-gray-500">Current Cost</span>
            </div>
            <p className="text-base font-bold text-navy-900 lg:text-lg">{formatCurrency(project.currentCost)}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="mb-2 flex items-center gap-2">
              <TrendingDown size={16} className="text-gray-500" />
              <span className="text-xs font-medium text-gray-500">Expenditure</span>
            </div>
            <p className="text-base font-bold text-navy-900 lg:text-lg">{formatCurrency(project.expenditure)}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="mb-2 flex items-center gap-2">
              <Target size={16} className="text-green-500" />
              <span className="text-xs font-medium text-gray-500">Physical Progress</span>
            </div>
            <p className="mb-1.5 text-base font-bold text-navy-900 lg:text-lg">{project.physicalProgress}%</p>
            <ProgressBar value={project.physicalProgress} color="green" />
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="mb-2 flex items-center gap-2">
              <Target size={16} className="text-gray-500" />
              <span className="text-xs font-medium text-gray-500">Planned Progress</span>
            </div>
            <p className="mb-1.5 text-base font-bold text-navy-900 lg:text-lg">{project.plannedProgress}%</p>
            <ProgressBar value={project.plannedProgress} color="gray" />
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="mb-2 flex items-center gap-2">
              <Calendar size={16} className="text-navy-500" />
              <span className="text-xs font-medium text-gray-500">Expected Completion</span>
            </div>
            <p className="text-sm font-bold text-navy-900">{formatDate(project.expectedCompletion)}</p>
          </div>
        </div>
      </div>

      <div className="mb-8">
        <p className={`${sectionLabel} mb-3`}>AI Risk Assessment</p>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-700">Overall Risk</h3>
              <ShieldAlert size={18} className="text-navy-300" />
            </div>
            <div className="my-5 flex justify-center">
              <RiskScore score={project.riskScore} size="lg" />
            </div>
            <p className="text-center text-sm text-gray-400">
              Score <span className="text-xl font-bold text-navy-900">{project.riskScore}</span> / 100
            </p>
            <p className={`mb-6 mt-1 text-center text-xl font-bold tracking-wide ${getRiskColor(project.riskLevel)}`}>
              {project.riskLevel} RISK
            </p>
            <div className="space-y-4 border-t border-gray-100 pt-4">
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-sm text-gray-600">Cost Risk</span>
                  <span className="text-sm font-semibold text-gray-800">{project.costOverrunProbability}%</span>
                </div>
                <ProgressBar value={project.costOverrunProbability} color={getProgressColor(project.costOverrunProbability)} size="sm" />
              </div>
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-sm text-gray-600">Schedule Risk</span>
                  <span className="text-sm font-semibold text-gray-800">{project.delayProbability}%</span>
                </div>
                <ProgressBar value={project.delayProbability} color={project.delayProbability > 80 ? 'red' : getProgressColor(project.delayProbability)} size="sm" />
              </div>
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-sm text-gray-600">Implementation Risk</span>
                  <span className="text-sm font-semibold text-gray-800">{project.implementationRisk}%</span>
                </div>
                <ProgressBar value={project.implementationRisk} color={getProgressColor(project.implementationRisk)} size="sm" />
              </div>
            </div>
          </div>

          <div className="space-y-6 lg:col-span-2">
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-orange-600">AI Risk Analysis</p>
              <h3 className="mb-4 mt-1 text-base font-semibold text-navy-900 lg:text-lg">
                Why is this project at risk?
              </h3>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {project.riskFactors.map((factor: string, index: number) => (
                  <div key={index} className="flex items-start gap-3 rounded-lg bg-orange-50/60 p-3">
                    <AlertTriangle size={16} className="mt-0.5 shrink-0 text-orange-500" />
                    <span className="text-sm leading-relaxed text-gray-700">{factor}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-blue-600">Recommended Interventions</p>
              <h3 className="mb-4 mt-1 text-base font-semibold text-navy-900 lg:text-lg">
                Recommended actions for the implementing agency
              </h3>
              <div className="space-y-3">
                {project.recommendations.map((rec: string, index: number) => (
                  <div key={index} className="flex items-start gap-3">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy-900 text-xs font-bold text-white">
                      {index + 1}
                    </span>
                    <span className="text-sm leading-relaxed text-gray-700">{rec}</span>
                  </div>
                ))}
              </div>
              <button className="mt-6 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-700">
                <FileText size={15} />
                Generate Detailed Risk Report
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="mb-8 rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-blue-600">Cost Prediction</p>
        <h3 className="mb-2 mt-1 text-base font-semibold text-navy-900 lg:text-lg">Predicted final cost</h3>
        <p className="mb-5 text-xs text-gray-500 lg:text-sm">
          Projected cost trajectory based on current escalation trend.
        </p>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={projectCostData} margin={{ top: 10, right: 16, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  axisLine={{ stroke: '#e5e7eb' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  axisLine={false}
                  tickLine={false}
                  width={70}
                  tickFormatter={(v) => `₹${(v / 100).toFixed(0)}Cr`}
                />
                <Tooltip
                  formatter={(value) => [formatCurrency(value as number), 'Amount']}
                  contentStyle={{
                    borderRadius: 8,
                    border: '1px solid #e5e7eb',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                    fontSize: 12,
                  }}
                  cursor={{ fill: '#f8fafc' }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={64}>
                  {projectCostData.map((entry) => (
                    <Cell key={entry.name} fill={getBarColor(entry.name)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-col justify-center">
            <p className="text-sm text-gray-500">Predicted Cost Overrun</p>
            <p className="mt-1 text-4xl font-bold tracking-tight text-red-600">+{costOverrunPercent}%</p>
            <p className="mt-1 text-sm text-gray-500">from original estimate</p>
            <div className="mt-5 space-y-2.5 border-t border-gray-100 pt-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Original</span>
                <span className="font-medium text-gray-700">{formatCurrency(project.originalCost)}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Predicted Final</span>
                <span className="font-semibold text-red-600">{formatCurrency(predictedCost)}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Potential Overspend</span>
                <span className="font-semibold text-red-600">{formatCurrency(predictedCost - project.originalCost)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mb-8 rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-orange-600">Schedule Prediction</p>
        <h3 className="mb-2 mt-1 text-base font-semibold text-navy-900 lg:text-lg">
          Predicted completion vs original plan
        </h3>
        <p className="mb-5 text-xs text-gray-500 lg:text-sm">
          {buildStatus(project)} risk project with estimated {delayMonths > 0 ? `${delayMonths} month` : ''} expected schedule slippage.
        </p>
        <ProjectTimeline
          expectedCompletion={project.expectedCompletion}
          predictedCompletion={project.predictedCompletion}
          delayMonths={delayMonths}
          delayProbability={project.delayProbability}
          progressGap={project.plannedProgress - project.physicalProgress}
        />
      </div>

      <section className="mb-8 rounded-xl border border-gray-200 bg-white p-5 lg:p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-blue-600">
              Project Updates
            </p>
            <h3 className="mt-1 text-base font-semibold text-navy-900 lg:text-lg">
              Notes and updates from the team
            </h3>
          </div>
          <button
            onClick={() => setNoteModal({ open: true, edit: null })}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
          >
            <Plus className="h-4 w-4" />
            Add Note / Update
          </button>
        </div>

        {noteToast && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 p-3">
            <MessageSquare className="mt-0.5 h-4 w-4 flex-shrink-0 text-green-600" />
            <p className="text-sm text-green-700">{noteToast}</p>
          </div>
        )}

        {updatesLoading ? (
          <LoadingState text="Loading updates..." />
        ) : updates.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 py-10 text-center">
            <MessageSquare className="mb-3 h-8 w-8 text-gray-300" />
            <p className="text-sm font-medium text-navy-900">No updates yet</p>
            <p className="mt-1 text-sm text-gray-500">
              Be the first to add a note or update for this project.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {updates.map((u) => (
              <div key={u.id} className="rounded-xl border border-gray-200 p-4">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-navy-900">
                      {u.userName}
                    </span>
                    <span className="text-sm text-gray-500">
                      &middot; {roleLabel(u.userRole)}
                    </span>
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${
                        UPDATE_TYPE_COLORS[u.updateType] || UPDATE_TYPE_COLORS.GENERAL
                      }`}
                    >
                      {UPDATE_TYPE_LABELS[u.updateType] || u.updateType}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">
                      {formatUpdateTime(u.createdAt)}
                    </span>
                    {canModifyUpdate(u) && (
                      <>
                        <button
                          onClick={() => setNoteModal({ open: true, edit: u })}
                          className="inline-flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs font-medium text-navy-900 hover:bg-gray-50"
                        >
                          <PenSquare className="h-3 w-3" />
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteUpdate(u)}
                          className="inline-flex items-center gap-1 rounded-lg border border-red-200 bg-white px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                        >
                          <Trash2 className="h-3 w-3" />
                          Delete
                        </button>
                      </>
                    )}
                  </div>
                </div>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700">
                  {u.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      <RiskFactorChart
        data={riskDriverData}
        title="What is driving the risk?"
        description="Relative contribution of key risk drivers to this project's overall risk score."
      />

      {id && (
        <AddUpdateModal
          projectId={id}
          open={noteModal.open}
          initial={noteModal.edit}
          onClose={() => setNoteModal({ open: false, edit: null })}
          onSaved={() => {
            setNoteToast(noteModal.edit ? 'Update saved.' : 'Update added successfully.');
            fetchUpdates();
          }}
        />
      )}

      <AddProjectModal
        open={editProjectOpen}
        mode="edit"
        initial={project}
        onClose={() => setEditProjectOpen(false)}
        onCreated={(p) => {
          setProject(p);
          setEditProjectOpen(false);
        }}
      />
    </div>
  );
}
