export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type Sector = 'Transport' | 'Energy' | 'Water' | 'Communication' | 'Mining' | 'Social Infrastructure';

export type AlertSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'RESOLVED';

export interface Project {
  id: string;
  name: string;
  ministry: string;
  sector: Sector;
  state: string;
  agency: string;
  originalCost: number;
  currentCost: number;
  expenditure: number;
  physicalProgress: number;
  plannedProgress: number;
  startDate: string;
  expectedCompletion: string;
  predictedCompletion: string;
  costOverrunProbability: number;
  delayProbability: number;
  implementationRisk: number;
  riskScore: number;
  riskLevel: RiskLevel;
  milestonesTotal: number;
  milestonesDelayed: number;
  lat: number;
  lng: number;
  riskFactors: string[];
  recommendations: string[];
}

export interface Alert {
  id: string;
  projectId: string;
  projectName: string;
  type: string;
  severity: AlertSeverity;
  detectedDate: string;
  description: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface SectorAnalytics {
  sector: string;
  avgRisk: number;
  projectCount: number;
  avgCostOverrun: number;
  avgDelay: number;
}

export interface MinistryRanking {
  rank: number;
  ministry: string;
  projectCount: number;
  avgRisk: number;
  highRiskCount: number;
}

export interface ScatterPoint {
  name: string;
  physicalProgress: number;
  costOverrun: number;
  sector: string;
}

export interface RiskTrend {
  month: string;
  low: number;
  medium: number;
  high: number;
  critical: number;
  overall: number;
}
