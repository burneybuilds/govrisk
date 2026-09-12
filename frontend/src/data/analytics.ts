import { SectorAnalytics, MinistryRanking, ScatterPoint, RiskTrend } from '../types';

export const sectorAnalytics: SectorAnalytics[] = [
  {
    sector: 'Transport',
    avgRisk: 74,
    projectCount: 5,
    avgCostOverrun: 18.3,
    avgDelay: 9.2,
  },
  {
    sector: 'Energy',
    avgRisk: 68,
    projectCount: 4,
    avgCostOverrun: 14.7,
    avgDelay: 7.5,
  },
  {
    sector: 'Water',
    avgRisk: 61,
    projectCount: 3,
    avgCostOverrun: 11.2,
    avgDelay: 5.8,
  },
  {
    sector: 'Communication',
    avgRisk: 55,
    projectCount: 3,
    avgCostOverrun: 8.6,
    avgDelay: 4.1,
  },
  {
    sector: 'Mining',
    avgRisk: 79,
    projectCount: 1,
    avgCostOverrun: 22.1,
    avgDelay: 11.3,
  },
  {
    sector: 'Social Infrastructure',
    avgRisk: 63,
    projectCount: 2,
    avgCostOverrun: 12.4,
    avgDelay: 6.7,
  },
];

export const ministryRankings: MinistryRanking[] = [
  {
    rank: 1,
    ministry: 'Ministry of Mining & Minerals',
    projectCount: 1,
    avgRisk: 79,
    highRiskCount: 1,
  },
  {
    rank: 2,
    ministry: 'Ministry of Transport & Infrastructure',
    projectCount: 3,
    avgRisk: 76,
    highRiskCount: 2,
  },
  {
    rank: 3,
    ministry: 'Ministry of Energy & Power',
    projectCount: 3,
    avgRisk: 71,
    highRiskCount: 2,
  },
  {
    rank: 4,
    ministry: 'Ministry of Water Resources',
    projectCount: 2,
    avgRisk: 67,
    highRiskCount: 1,
  },
  {
    rank: 5,
    ministry: 'Ministry of Health & Family Welfare',
    projectCount: 1,
    avgRisk: 64,
    highRiskCount: 1,
  },
  {
    rank: 6,
    ministry: 'Ministry of Education',
    projectCount: 1,
    avgRisk: 62,
    highRiskCount: 0,
  },
  {
    rank: 7,
    ministry: 'Ministry of Communications',
    projectCount: 2,
    avgRisk: 58,
    highRiskCount: 1,
  },
  {
    rank: 8,
    ministry: 'Ministry of Rural Development',
    projectCount: 1,
    avgRisk: 53,
    highRiskCount: 0,
  },
  {
    rank: 9,
    ministry: 'Ministry of Urban Development',
    projectCount: 2,
    avgRisk: 49,
    highRiskCount: 1,
  },
  {
    rank: 10,
    ministry: 'Ministry of Electronics & IT',
    projectCount: 2,
    avgRisk: 45,
    highRiskCount: 0,
  },
];

export const scatterData: ScatterPoint[] = [
  { name: 'River Basin Development', physicalProgress: 32, costOverrun: 24, sector: 'Water' },
  { name: 'National Highway Dev', physicalProgress: 58, costOverrun: 18, sector: 'Transport' },
  { name: 'Irrigation Canal Upgrade', physicalProgress: 41, costOverrun: 12, sector: 'Water' },
  {
    name: 'Coastal Port Modernization',
    physicalProgress: 67,
    costOverrun: 15,
    sector: 'Transport',
  },
  { name: 'Solar Energy Grid', physicalProgress: 73, costOverrun: 9, sector: 'Energy' },
  {
    name: 'Airport Terminal Expansion',
    physicalProgress: 54,
    costOverrun: 21,
    sector: 'Transport',
  },
  { name: 'Broadband Connectivity', physicalProgress: 82, costOverrun: 7, sector: 'Communication' },
  { name: 'Wind Farm Installation', physicalProgress: 88, costOverrun: 5, sector: 'Energy' },
  { name: 'Urban Metro Rail Phase II', physicalProgress: 38, costOverrun: 28, sector: 'Transport' },
  { name: 'Telecom Tower Network', physicalProgress: 76, costOverrun: 8, sector: 'Communication' },
  { name: 'Thermal Power Expansion', physicalProgress: 61, costOverrun: 22, sector: 'Energy' },
  { name: 'Hydropower Dam Rehab', physicalProgress: 47, costOverrun: 14, sector: 'Energy' },
  {
    name: 'Mining Infrastructure Corridor',
    physicalProgress: 28,
    costOverrun: 32,
    sector: 'Mining',
  },
  { name: 'Water Treatment Upgrade', physicalProgress: 69, costOverrun: 11, sector: 'Water' },
  {
    name: 'Hospital Construction',
    physicalProgress: 52,
    costOverrun: 16,
    sector: 'Social Infrastructure',
  },
  { name: 'Fiber Optic Backbone', physicalProgress: 85, costOverrun: 6, sector: 'Communication' },
  {
    name: 'School Construction Program',
    physicalProgress: 44,
    costOverrun: 13,
    sector: 'Social Infrastructure',
  },
  { name: 'Bridge Reconstruction', physicalProgress: 35, costOverrun: 19, sector: 'Transport' },
  { name: 'Waste Management Network', physicalProgress: 91, costOverrun: 4, sector: 'Water' },
  { name: 'Smart Grid Pilot', physicalProgress: 78, costOverrun: 10, sector: 'Energy' },
];

export const riskTrends: RiskTrend[] = [
  { month: 'Apr 2025', low: 4, medium: 6, high: 5, critical: 3, overall: 62.4 },
  { month: 'May 2025', low: 3, medium: 7, high: 5, critical: 3, overall: 63.1 },
  { month: 'Jun 2025', low: 3, medium: 6, high: 6, critical: 3, overall: 64.8 },
  { month: 'Jul 2025', low: 2, medium: 6, high: 6, critical: 4, overall: 66.2 },
  { month: 'Aug 2025', low: 2, medium: 5, high: 7, critical: 4, overall: 67.5 },
  { month: 'Sep 2025', low: 2, medium: 5, high: 7, critical: 4, overall: 68.1 },
];

export const costPredictionData = [
  { name: 'Original Cost', value: 4800 },
  { name: 'Current Cost', value: 5822 },
  { name: 'Predicted Final Cost', value: 6172 },
];

export const riskDriverData = [
  { name: 'Physical Progress Gap', value: 87 },
  { name: 'Milestone Delays', value: 81 },
  { name: 'Cost Escalation', value: 73 },
  { name: 'Expenditure Variance', value: 64 },
  { name: 'Historical Sector Risk', value: 58 },
];
