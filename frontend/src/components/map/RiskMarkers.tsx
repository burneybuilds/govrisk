import { memo, useCallback } from 'react';
import { CircleMarker, Tooltip } from 'react-leaflet';
import type { ProjectRiskPoint, StateKey } from '../../types/map';
import { quantileColor } from '../../utils/colors';
import { resolveStateKey } from '../../constants/regions';
import { escapeHtml } from '../../utils/html';

export interface RiskMarkersProps {
  points: readonly ProjectRiskPoint[];
  selectedKey?: StateKey | null;
  onSelectRegion?: (key: StateKey) => void;
}

function radiusFor(score: number): number {
  return 5 + (Math.min(100, Math.max(0, score)) / 100) * 9;
}

function RiskMarkersInner({ points, selectedKey = null, onSelectRegion }: RiskMarkersProps) {
  const selectByPoint = useCallback(
    (point: ProjectRiskPoint) => {
      const key = resolveStateKey(point.stateName);
      if (key) onSelectRegion?.(key);
    },
    [onSelectRegion],
  );

  return (
    <>
      {points.map((point) => {
        const key = resolveStateKey(point.stateName) ?? point.stateName;
        const isSelected = key === selectedKey;
        return (
          <CircleMarker
            key={point.id}
            center={[point.lat, point.lng]}
            radius={radiusFor(point.riskScore)}
            pathOptions={{
              fillColor: quantileColor(point.riskScore / 100, 'risk'),
              fillOpacity: 0.85,
              color: isSelected ? '#fbbf24' : '#ffffff',
              weight: isSelected ? 2.5 : 1,
              opacity: 1,
            }}
            eventHandlers={{
              click: () => selectByPoint(point),
            }}
          >
            <Tooltip className="gm-map-tooltip" sticky direction="top">
              <div className="gm-tooltip-title">{escapeHtml(point.name)}</div>
              <div className="gm-tooltip-row">
                <span>Risk score</span>
                <b>{point.riskScore}/100</b>
              </div>
              <div className="gm-tooltip-row">
                <span>Delay prob.</span>
                <b>{point.delayProbability}%</b>
              </div>
            </Tooltip>
          </CircleMarker>
        );
      })}
    </>
  );
}

/**
 * Graduated project markers on the purple scale. Independent of the regional
 * choropleth so both can render together.
 */
export const RiskMarkers = memo(RiskMarkersInner);
