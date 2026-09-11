import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Maximize, Minimize } from 'lucide-react';
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

const tileProviders: { url: string; options: L.TileLayerOptions }[] = [
  {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    options: {
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics',
    },
  },
  {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    options: {
      attribution: '&copy; OpenStreetMap contributors',
    },
  },
  {
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    options: {
      subdomains: 'abcd',
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    },
  },
];

export default function RiskMap() {
  const mapRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [riskMapData, setRiskMapData] = useState<RiskMapProject[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = () => {
    setIsFullscreen((prev) => !prev);
  };

  const savedViewRef = useRef<{ center: L.LatLng; zoom: number } | null>(null);

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
    if (!mapRef.current || riskMapData.length === 0) return;
    if (mapInstanceRef.current) return;

    const saved = savedViewRef.current;
    const map = saved
      ? L.map(mapRef.current, {
          zoomAnimation: false,
          fadeAnimation: false,
          markerZoomAnimation: false,
        }).setView(saved.center, saved.zoom)
      : L.map(mapRef.current, {
          zoomAnimation: false,
          fadeAnimation: false,
          markerZoomAnimation: false,
        }).setView([20.5937, 78.9629], 5);

    let providerIndex = 0;
    let tileLayer: L.TileLayer | null = null;
    let errorCount = 0;
    let failoverTimer: ReturnType<typeof setTimeout> | null = null;

    const addTileLayer = () => {
      const provider = tileProviders[providerIndex % tileProviders.length];
      tileLayer = L.tileLayer(provider.url, {
        maxZoom: 19,
        updateWhenZooming: false,
        updateWhenIdle: true,
        keepBuffer: 3,
        ...provider.options,
      }).addTo(map);

      tileLayer.on('tileerror', () => {
        errorCount += 1;
        if (errorCount >= 5 && !failoverTimer) {
          errorCount = 0;
          failoverTimer = setTimeout(() => {
            failoverTimer = null;
            tileLayer?.remove();
            providerIndex = (providerIndex + 1) % tileProviders.length;
            addTileLayer();
          }, 400);
        }
      });
      tileLayer.on('tileload', () => {
        errorCount = 0;
      });
    };
    addTileLayer();

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
      savedViewRef.current = { center: map.getCenter(), zoom: map.getZoom() };
      if (failoverTimer) clearTimeout(failoverTimer);
      tileLayer?.remove();
      map.remove();
      mapInstanceRef.current = null;
    };
  }, [riskMapData, projects, navigate, isFullscreen]);

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

      <div
        ref={wrapperRef}
        className={`overflow-hidden bg-white shadow-sm ${
          isFullscreen
            ? 'fixed inset-0 z-[9999] rounded-none border-0'
            : 'relative z-0 mb-6 rounded-xl border border-gray-300'
        }`}
      >
        <button
          type="button"
          onClick={toggleFullscreen}
          aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          className="absolute right-4 top-4 z-[10000] flex h-9 w-9 items-center justify-center rounded-lg bg-white text-navy-900 shadow-md ring-1 ring-gray-200 transition-colors hover:bg-gray-100"
        >
          {isFullscreen ? <Minimize size={16} /> : <Maximize size={16} />}
        </button>
        <div
          ref={mapRef}
          id="risk-map"
          className={isFullscreen ? 'h-full w-full' : 'h-[600px] w-full'}
        />
      </div>

      <div className="relative z-20 rounded-xl border border-gray-200 bg-white p-4">
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
