import client from "./client";

export interface Target {
  id: number;
  bid_id: number;
  assignee_id: number | null;
  assignee_name: string | null;
  status: string;
  required_staff: number | null;
  office_info: string | null;
  estimated_cost: number | null;
  bid_estimate: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  bid_ntce_nm: string | null;
  dminstt_nm: string | null;
  bid_close_dt: string | null;
  presmpt_prce: number | null;
  risk_level: string | null;
  analysis_status: string | null;
}

export interface TargetUpdate {
  status?: string;
  required_staff?: number;
  office_info?: string;
  estimated_cost?: number;
  bid_estimate?: number;
  notes?: string;
}

export const targetsApi = {
  list: (status?: string) =>
    client.get<Target[]>("/targets", { params: status ? { status } : {} }),

  create: (bid_id: number) =>
    client.post<Target>("/targets", { bid_id }),

  update: (id: number, data: TargetUpdate) =>
    client.patch<Target>(`/targets/${id}`, data),

  remove: (id: number) => client.delete(`/targets/${id}`),
};
