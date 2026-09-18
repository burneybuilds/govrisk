import { memo, useCallback } from 'react';
import { CircleMarker, Tooltip } from 'react-leaflet';
import type { ProjectRiskPoint, ProjectScale, ProjectStatus } from '../../types/map';
import { projectStatusColor } from '../../utils/colors';
import { escapeHtml } from '../../utils/html';

export interface ProjectLayerProps {
  points: readonly ProjectRiskPoint[];
  /** Id of the currently highlighted project (from the detail panel). */
  selectedProjectId?: string | null;
  onSelectProject: (point: ProjectRiskPoint) => void;
}

/** Radius (px) for MEDIUM vs LARGE projects. */
const SCALE_RADIUS: Record<ProjectScale, number> = { MEDIUM: 6, LARGE: 9 };

const DEFAULT_RADIUS = 7;

function radiusFor(point: ProjectRiskPoint): number {
  if (point.scale) return SCALE_RADIUS[point.scale] ?? DEFAULT_RADIUS;
  // No scale metadata: derive from cost, else a neutral marker.
  if (point.costEstimateCr && point.costEstimateCr > 1000) return SCALE_RADIUS.LARGE;
  return SCALE_RADIUS.MEDIUM;
}

function ProjectLayerInner({ points, selectedProjectId = null, onSelectProject }: ProjectLayerProps) {
  const handleClick = useCallback(
    (point: ProjectRiskPoint) => onSelectProject(point),
    [onSelectProject],
  );

  return (
    <>
      {points.map((point) => {
        const status = point.status ?? 'ONGOING';
        const isSelected = point.id === selectedProjectId;
        return (
          <CircleMarker
            key={`proj-${point.id}`}
            center={[point.lat, point.lng]}
            radius={radiusFor(point)}
            pathOptions={{
              fillColor: projectStatusColor(status),
              fillOpacity: 0.7,
              color: isSelected ? '#ffffff' : '#0f1830',
              weight: isSelected ? 2.5 : 1,
              opacity: 1,
            }}
            eventHandlers={{ click: () => handleClick(point) }}
          >
            <Tooltip className="gm-map-tooltip" sticky direction="top">
              <div className="gm-tooltip-title">{escapeHtml(point.name)}</div>
              <div className="gm-tooltip-row">
                <span>Status</span>
                <b>{status}</b>
              </div>
              <div className="gm-tooltip-row">
                <span>Sector</span>
                <b>{escapeHtml(point.sector ?? '—')}</b>
              </div>
              <div className="gm-tooltip-row">
                <span>Cost</span>
                <b>{formatCost(point.costEstimateCr)}</b>
              </div>
            </Tooltip>
          </CircleMarker>
        );
      })}
    </>
  );
}

function formatCost(crore: number | undefined): string {
  if (crore === undefined || Number.isNaN(crore)) return '—';
  if (crore >= 1000) return `₹${(crore / 1000).toFixed(crore % 1000 === 0 ? 0 : 1)}k Cr`;
  return `₹${Math.round(crore)} Cr`;
}

/**
 * Government-ingest infrastructure projects layer. Status determines the fill
 * color, scale (or cost) or determines the radius. Independent of both the
 * choropleth and the risk markers so all three stack freely.
 */
export const ProjectLayer = memo(ProjectLayerInner);

export type { ProjectStatus };