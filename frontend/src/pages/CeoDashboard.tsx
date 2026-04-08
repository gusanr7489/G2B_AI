import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Layout, Typography, Table, Tag, Button, Space, Alert } from "antd";
import { LogoutOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import client from "../api/client";
import { targetsApi, type Target } from "../api/targets";
import StatsCard from "../components/StatsCard";
import { useAuth } from "../hooks/useAuth";

const { Header, Content } = Layout;
const { Title } = Typography;

const STATUS_COLORS: Record<string, string> = {
  검토필요: "blue",
  검토중: "orange",
  진행중: "geekblue",
  완료: "green",
};
const RISK_COLORS: Record<string, string> = {
  caution: "gold",
  warning: "orange",
  danger: "red",
};

interface StatsData {
  total_bids: number;
  target_stats: Record<string, number>;
  urgent_targets: Array<Record<string, unknown>>;
}

export default function CeoDashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => client.get<StatsData>("/dashboard/stats"),
    select: (res) => res.data,
  });

  const { data: targets } = useQuery({
    queryKey: ["ceo-targets"],
    queryFn: () => targetsApi.list(),
    select: (res) => res.data,
  });

  const formatDate = (dt: string | null) => {
    if (!dt) return "-";
    return new Date(dt).toLocaleDateString("ko-KR", {
      month: "2-digit",
      day: "2-digit",
    });
  };

  const formatAmount = (amt: number | null) => {
    if (!amt) return "-";
    if (amt >= 100_000_000) return `${(amt / 100_000_000).toFixed(1)}억`;
    if (amt >= 10_000) return `${(amt / 10_000).toFixed(0)}만`;
    return amt.toLocaleString();
  };

  const columns: ColumnsType<Target> = [
    {
      title: "공고명",
      dataIndex: "bid_ntce_nm",
      ellipsis: true,
      render: (text, record) => (
        <a onClick={() => navigate(`/bids/${record.bid_id}`)}>{text}</a>
      ),
    },
    { title: "담당자", dataIndex: "assignee_name", width: 80 },
    {
      title: "마감일",
      dataIndex: "bid_close_dt",
      width: 80,
      render: formatDate,
    },
    {
      title: "위험",
      dataIndex: "risk_level",
      width: 65,
      render: (v: string | null) =>
        v && v !== "safe" ? (
          <Tag color={RISK_COLORS[v] || "default"}>{v}</Tag>
        ) : null,
    },
    {
      title: "상태",
      dataIndex: "status",
      width: 85,
      render: (v: string) => (
        <Tag color={STATUS_COLORS[v] || "default"}>{v}</Tag>
      ),
    },
    {
      title: "인원",
      dataIndex: "required_staff",
      width: 55,
      render: (v) => v || "-",
    },
    {
      title: "사무실",
      dataIndex: "office_info",
      width: 100,
      ellipsis: true,
      render: (v) => v || "-",
    },
    {
      title: "소요비용",
      dataIndex: "estimated_cost",
      width: 85,
      render: formatAmount,
    },
    {
      title: "사업견적",
      dataIndex: "bid_estimate",
      width: 85,
      render: formatAmount,
    },
  ];

  const targetTotal = stats
    ? Object.values(stats.target_stats).reduce((a, b) => a + b, 0)
    : 0;

  const urgentCount = stats?.urgent_targets?.length || 0;

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
          CEO 대시보드
        </Title>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span>{user?.name || ""}</span>
          <Button icon={<LogoutOutlined />} onClick={logout} type="text">
            로그아웃
          </Button>
        </div>
      </Header>
      <Content style={{ padding: 24 }}>
        {/* 통계 카드 */}
        <Space size="middle" wrap style={{ marginBottom: 24 }}>
          <StatsCard title="대상 합계" value={targetTotal} color="#1677ff" />
          <StatsCard
            title="검토필요"
            value={stats?.target_stats?.["검토필요"] || 0}
            color="#1677ff"
          />
          <StatsCard
            title="검토중"
            value={stats?.target_stats?.["검토중"] || 0}
            color="#fa8c16"
          />
          <StatsCard
            title="진행중"
            value={stats?.target_stats?.["진행중"] || 0}
            color="#531dab"
          />
          <StatsCard
            title="완료"
            value={stats?.target_stats?.["완료"] || 0}
            color="#389e0d"
          />
          <StatsCard
            title="마감 임박"
            value={urgentCount}
            color="#cf1322"
          />
        </Space>

        {/* 마감 임박 알림 */}
        {urgentCount > 0 && (
          <Alert
            message={`마감 임박 공고 ${urgentCount}건 (D-7 이내)`}
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 대상 리스트 (전체) */}
        <div style={{ background: "#fff", padding: 16, borderRadius: 8 }}>
          <Title level={5}>대상 리스트</Title>
          <Table
            columns={columns}
            dataSource={targets || []}
            rowKey="id"
            size="small"
            pagination={{ pageSize: 20, showTotal: (t) => `총 ${t}건` }}
          />
        </div>
      </Content>
    </Layout>
  );
}
