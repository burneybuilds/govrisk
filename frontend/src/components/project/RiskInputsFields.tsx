import { ShieldAlert, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { RiskInputs } from '../../types';

const inputClass =
  'h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20';

function Group({
  title,
  defaultOpen,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(!!defaultOpen);
  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="rounded-lg border border-gray-200 bg-gray-50/50"
    >
      <summary className="flex cursor-pointer list-none items-center justify-between px-3.5 py-2.5 text-sm font-medium text-gray-700">
        <span>{title}</span>
        <ChevronDown
          className={`h-4 w-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </summary>
      <div className="grid grid-cols-1 gap-3 px-3.5 pb-3.5 pt-1 sm:grid-cols-2 lg:grid-cols-3">
        {children}
      </div>
    </details>
  );
}

function Labeled({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-500">{label}</label>
      {children}
    </div>
  );
}

function Select({
  value,
  options,
  placeholder,
  onChange,
}: {
  value: string | undefined;
  options: string[];
  placeholder?: string;
  onChange: (v: string) => void;
}) {
  return (
    <select value={value || ''} onChange={(e) => onChange(e.target.value)} className={inputClass}>
      <option value="">{placeholder || 'Not provided'}</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o.replace(/_/g, ' ')}
        </option>
      ))}
    </select>
  );
}

function NumberInput({
  value,
  placeholder,
  onChange,
}: {
  value: number | string | undefined;
  placeholder?: string;
  onChange: (v: string) => void;
}) {
  return (
    <input
      type="number"
      inputMode="decimal"
      value={value === undefined || value === null ? '' : String(value)}
      placeholder={placeholder || 'Not provided'}
      onChange={(e) => onChange(e.target.value)}
      className={inputClass}
    />
  );
}

function BoolInput({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex h-10 items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-600">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-gray-300 text-blue-600"
      />
      {label}
    </label>
  );
}

const asNum = (v: string | undefined): number | undefined => {
  if (v === undefined || isNaN(Number(v)) || String(v).trim() === '') return undefined;
  return Number(v);
};

const clean = (group: Record<string, any>): Record<string, any> | undefined => {
  const out: Record<string, any> = {};
  for (const [k, v] of Object.entries(group || {})) {
    if (v === undefined || v === null) continue;
    if (typeof v === 'string' && v.trim() === '') continue;
    if (typeof v === 'number' && isNaN(v)) continue;
    out[k] = v;
  }
  return Object.keys(out).length ? out : undefined;
};

export default function RiskInputsFields({
  value,
  onChange,
}: {
  value: RiskInputs;
  onChange: (v: RiskInputs) => void;
}) {
  const setGroup = (group: keyof RiskInputs, patch: Record<string, any>) => {
    const current = { ...((value as any)[group] || {}) };
    for (const [k, v] of Object.entries(patch)) {
      if (v === undefined) delete current[k];
      else current[k] = v;
    }
    const cleaned = clean(current);
    const next = { ...value } as any;
    if (cleaned) next[group] = cleaned;
    else delete next[group];
    onChange(next as RiskInputs);
  };

  const g = (group: keyof RiskInputs): Record<string, any> => (value as any)?.[group] || {};

  return (
    <div className="space-y-2.5">
      <div className="flex items-start gap-2 text-xs text-gray-500">
        <ShieldAlert className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-500" />
        <p>
          Optional on-the-ground inputs. Leave groups blank to use neutral baselines (lower
          confidence). The backend engine derives the rest from core fields.
        </p>
      </div>

      <Group title="Weather & Seasons" defaultOpen>
        <Labeled label="Current weather condition">
          <Select
            value={g('weather').condition}
            options={['CLEAR', 'MILD', 'UNFAVOURABLE', 'SEVERE']}
            onChange={(v) => setGroup('weather', { condition: v || undefined })}
          />
        </Labeled>
        <Labeled label="Disruption level">
          <Select
            value={g('weather').disruption}
            options={['LOW', 'MODERATE', 'HIGH', 'CRITICAL']}
            onChange={(v) => setGroup('weather', { disruption: v || undefined })}
          />
        </Labeled>
        <Labeled label="Working days lost (approx.)">
          <NumberInput
            value={g('weather').workingDaysLost}
            placeholder="Days"
            onChange={(v) => setGroup('weather', { workingDaysLost: asNum(v) })}
          />
        </Labeled>
      </Group>

      <Group title="Ground & Geological Conditions">
        <Labeled label="Ground condition">
          <Select
            value={g('ground').condition}
            options={['FAVOURABLE', 'MODERATE', 'DIFFICULT', 'SEVERE']}
            onChange={(v) => setGroup('ground', { condition: v || undefined })}
          />
        </Labeled>
        <Labeled label="Rock excavation">
          <Select
            value={g('ground').rockExcavation}
            options={['NONE', 'LIGHT', 'MODERATE', 'EXTENSIVE']}
            onChange={(v) => setGroup('ground', { rockExcavation: v || undefined })}
          />
        </Labeled>
        <Labeled label="Groundwater">
          <Select
            value={g('ground').groundwater}
            options={['LOW', 'MODERATE', 'HIGH']}
            onChange={(v) => setGroup('ground', { groundwater: v || undefined })}
          />
        </Labeled>
        <Labeled label="Landslide potential">
          <Select
            value={g('ground').landslidePotential}
            options={['LOW', 'MODERATE', 'HIGH']}
            onChange={(v) => setGroup('ground', { landslidePotential: v || undefined })}
          />
        </Labeled>
      </Group>

      <Group title="Natural Calamity Exposure">
        {(
          [
            'floodExposure',
            'earthquakeExposure',
            'cycloneExposure',
            'landslideExposure',
            'droughtExposure',
          ] as const
        ).map((key) => (
          <Labeled key={key} label={key.replace('Exposure', '').replace('Le', 'le') + ' exposure'}>
            <Select
              value={g('calamity')[key]}
              options={['LOW', 'MODERATE', 'HIGH']}
              onChange={(v) => setGroup('calamity', { [key]: v || undefined })}
            />
          </Labeled>
        ))}
      </Group>

      <Group title="Material & Supply">
        <Labeled label="Material availability">
          <Select
            value={g('material').availability}
            options={['ADEQUATE', 'TIGHT', 'SHORTAGE', 'SEVERE_SHORTAGE']}
            onChange={(v) => setGroup('material', { availability: v || undefined })}
          />
        </Labeled>
        <Labeled label="Price increase (%)">
          <NumberInput
            value={g('material').priceIncreasePct}
            placeholder="e.g. 8"
            onChange={(v) => setGroup('material', { priceIncreasePct: asNum(v) })}
          />
        </Labeled>
        <Labeled label="Quality inspection failures">
          <NumberInput
            value={g('material').qualityIssues}
            placeholder="Count"
            onChange={(v) => setGroup('material', { qualityIssues: asNum(v) })}
          />
        </Labeled>
        <BoolInput
          checked={!!g('material').criticalMaterial}
          label="Critical material at risk"
          onChange={(v) => setGroup('material', { criticalMaterial: v })}
        />
      </Group>

      <Group title="Workforce">
        <Labeled label="Overall availability">
          <Select
            value={g('workforce').availability}
            options={['ADEQUATE', 'SHORTAGE', 'SEVERE_SHORTAGE']}
            onChange={(v) => setGroup('workforce', { availability: v || undefined })}
          />
        </Labeled>
        <Labeled label="Skilled labour availability">
          <Select
            value={g('workforce').skilledAvailability}
            options={['ADEQUATE', 'SHORTAGE', 'SEVERE_SHORTAGE']}
            onChange={(v) => setGroup('workforce', { skilledAvailability: v || undefined })}
          />
        </Labeled>
        <Labeled label="Productivity">
          <Select
            value={g('workforce').productivity}
            options={['HIGH', 'NORMAL', 'LOW', 'VERY_LOW']}
            onChange={(v) => setGroup('workforce', { productivity: v || undefined })}
          />
        </Labeled>
        <Labeled label="Turnover (%)">
          <NumberInput
            value={g('workforce').turnoverPct}
            placeholder="e.g. 5"
            onChange={(v) => setGroup('workforce', { turnoverPct: asNum(v) })}
          />
        </Labeled>
      </Group>

      <Group title="Contractor Performance">
        <Labeled label="Performance">
          <Select
            value={g('contractor').performance}
            options={['EXCELLENT', 'GOOD', 'FAIR', 'POOR', 'CRITICAL']}
            onChange={(v) => setGroup('contractor', { performance: v || undefined })}
          />
        </Labeled>
        <Labeled label="Delayed milestones">
          <NumberInput
            value={g('contractor').delayedMilestoneCount}
            placeholder="Count"
            onChange={(v) => setGroup('contractor', { delayedMilestoneCount: asNum(v) })}
          />
        </Labeled>
        <Labeled label="Financial stress">
          <Select
            value={g('contractor').financialStress}
            options={['NONE', 'MODERATE', 'HIGH']}
            onChange={(v) => setGroup('contractor', { financialStress: v || undefined })}
          />
        </Labeled>
        <Labeled label="Unresolved issues">
          <NumberInput
            value={g('contractor').unresolvedIssueCount}
            placeholder="Count"
            onChange={(v) => setGroup('contractor', { unresolvedIssueCount: asNum(v) })}
          />
        </Labeled>
      </Group>

      <Group title="Engineering & Design">
        <Labeled label="Rework level">
          <Select
            value={g('engineering').reworkLevel}
            options={['NONE', 'LOW', 'MODERATE', 'HIGH']}
            onChange={(v) => setGroup('engineering', { reworkLevel: v || undefined })}
          />
        </Labeled>
        <Labeled label="Technical complexity">
          <Select
            value={g('engineering').technicalComplexity}
            options={['LOW', 'MODERATE', 'HIGH']}
            onChange={(v) => setGroup('engineering', { technicalComplexity: v || undefined })}
          />
        </Labeled>
        <Labeled label="Design changes">
          <NumberInput
            value={g('engineering').designChangeCount}
            placeholder="Count"
            onChange={(v) => setGroup('engineering', { designChangeCount: asNum(v) })}
          />
        </Labeled>
        <Labeled label="Design errors found">
          <NumberInput
            value={g('engineering').designErrorCount}
            placeholder="Count"
            onChange={(v) => setGroup('engineering', { designErrorCount: asNum(v) })}
          />
        </Labeled>
        <BoolInput
          checked={!!g('engineering').approvalPending}
          label="Design approval pending"
          onChange={(v) => setGroup('engineering', { approvalPending: v })}
        />
      </Group>

      <Group title="Land & Clearances">
        <Labeled label="Land acquired (%)">
          <NumberInput
            value={g('clearance').landAcquiredPct}
            placeholder="0 - 100"
            onChange={(v) => setGroup('clearance', { landAcquiredPct: asNum(v) })}
          />
        </Labeled>
        <Labeled label="Environmental clearance">
          <Select
            value={g('clearance').environmentalClearance}
            options={['CLEARED', 'NOT_REQUIRED', 'PENDING', 'REJECTED']}
            onChange={(v) => setGroup('clearance', { environmentalClearance: v || undefined })}
          />
        </Labeled>
        <Labeled label="Forest clearance">
          <Select
            value={g('clearance').forestClearance}
            options={['CLEARED', 'NOT_REQUIRED', 'PENDING']}
            onChange={(v) => setGroup('clearance', { forestClearance: v || undefined })}
          />
        </Labeled>
        <BoolInput
          checked={!!g('clearance').rehabilitationPending}
          label="Rehabilitation pending"
          onChange={(v) => setGroup('clearance', { rehabilitationPending: v })}
        />
      </Group>

      <Group title="Government & Administrative">
        <Labeled label="Approval turnaround">
          <Select
            value={g('administrative').turnaround}
            options={['FAST', 'NORMAL', 'SLOW', 'BLOCKED']}
            onChange={(v) => setGroup('administrative', { turnaround: v || undefined })}
          />
        </Labeled>
        <Labeled label="Pending approvals">
          <NumberInput
            value={g('administrative').pendingApprovalCount}
            placeholder="Count"
            onChange={(v) => setGroup('administrative', { pendingApprovalCount: asNum(v) })}
          />
        </Labeled>
        <Labeled label="Inter-department dependency">
          <Select
            value={g('administrative').interDepartmentDependency}
            options={['LOW', 'MODERATE', 'HIGH']}
            onChange={(v) =>
              setGroup('administrative', { interDepartmentDependency: v || undefined })
            }
          />
        </Labeled>
        <BoolInput
          checked={!!g('administrative').procurementDelay}
          label="Procurement delayed"
          onChange={(v) => setGroup('administrative', { procurementDelay: v })}
        />
      </Group>

      <Group title="Supply Chain & Logistics">
        <Labeled label="Site accessibility">
          <Select
            value={g('supplyChain').accessibility}
            options={['GOOD', 'MODERATE', 'POOR', 'REMOTE']}
            onChange={(v) => setGroup('supplyChain', { accessibility: v || undefined })}
          />
        </Labeled>
        <Labeled label="Supplier dependency">
          <Select
            value={g('supplyChain').supplierDependency}
            options={['LOW', 'MODERATE', 'HIGH']}
            onChange={(v) => setGroup('supplyChain', { supplierDependency: v || undefined })}
          />
        </Labeled>
        <Labeled label="Equipment availability">
          <Select
            value={g('supplyChain').equipmentAvailability}
            options={['ADEQUATE', 'TIGHT', 'SHORTAGE']}
            onChange={(v) => setGroup('supplyChain', { equipmentAvailability: v || undefined })}
          />
        </Labeled>
        <Labeled label="Delivery delays observed">
          <NumberInput
            value={g('supplyChain').deliveryDelayCount}
            placeholder="Count"
            onChange={(v) => setGroup('supplyChain', { deliveryDelayCount: asNum(v) })}
          />
        </Labeled>
        <BoolInput
          checked={!!g('supplyChain').importDependency}
          label="Relies on critical imports"
          onChange={(v) => setGroup('supplyChain', { importDependency: v })}
        />
      </Group>

      <Group title="Legal & Social">
        <Labeled label="Local opposition">
          <Select
            value={g('legalSocial').oppositionLevel}
            options={['NONE', 'LOW', 'MODERATE', 'HIGH']}
            onChange={(v) => setGroup('legalSocial', { oppositionLevel: v || undefined })}
          />
        </Labeled>
        <Labeled label="Active disputes">
          <NumberInput
            value={g('legalSocial').activeDisputeCount}
            placeholder="Count"
            onChange={(v) => setGroup('legalSocial', { activeDisputeCount: asNum(v) })}
          />
        </Labeled>
        <Labeled label="Unresolved compensation (cases)">
          <NumberInput
            value={g('legalSocial').unresolvedCompensation}
            placeholder="Count"
            onChange={(v) => setGroup('legalSocial', { unresolvedCompensation: asNum(v) })}
          />
        </Labeled>
        <BoolInput
          checked={!!g('legalSocial').courtStay}
          label="Court stay in effect"
          onChange={(v) => setGroup('legalSocial', { courtStay: v })}
        />
      </Group>
    </div>
  );
}
