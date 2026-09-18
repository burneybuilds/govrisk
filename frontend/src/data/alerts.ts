import { Alert } from '../types';

export const mockAlerts: Alert[] = [
  {
    id: 'ALR-001',
    projectId: 'PRJ-001',
    projectName: 'River Basin Development Project',
    type: 'Schedule Delay Risk',
    severity: 'CRITICAL',
    detectedDate: '2025-09-02',
    description:
      'River Basin Development Project has an estimated 88% probability of schedule delay due to prolonged land acquisition delays.',
  },
  {
    id: 'ALR-002',
    projectId: 'PRJ-005',
    projectName: 'National Highway Development Project',
    type: 'Cost Escalation',
    severity: 'CRITICAL',
    detectedDate: '2025-08-18',
    description:
      'National Highway Development Project shows a significant upward cost trend with 18.4% overrun detected.',
  },
  {
    id: 'ALR-003',
    projectId: 'PRJ-012',
    projectName: 'Thermal Power Plant Expansion',
    type: 'Budget Overrun Alert',
    severity: 'CRITICAL',
    detectedDate: '2025-10-05',
    description:
      'Thermal Power Plant Expansion has exhausted 92% of its budget with only 61% physical progress achieved.',
  },
  {
    id: 'ALR-004',
    projectId: 'PRJ-009',
    projectName: 'Urban Metro Rail Phase II',
    type: 'Implementation Bottleneck',
    severity: 'CRITICAL',
    detectedDate: '2025-07-30',
    description:
      'Urban Metro Rail Phase II faces critical structural bottlenecks with 14 out of 22 milestones delayed by over 90 days.',
  },
  {
    id: 'ALR-005',
    projectId: 'PRJ-003',
    projectName: 'Irrigation Canal Network Upgrade',
    type: 'Progress Variance',
    severity: 'HIGH',
    detectedDate: '2025-11-12',
    description:
      'Irrigation Canal Network Upgrade shows a 24% gap between planned and actual physical progress.',
  },
  {
    id: 'ALR-006',
    projectId: 'PRJ-007',
    projectName: 'Broadband Connectivity Expansion',
    type: 'Milestone Delay',
    severity: 'HIGH',
    detectedDate: '2025-06-22',
    description:
      'Broadband Connectivity Expansion has 6 critical milestones overdue impacting the Q4 2025 delivery target.',
  },
  {
    id: 'ALR-007',
    projectId: 'PRJ-014',
    projectName: 'Mining Infrastructure Corridor',
    type: 'Cost Escalation',
    severity: 'HIGH',
    detectedDate: '2025-12-01',
    description:
      'Mining Infrastructure Corridor is projected to exceed original cost estimates by 15.7% based on current expenditure trajectory.',
  },
  {
    id: 'ALR-008',
    projectId: 'PRJ-016',
    projectName: 'Rural School Construction Program',
    type: 'Schedule Delay Risk',
    severity: 'HIGH',
    detectedDate: '2025-08-09',
    description:
      'Rural School Construction Program delay probability has risen to 79% following contractor mobilization issues in 3 districts.',
  },
  {
    id: 'ALR-009',
    projectId: 'PRJ-002',
    projectName: 'Coastal Port Modernization',
    type: 'Budget Overrun Alert',
    severity: 'HIGH',
    detectedDate: '2026-01-14',
    description:
      'Coastal Port Modernization expenditure is running 11.2% ahead of schedule with revised cost projections indicating further escalation.',
  },
  {
    id: 'ALR-010',
    projectId: 'PRJ-006',
    projectName: 'Solar Energy Grid Integration',
    type: 'Progress Variance',
    severity: 'MEDIUM',
    detectedDate: '2025-07-15',
    description:
      'Solar Energy Grid Integration physical progress is 8% below planned milestones for the current reporting period.',
  },
  {
    id: 'ALR-011',
    projectId: 'PRJ-010',
    projectName: 'Telecommunications Tower Network',
    type: 'Milestone Delay',
    severity: 'MEDIUM',
    detectedDate: '2025-09-28',
    description:
      'Telecommunications Tower Network has 3 secondary milestones delayed by 30-45 days due to spectrum allocation delays.',
  },
  {
    id: 'ALR-012',
    projectId: 'PRJ-013',
    projectName: 'Hydropower Dam Rehabilitation',
    type: 'Implementation Bottleneck',
    severity: 'MEDIUM',
    detectedDate: '2025-10-20',
    description:
      'Hydropower Dam Rehabilitation procurement cycle is causing a 6-week lag in equipment delivery for Phase 2 works.',
  },
  {
    id: 'ALR-013',
    projectId: 'PRJ-004',
    projectName: 'Airport Terminal Expansion',
    type: 'Schedule Delay Risk',
    severity: 'MEDIUM',
    detectedDate: '2026-02-03',
    description:
      'Airport Terminal Expansion delay probability has increased to 62% following revised air traffic projections.',
  },
  {
    id: 'ALR-014',
    projectId: 'PRJ-011',
    projectName: 'Water Treatment Facility Upgrade',
    type: 'Cost Escalation',
    severity: 'MEDIUM',
    detectedDate: '2025-11-30',
    description:
      'Water Treatment Facility Upgrade raw material costs have risen 9.3% above baseline estimates in the last quarter.',
  },
  {
    id: 'ALR-015',
    projectId: 'PRJ-018',
    projectName: 'Highway Bridge Reconstruction',
    type: 'Progress Variance',
    severity: 'MEDIUM',
    detectedDate: '2026-03-11',
    description:
      'Highway Bridge Reconstruction shows a 12% variance between planned and achieved physical progress across 4 of 7 segments.',
  },
  {
    id: 'ALR-016',
    projectId: 'PRJ-008',
    projectName: 'Wind Farm Installation Project',
    type: 'Milestone Delay',
    severity: 'RESOLVED',
    detectedDate: '2025-05-18',
    description:
      'Wind Farm Installation Project turbine delivery milestone delay has been resolved with revised logistics arrangements.',
  },
  {
    id: 'ALR-017',
    projectId: 'PRJ-015',
    projectName: 'National Fiber Optic Backbone',
    type: 'Budget Overrun Alert',
    severity: 'RESOLVED',
    detectedDate: '2025-04-25',
    description:
      'National Fiber Optic Backbone budget overrun alert resolved after successful renegotiation of right-of-way agreements.',
  },
  {
    id: 'ALR-018',
    projectId: 'PRJ-017',
    projectName: 'Regional Hospital Construction',
    type: 'Schedule Delay Risk',
    severity: 'RESOLVED',
    detectedDate: '2025-06-10',
    description:
      'Regional Hospital Construction schedule delay risk was mitigated after additional workforce was deployed to critical path activities.',
  },
];
