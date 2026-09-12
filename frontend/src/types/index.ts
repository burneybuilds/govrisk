export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type Sector =
  'Transport' | 'Energy' | 'Water' | 'Communication' | 'Mining' | 'Social Infrastructure';

export type AlertSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'RESOLVED';

export interface RiskInputs {
  weather?: Record<string, any>;
  ground?: Record<string, any>;
  calamity?: Record<string, any>;
  material?: Record<string, any>;
  workforce?: Record<string, any>;
  contractor?: Record<string, any>;
  engineering?: Record<string, any>;
  clearance?: Record<string, any>;
  administrative?: Record<string, any>;
  supplyChain?: Record<string, any>;
  legalSocial?: Record<string, any>;
}

export interface RiskFactor {
  key: string;
  name: string;
  score: number;
  weight: number;
  contribution: number;
  probability: number;
  impact: number;
  severity: string;
  reason: string;
  dataAvailable: boolean;
}

export interface RiskInteraction {
  key: string;
  name: string;
  penalty: number;
  reason: string;
}

export interface RiskAssessment {
  projectId: string;
  riskScore: number;
  riskLevel: RiskLevel;
  confidence: number;
  dataCompleteness: number;
  criticalBlocker: boolean;
  criticalBlockerReasons: string[];
  factors: RiskFactor[];
  interactions: RiskInteraction[];
  topRisks: string[];
  recommendations: string[];
  explanations: string[];
  missingData: string[];
  riskTrend?: { available: boolean; note?: string };
  costOverrunProbability: number;
  delayProbability: number;
  implementationRisk: number;
  calculatedAt?: string;
}

export interface Project {
  id: string;
  name: string;
  ministry: string;
  sector: Sector;
  state: string;
  agency: string;
  district?: string;
  description?: string;
  nodalOfficer?: string;
  contactInfo?: string;
  originalCost: number;
  currentCost: number;
  expenditure: number;
  physicalProgress: number;
  financialProgress?: number;
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
  riskConfidence?: number;
  criticalBlocker?: boolean;
  riskInputs?: RiskInputs;
  riskReport?: RiskAssessment;
  createdAt?: string;
  updatedAt?: string;
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

export type ProjectUpdateType =
  'GENERAL' | 'PROGRESS' | 'RISK' | 'FINANCIAL' | 'MILESTONE' | 'FIELD_VISIT';

export interface ProjectUpdate {
  id: number;
  projectId: string;
  userId: string;
  userName: string;
  userRole: string;
  updateType: ProjectUpdateType;
  content: string;
  createdAt: string;
  updatedAt: string;
}
