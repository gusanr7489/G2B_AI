import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Layout, Typography, Button, App } from "antd";
import { LogoutOutlined, SearchOutlined } from "@ant-design/icons";
import BidListPanel from "../components/BidListPanel";
import TargetListPanel from "../components/TargetListPanel";
import { targetsApi } from "../api/targets";
import type { BidSummary } from "../api/bids";
import type { Target } from "../api/targets";
import { useAuth } from "../hooks/useAuth";

const { Header, Content } = Layout;
const { Title } = Typography;

export default function StaffDashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
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

  const handleBidSelect = (bid: BidSummary) => {
    navigate(`/bids/${bid.id}`);
  };

  const handleMoveToTarget = (bid: BidSummary) => {
    addTargetMutation.mutate(bid.id);
  };

  const handleTargetSelect = (target: Target) => {
    navigate(`/bids/${target.bid_id}`);
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "#fff",
          borderBottom: "1px solid #f0f0f0",
          padding: "0 24px",
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          G2B AI
        </Title>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {user?.role === "admin" && (
            <Button size="small" onClick={() => navigate("/ceo")}>
              CEO 대시보드
            </Button>
          )}
          <span>{user?.name || ""}</span>
          <Button icon={<LogoutOutlined />} onClick={logout} type="text">
            로그아웃
          </Button>
        </div>
      </Header>
      <Content style={{ display: "flex", gap: 16, padding: 24 }}>
        {/* 좌측: 현황 리스트 */}
        <div
          style={{
            flex: 1,
            background: "#fff",
            padding: 16,
            borderRadius: 8,
          }}
        >
          <Title level={5}>현황 리스트</Title>
          <BidListPanel
            onSelect={handleBidSelect}
            onMoveToTarget={handleMoveToTarget}
          />
        </div>
        {/* 우측: 대상 리스트 */}
        <div
          style={{
            flex: 1,
            background: "#fff",
            padding: 16,
            borderRadius: 8,
          }}
        >
          <Title level={5}>대상 리스트</Title>
          <TargetListPanel onSelect={handleTargetSelect} />
        </div>
      </Content>
    </Layout>
  );
}
