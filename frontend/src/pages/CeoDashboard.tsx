import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Layout, Typography, Table, Tag, Button, Space, Alert } from "antd";
import { LogoutOutlined, ArrowLeftOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import client from "../api/client";
import StatsCard from "../components/StatsCard";
import { useAuth } from "../hooks/useAuth";

const { Header, Content } = Layout;
const { Title, Text } = Typography;

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

  const formatDate = (dt: unknown) => {
    if (!dt) return "-";
    return new Date(dt as string).toLocaleDateString("ko-KR", {
      month: "2-digit",
      day: "2-digit",
    });
  };

  const formatAmount = (amt: unknown) => {
    if (!amt) return "-";
    const n = amt as number;
    if (n >= 100_000_000) return `${(n / 100_000_000).toFixed(1)}억`;
    if (n >= 10_000) return `${(n / 10_000).toFixed(0)}만`;
    return n.toLocaleString();
  };

  const urgentColumns: ColumnsType<Record<string, unknown>> = [
    {
      title: "공고명",
      dataIndex: "bid_ntce_nm",
      ellipsis: true,
      render: (text, record) => (
        <a onClick={() => navigate(`/bids/${record.bid_id as number}`)}>{text}</a>
      ),
    },
    { title: "담당자", dataIndex: "assignee_name", width: 80 },
    { title: "수요기관", dataIndex: "dminstt_nm", width: 120, ellipsis: true },
    {
      title: "마감일",
      dataIndex: "bid_close_dt",
      width: 80,
      render: formatDate,
    },
    {
      title: "인원",
      dataIndex: "required_staff",
      width: 55,
      render: (v) => v || "-",
    },
    { title: "비용", dataIndex: "estimated_cost", width: 70, render: formatAmount },
    { title: "견적", dataIndex: "bid_estimate", width: 70, render: formatAmount },
    {
      title: "상태",
      dataIndex: "status",
      width: 85,
      render: (v: string) => (
        <Tag color={STATUS_COLORS[v] || "default"}>{v}</Tag>
      ),
    },
  ];

  const targetTotal = stats
    ? Object.values(stats.target_stats).reduce((a, b) => a + b, 0)
    : 0;

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
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate("/dashboard")}
            type="text"
          />
          <Title level={4} style={{ margin: 0 }}>
            CEO 대시보드
          </Title>
        </Space>
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
          <StatsCard title="총 수집 공고" value={stats?.total_bids || 0} />
          <StatsCard title="대상 합계" value={targetTotal} color="#1677ff" />
          <StatsCard
            title="검토필요"
            value={stats?.target_stats?.["검토필요"] || 0}
            color="#1677ff"
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
            value={stats?.urgent_targets?.length || 0}
            color="#cf1322"
          />
        </Space>

        {/* 마감 임박 알림 */}
        {stats?.urgent_targets && stats.urgent_targets.length > 0 && (
          <Alert
            message={`마감 임박 공고 ${stats.urgent_targets.length}건 (D-7 이내)`}
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 대상 리스트 */}
        <div style={{ background: "#fff", padding: 16, borderRadius: 8 }}>
          <Title level={5}>대상 리스트</Title>
          <Table
            columns={urgentColumns}
            dataSource={stats?.urgent_targets || []}
            rowKey="id"
            size="small"
            pagination={false}
          />
        </div>
      </Content>
    </Layout>
  );
}
