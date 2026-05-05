import client from "./client";

export interface Analysis {
  id: number;
  bid_id: number;
  issuing_org: string | null;
  deadline: string | null;
  project_summary: string | null;
  project_scope: string | null;
  project_type: string | null;
  project_duration: string | null;
  estimated_price: number | null;
  allocated_budget: number | null;
  contract_method: string | null;
  eval_criteria: Array<{ category: string; item: string; score: number; eval_method?: string }>;
  requirements: {
    groups: Array<{
      group_name: string;
      items: Array<{ id: string; name: string; description: string }>;
    }>;
  } | Array<{ id: string; category: string; name: string; description: string }>;
  qualification: string | null;
  tech_requirements: string[];
  poison_clauses: {
    items: Array<{
      category: string;
      clause: string;
      severity: string;
      reason: string;
      source: string;
    }>;
    risk_level: string;
    summary: string;
  } | null;
  risk_level: string | null;
  model_used: string | null;
  analysis_status: string;
  created_at: string;
}

export interface ProgressLog {
  ts: string;
  level: string;
  message: string;
}

export interface AnalysisStatus {
  bid_id: number;
  analysis_status: string;
  risk_level: string | null;
  logs: ProgressLog[];
}

export interface OutlineMain {
  project_name: string;
  client: string;
  duration: string;
  amount: string;
  submit_date: string;
  submit_place: string;
  notes: string;
}

export interface OutlineNode {
  level?: number;
  number?: string;
  code?: string;
  title: string;
  page_count?: number | null;
  eval_mapping?: string | null;
  assignee?: string;
  children?: OutlineNode[];
}

export interface OutlineRequirement {
  category: string;
  code: string;
  name: string;
  definition: string;
  detail: string;
  output: string;
  note: string;
}

export interface OutlineDataV2 {
  main?: OutlineMain;
  outline?: OutlineNode[];
  requirements?: OutlineRequirement[];
  // 구버전 호환
  is_ismp?: boolean;
}

export interface Outline {
  id: number;
  analysis_id: number;
  outline_data: OutlineDataV2 | Record<string, unknown>;
  is_ismp: boolean;
  created_at: string;
  updated_at: string;
}

export interface SupportedOutlineType {
  code: string;
  label: string;
}

export const analysesApi = {
  request: (bidId: number) => client.post(`/analyses/${bidId}`),

  remove: (bidId: number) => client.delete(`/analyses/${bidId}`),

  get: (bidId: number) => client.get<Analysis>(`/analyses/${bidId}`),

  status: (bidId: number) =>
    client.get<AnalysisStatus>(`/analyses/${bidId}/status`),

  requestOutline: (bidId: number) =>
    client.post(`/analyses/${bidId}/outline`),

  getOutline: (bidId: number) =>
    client.get<Outline>(`/analyses/${bidId}/outline`),

  downloadOutlineExcel: (bidId: number) =>
    client.get(`/analyses/${bidId}/outline/excel`, { responseType: "blob" }),

  supportedOutlineTypes: () =>
    client.get<SupportedOutlineType[]>("/analyses/outline/supported-types"),
};
