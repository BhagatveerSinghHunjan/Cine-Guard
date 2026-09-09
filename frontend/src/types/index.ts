export type Severity = "critical" | "high" | "medium" | "low";

export type EvidenceLevel = "explicit" | "inferred" | "unknown";

export type RiskCategory =
  | "location"
  | "cast"
  | "schedule"
  | "permit"
  | "brand"
  | "music"
  | "vehicle"
  | "stunt"
  | "vfx"
  | "weather"
  | "equipment"
  | "continuity"
  | "other";

export interface Scene {
  scene_number: number;
  heading: string;
  interior_or_exterior?: string;
  location: string;
  time_of_day: string;
  characters: string[];
  description: string;
  production_requirements: string[];
  evidence_level?: EvidenceLevel;
}

export interface CharacterDetail {
  name: string;
  role?: string | null;
  scenes_present: number[];
  evidence_level?: EvidenceLevel;
}

export interface LocationDetail {
  name: string;
  scenes: number[];
  location_type?: string | null;
  special_requirements: string[];
  evidence_level?: EvidenceLevel;
}

export interface InitialConcern {
  title: string;
  description?: string;
  category?: string;
  scene_numbers?: number[];
  evidence_level?: EvidenceLevel;
  recommendation?: string;
}

export interface ScreenplayAnalysis {
  project_title: string;
  genre?: string | null;
  estimated_complexity?: string;
  scenes: Scene[];
  characters: string[];
  characters_detailed?: CharacterDetail[];
  locations: string[];
  locations_detailed?: LocationDetail[];
  props: string[];
  vehicles: string[];
  brands: string[];
  music: string[];
  stunts: string[];
  vfx_requirements: string[];
  weather_dependencies: string[];
  time_dependencies: string[];
  special_equipment?: string[];
  permits_or_clearances?: string[];
  production_dependencies: string[];
  initial_concerns?: InitialConcern[];
  unknowns?: string[];
}

export interface Risk {
  id: string;
  scene_number?: number | null;
  affected_scenes?: number[];
  category: RiskCategory | string;
  severity: Severity;
  title: string;
  description: string;
  why_it_matters?: string;
  evidence?: string;
  evidence_items?: EvidenceItem[];
  recommendation?: string;
  affected_dependencies?: string[];
  confidence?: "high" | "medium" | "low";
  status?: "open" | "mitigated" | "unknown";
}

export type EvidenceKind = "screenplay" | "research" | "inference";

export interface EvidenceItem {
  kind: EvidenceKind;
  text: string;
  source_title?: string;
  source_domain?: string;
  source_url?: string;
  scene_numbers?: number[];
  query?: string;
  provider?: string;
  retrieved_at?: string;
}

export interface RiskDependency {
  id: string;
  source_risk_id: string;
  target_risk_id: string;
  relationship: "blocks" | "causes" | "affects" | "depends_on";
  impact?: string;
}

export interface ResearchSource {
  title?: string;
  domain?: string;
  url?: string;
  excerpt?: string;
  publish_date?: string | null;
}

export interface ResearchEvidence {
  topic: string;
  provider?: string;
  status?: string;
  summary?: string;
  sources?: ResearchSource[];
  query?: string;
  retrieved_at?: string;
}

export interface PenaltyLine {
  severity: string;
  count: number;
  weight: number;
  penalty: number;
}

export interface ProductionReadiness {
  score: number;
  status: "READY" | "AT RISK" | "HIGH RISK" | "NOT READY";
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  total_risks: number;
  blockers: string[];
  methodology?: string;
  penalty_breakdown?: PenaltyLine[];
}

export interface DemoScreenplay {
  title: string;
  screenplay_text: string;
  is_fictional: boolean;
  note: string;
}

export interface Recommendation {
  id: string;
  priority: number;
  title: string;
  description?: string;
  addresses_risk_ids: string[];
  expected_impact?: string;
  action_type: string;
}

export interface PlanAction {
  id: string;
  recommendation_id: string;
  title: string;
  description?: string;
  affected_scenes: number[];
  affected_risk_ids: string[];
  expected_risk_reduction: number;
  schedule_impact?: string;
}

export interface FixPlan {
  actions: PlanAction[];
  affected_risk_ids: string[];
  projected_readiness: ProductionReadiness;
  remaining_blockers: string[];
  schedule_impact?: string;
  revised_plan?: string;
  improvements?: string[];
}

export interface AnalyzeRequest {
  screenplay_text: string;
  project_title?: string;
  project_id?: string;
}

export interface AnalyzeResponse {
  project_title: string;
  run_id?: string;
  analysis: ScreenplayAnalysis;
  risks: Risk[];
  dependencies?: RiskDependency[];
  recommendations?: Recommendation[];
  research?: ResearchEvidence[];
  readiness?: ProductionReadiness;
  research_notes: string[];
  readiness_score: number;
  risk_counts: Record<string, number>;
  analysis_source?: string;
  extraction_model?: string;
  extraction_warnings?: string[];
}

export interface PlanResponse {
  project_title: string;
  run_id?: string;
  affected_risk_ids: string[];
  projected_readiness: ProductionReadiness;
  current_readiness?: ProductionReadiness;
  fix_plan?: FixPlan | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  api?: string;
  database?: string;
  gemini?: string;
  parallel?: string;
}

export interface RunAccepted {
  run_id: string;
  project_id: string;
  status: string;
}

export interface RunErrorInfo {
  code: string;
  message: string;
  stage?: string;
}

export interface RunEvent {
  seq: number;
  ts: string;
  type: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export interface RunStatus {
  run_id: string;
  project_id?: string;
  project_title?: string;
  status: string;
  current_stage?: string;
  progress?: number;
  attempt?: number;
  started_at?: string;
  completed_at?: string | null;
  error?: RunErrorInfo | null;
  has_results?: boolean;
  events?: RunEvent[];
  result?: AnalyzeResponse | null;
}

export interface Project {
  id: string;
  name: string;
  created_at?: string;
  updated_at?: string;
  latest_run_id?: string | null;
  latest_run_status?: string | null;
}

export interface RunSummary {
  run_id: string;
  project_id?: string;
  status: string;
  current_stage?: string;
  progress?: number;
  created_at?: string;
  has_results?: boolean;
  event_count?: number;
}

export type BackendStatus = "checking" | "online" | "offline";
