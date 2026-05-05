import { Outlet, useLocation, useNavigate, Navigate } from "react-router-dom";
import { Layout, Menu, Button, Spin, Typography } from "antd";
import {
  DashboardOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  LogoutOutlined,
} from "@ant-design/icons";
import { useAuth } from "../hooks/useAuth";

const { Header, Content } = Layout;
const { Text, Title } = Typography;

const MENU_ITEMS = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "대시보드" },
  { key: "/projects/active", icon: <RocketOutlined />, label: "진행 프로젝트" },
  { key: "/projects/completed", icon: <CheckCircleOutlined />, label: "완료 프로젝트" },
];

export default function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, loading, logout } = useAuth();

  if (loading) return <Spin style={{ margin: "100px auto", display: "block" }} />;
  if (!user) return <Navigate to="/login" replace />;

  // 활성 메뉴 결정 (가장 길게 일치하는 prefix)
  const selectedKey =
    [...MENU_ITEMS]
      .map((i) => i.key)
      .sort((a, b) => b.length - a.length)
      .find((k) => location.pathname.startsWith(k)) || "/dashboard";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          background: "#fff",
          padding: "0 24px",
          borderBottom: "1px solid #f0f0f0",
          display: "flex",
          alignItems: "center",
          gap: 24,
          position: "sticky",
          top: 0,
          zIndex: 10,
        }}
      >
        <Title
          level={4}
          style={{ margin: 0, cursor: "pointer", flexShrink: 0 }}
          onClick={() => navigate("/dashboard")}
        >
          G2B AI
        </Title>
        <Menu
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={MENU_ITEMS}
          onClick={({ key }) => navigate(key)}
          style={{ flex: 1, borderBottom: 0, minWidth: 0 }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
          <Text>{user.name}</Text>
          <Button type="text" icon={<LogoutOutlined />} onClick={logout}>
            로그아웃
          </Button>
        </div>
      </Header>
      <Content style={{ background: "#f5f5f5" }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
