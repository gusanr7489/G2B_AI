import client from "./client";

export interface Analysis {
  id: number;
  bid_id: number;
  issuing_org: string | null;
  deadline: string | null;
  project_summary: string | null;
  project_scope: string | null;
  eval_criteria: Array<{ category: string; item: string; score: number }>;
  requirements: Array<{ id: string; category: string; name: string; description: string }>;
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
  analysis_status: string;
  created_at: string;
}

export interface AnalysisStatus {
  bid_id: number;
  analysis_status: string;
  risk_level: string | null;
}

export interface Outline {
  id: number;
  analysis_id: number;
  outline_data: Record<string, unknown>;
  is_ismp: boolean;
  created_at: string;
  updated_at: string;
}

export const analysesApi = {
  request: (bidId: number) => client.post(`/analyses/${bidId}`),

  get: (bidId: number) => client.get<Analysis>(`/analyses/${bidId}`),

  status: (bidId: number) =>
    client.get<AnalysisStatus>(`/analyses/${bidId}/status`),

  requestOutline: (bidId: number) =>
    client.post(`/analyses/${bidId}/outline`),

  getOutline: (bidId: number) =>
    client.get<Outline>(`/analyses/${bidId}/outline`),
};
