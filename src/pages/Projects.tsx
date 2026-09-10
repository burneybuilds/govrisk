import { useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { LayoutGrid, Table as TableIcon } from 'lucide-react';
import { mockProjects } from '../data/projects';
import type { Project } from '../types';
import { SearchBar } from '../components/ui/SearchBar';
import { FilterBar, FilterSelect } from '../components/ui/FilterBar';
import { ProjectTable } from '../components/project/ProjectTable';
import { ProjectCard } from '../components/project/ProjectCard';
import { EmptyState } from '../components/ui/EmptyState';
import { FolderSearch } from 'lucide-react';

type ViewMode = 'table' | 'cards';

export default function Projects() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [sectorFilter, setSectorFilter] = useState('All');
  const [riskFilter, setRiskFilter] = useState('All');
  const [stateFilter, setStateFilter] = useState('All');
  const [ministryFilter, setMinistryFilter] = useState('All');
  const [viewMode, setViewMode] = useState<ViewMode>('table');

  const sectors = useMemo(() => {
    const unique = Array.from(new Set(mockProjects.map((p) => p.sector)));
    return unique.sort();
  }, []);

  const states = useMemo(() => {
    const unique = Array.from(new Set(mockProjects.map((p) => p.state)));
    return unique.sort();
  }, []);

  const ministries = useMemo(() => {
    const unique = Array.from(new Set(mockProjects.map((p) => p.ministry)));
    return unique.sort();
  }, []);

  const filteredProjects = useMemo(() => {
    return mockProjects.filter((project: Project) => {
      if (search) {
        const q = search.toLowerCase();
        const matchesSearch =
          project.name.toLowerCase().includes(q) ||
          project.ministry.toLowerCase().includes(q) ||
          project.state.toLowerCase().includes(q) ||
          project.id.toLowerCase().includes(q);
        if (!matchesSearch) return false;
      }
      if (sectorFilter !== 'All' && project.sector !== sectorFilter) return false;
      if (riskFilter !== 'All' && project.riskLevel !== riskFilter) return false;
      if (stateFilter !== 'All' && project.state !== stateFilter) return false;
      if (ministryFilter !== 'All' && project.ministry !== ministryFilter) return false;
      return true;
    });
  }, [search, sectorFilter, riskFilter, stateFilter, ministryFilter]);

  const sortedByRisk = useMemo(() => {
    return [...filteredProjects].sort((a, b) => b.riskScore - a.riskScore);
  }, [filteredProjects]);

  return (
    <div className="min-w-0">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">Infrastructure Projects</h1>
          <p className="mt-1 text-sm text-gray-500 lg:text-base">
            Monitor project performance, cost, progress and risk.
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white p-1">
          <button
            onClick={() => setViewMode('table')}
            className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              viewMode === 'table' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <TableIcon size={14} />
            Table
          </button>
          <button
            onClick={() => setViewMode('cards')}
            className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              viewMode === 'cards' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <LayoutGrid size={14} />
            Cards
          </button>
        </div>
      </div>

      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-4 lg:p-5">
        <FilterBar>
          <div className="w-full sm:w-72">
            <SearchBar
              value={search}
              onChange={setSearch}
              placeholder="Search projects..."
            />
          </div>
          <FilterSelect
            label="Sector"
            value={sectorFilter}
            onChange={setSectorFilter}
            options={[
              { value: 'All', label: 'All Sectors' },
              ...sectors.map((s) => ({ value: s, label: s })),
            ]}
          />
          <FilterSelect
            label="Risk Level"
            value={riskFilter}
            onChange={setRiskFilter}
            options={[
              { value: 'All', label: 'All' },
              { value: 'LOW', label: 'LOW' },
              { value: 'MEDIUM', label: 'MEDIUM' },
              { value: 'HIGH', label: 'HIGH' },
              { value: 'CRITICAL', label: 'CRITICAL' },
            ]}
          />
          <FilterSelect
            label="State"
            value={stateFilter}
            onChange={setStateFilter}
            options={[
              { value: 'All', label: 'All States' },
              ...states.map((s) => ({ value: s, label: s })),
            ]}
          />
          <FilterSelect
            label="Ministry"
            value={ministryFilter}
            onChange={setMinistryFilter}
            options={[
              { value: 'All', label: 'All Ministries' },
              ...ministries.map((m) => ({ value: m, label: m })),
            ]}
          />
        </FilterBar>
      </div>

      <p className="mb-4 text-sm text-gray-500">
        Showing {filteredProjects.length} of {mockProjects.length} projects
      </p>

      {filteredProjects.length === 0 ? (
        <EmptyState
          title="No projects found"
          description="Try adjusting your search query or clearing some filters."
          icon={<FolderSearch size={40} />}
        />
      ) : viewMode === 'table' ? (
        <ProjectTable
          projects={filteredProjects}
          showPagination={true}
          pageSize={12}
          onRowClick={(project) => navigate(`/projects/${project.id}`)}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {sortedByRisk.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </div>
  );
}