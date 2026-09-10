import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getProjects, getRiskMapData } from '../services/api';
import { LoadingState } from '../components/ui/LoadingState';

interface RiskMapProject {
  id: string;
  name: string;
  sector: string;
  state: string;
  riskLevel: string;
  riskScore: number;
  lat: number;
  lng: number;
  expenditure: number;
  physicalProgress: number;
  plannedProgress: number;
}

const riskColors: Record<string, string> = {
  LOW: '#22c55e',
  MEDIUM: '#eab308',
  HIGH: '#f97316',
  CRITICAL: '#ef4444',
};

const riskRadii: Record<string, number> = {
  LOW: 8,
  MEDIUM: 10,
  HIGH: 12,
  CRITICAL: 14,
};

export default function RiskMap() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [riskMapData, setRiskMapData] = useState<RiskMapProject[]>([]);
  const [projects, setProjects] = useState<any[]>([]);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const [riskData, projectData] = await Promise.all([
          getRiskMapData(),
          getProjects(),
        ]);
        setRiskMapData(riskData);
        setProjects(projectData);
      } catch (err: any) {
        setError(err.message || 'Failed to load risk map data');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current || riskMapData.length === 0) return;

    const map = L.map(mapRef.current).setView([20.5937, 78.9629], 5);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    riskMapData.forEach((project) => {
      const color = riskColors[project.riskLevel];
      const radius = riskRadii[project.riskLevel];

      const marker = L.circleMarker([project.lat, project.lng], {
        radius,
        fillColor: color,
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8,
      }).addTo(map);

      const popupContent = `
        <div style="min-width: 220px;">
          <h3 style="font-weight: 600; font-size: 14px; margin-bottom: 4px;">${project.name}</h3>
          <p style="font-size: 12px; color: #6b7280; margin-bottom: 8px;">${project.state}</p>
          <div style="font-size: 13px; line-height: 1.6;">
            <div><strong>Risk Score:</strong> ${project.riskScore}</div>
          </div>
          <button class="view-project-btn" data-id="${project.id}" style="display: inline-block; margin-top: 8px; font-size: 13px; color: #2563eb; font-weight: 500; background: none; border: none; cursor: pointer; padding: 0;">View Project →</button>
        </div>
      `;

      marker.bindPopup(popupContent);

      marker.on('popupopen', () => {
        const btn = document.querySelector(`.view-project-btn[data-id="${project.id}"]`);
        if (btn) {
          btn.addEventListener('click', () => navigate(`/projects/${project.id}`));
        }
      });
    });

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, [riskMapData, projects, navigate]);

  const legendItems = [
    { label: 'Low Risk', color: riskColors.LOW },
    { label: 'Medium Risk', color: riskColors.MEDIUM },
    { label: 'High Risk', color: riskColors.HIGH },
    { label: 'Critical Risk', color: riskColors.CRITICAL },
  ];

  if (loading) {
    return (
      <div className="mx-auto min-w-0 max-w-[1200px]">
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">Risk Map</h1>
          <p className="mt-1 text-sm text-gray-500 lg:text-base">Geographic distribution of project risks</p>
        </div>
        <div className="mb-6 overflow-hidden rounded-xl border border-gray-200 bg-white">
          <LoadingState text="Loading risk map data..." />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto min-w-0 max-w-[1200px]">
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">Risk Map</h1>
          <p className="mt-1 text-sm text-gray-500 lg:text-base">Geographic distribution of project risks</p>
        </div>
        <div className="mb-6 overflow-hidden rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto min-w-0 max-w-[1200px]">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">Risk Map</h1>
        <p className="mt-1 text-sm text-gray-500 lg:text-base">Geographic distribution of project risks</p>
      </div>

      <div className="mb-6 overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div ref={mapRef} style={{ height: '600px', width: '100%' }} id="risk-map" />
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-6">
          {legendItems.map((item) => (
            <div key={item.label} className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-sm text-gray-600">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
