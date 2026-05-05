import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Typography, App } from "antd";
import BidListPanel from "../components/BidListPanel";
import TargetListPanel from "../components/TargetListPanel";
import { targetsApi } from "../api/targets";
import type { BidSummary } from "../api/bids";
import type { Target } from "../api/targets";

const { Title } = Typography;

// 메인 대시보드는 검토 단계만 노출 (진행/완료는 별도 페이지)
const REVIEW_STATUSES = ["검토필요", "검토중"];

export default function StaffDashboard() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  const addTargetMutation = useMutation({
    mutationFn: (bidId: number) => targetsApi.create(bidId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      message.success("대상 리스트에 추가했습니다");
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail || "추가 실패";
      message.warning(detail);
    },
  });

  const handleBidSelect = (bid: BidSummary) => navigate(`/bids/${bid.id}`);
  const handleMoveToTarget = (bid: BidSummary) => addTargetMutation.mutate(bid.id);
  const handleTargetSelect = (target: Target) => navigate(`/bids/${target.bid_id}`);

  return (
    <div style={{ display: "flex", gap: 16, padding: 24 }}>
      <section style={panelStyle}>
        <Title level={5}>현황 리스트</Title>
        <BidListPanel onSelect={handleBidSelect} onMoveToTarget={handleMoveToTarget} />
      </section>
      <section style={panelStyle}>
        <Title level={5}>대상 리스트 (검토 단계)</Title>
        <TargetListPanel onSelect={handleTargetSelect} filterStatus={REVIEW_STATUSES} />
      </section>
    </div>
  );
}

const panelStyle: React.CSSProperties = {
  flex: 1,
  background: "#fff",
  padding: 16,
  borderRadius: 8,
};
