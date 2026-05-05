import client from "./client";

export interface BidSummary {
  id: number;
  bid_ntce_no: string;
  bid_ntce_ord: string | null;
  bid_ntce_nm: string;
  ntce_instt_nm: string | null;
  dminstt_nm: string | null;
  bid_close_dt: string | null;
  asign_bdgt_amt: number | null;
  presmpt_prce: number | null;
  created_at: string;
  display_status: string;
  analysis_status: string | null;
}

export interface BidListResponse {
  items: BidSummary[];
  total: number;
  page: number;
  size: number;
}

export interface BidSearchParams {
  keyword?: string;
  inqry_bgn_dt?: string;
  inqry_end_dt?: string;
  page_no?: number;
  num_of_rows?: number;
}

export const bidsApi = {
  list: (params: {
    page?: number;
    size?: number;
    keyword?: string;
    org?: string;
    analysis_status?: string;
    hide_expired?: boolean;
    min_price?: number;
    max_price?: number;
  }) => client.get<BidListResponse>("/bids", { params }),

  detail: (id: number) => client.get(`/bids/${id}`),

  search: (params: BidSearchParams) =>
    client.post<{ total_found: number; saved: number; message: string }>(
      "/bids/search",
      params,
    ),

  collect: (id: number) => client.post(`/bids/${id}/collect`),

  collectAll: () => client.post<{ message: string }>("/bids/collect-all"),
};
