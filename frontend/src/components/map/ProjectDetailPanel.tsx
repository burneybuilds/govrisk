import { memo } from 'react';
import { X } from 'lucide-react';
import type { ProjectRiskPoint, ProjectStatus } from '../../types/map';
import { PROJECT_STATUS_COLORS, projectStatusColor } from '../../utils/colors';

export interface ProjectDetailPanelProps {
  project: ProjectRiskPoint;
  onClose: () => void;
}

function StatusBadge({ status }: { status: ProjectStatus }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
      style={{
        color: projectStatusColor(status),
        borderColor: projectStatusColor(status),
        backgroundColor: `${PROJECT_STATUS_COLORS[status]}14`,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: projectStatusColor(status) }}
        aria-hidden="true"
      />
      {status}
    </span>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 text-[12px]">
      <span className="shrink-0 text-gray-400">{label}</span>
      <span className="text-right font-medium text-gray-100">{value}</span>
    </div>
  );
}

function formatCost(crore: number | undefined): string {
  if (crore === undefined || Number.isNaN(crore)) return '—';
  if (crore >= 100000) return `${(crore / 1000).toFixed(0)}k Cr`;
  return `₹${Math.round(crore)} crore`;
}

const FUNDING_LABELS: Record<string, string> = {
  CENTRAL_GOVT: 'Central government',
  STATE_GOVT: 'State government',
  PPP: 'Public–private',
  MIXED: 'Mixed',
  PRIVATE: 'Private',
};

function ProjectDetailPanelInner({ project, onClose }: ProjectDetailPanelProps) {
  const status = project.status ?? 'ONGOING';
  return (
    <div
      role="dialog"
      aria-label="Project details"
      className="pointer-events-auto flex max-h-[70vh] w-full max-w-[300px] flex-col overflow-hidden rounded-md border border-white/10 bg-[#0f1830]/95 text-gray-200 shadow-2xl backdrop-blur"
    >
      <div className="flex items-start justify-between gap-2 border-b border-white/10 px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-white">{project.name}</h3>
          <p className="mt-0.5 truncate text-[11px] text-gray-400">
            {project.agency && project.agency !== 'Unspecified'
              ? project.agency
              : project.stateName}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close project details"
          className="shrink-0 rounded p-1 text-gray-400 hover:bg-white/10 hover:text-white focus-visible:outline-2 focus-visible:outline-amber-400"
        >
          <X size={14} />
        </button>
      </div>

      <div className="space-y-2 overflow-y-auto px-3 py-2.5">
        <div className="flex items-center justify-between">
          <StatusBadge status={status} />
          {project.scale && (
            <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-300">
              {project.scale} scale
            </span>
          )}
        </div>

        <div className="space-y-1.5">
          <Row label="Sector" value={project.sector ?? '—'} />
          <Row label="Risk score" value={`${project.riskScore}/100 · ${project.riskLevel}`} />
          <Row label="Cost estimate" value={formatCost(project.costEstimateCr)} />
          <Row label="Delay prob." value={`${project.delayProbability}%`} />
          <Row label="Funding" value={FUNDING_LABELS[project.fundingSource ?? ''] ?? '—'} />
          <Row label="State" value={project.stateName} />
          {project.confidence && (
            <Row label="Data confidence" value={project.confidence.replaceAll('_', ' ')} />
          )}
        </div>

        <p className="border-t border-white/10 pt-2 text-[10px] leading-relaxed text-gray-500">
          {project.confidence
            ? `Data confidence: ${project.confidence.replaceAll('_', ' ').toLowerCase()} · gov-ingest provenance via /api/risk-map.`
            : 'Risk assessment computed from the deterministic risk engine.'}
        </p>
      </div>
    </div>
  );
}

export const ProjectDetailPanel = memo(ProjectDetailPanelInner);