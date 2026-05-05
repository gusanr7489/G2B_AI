import { useNavigate } from "react-router-dom";
import { Typography } from "antd";
import TargetListPanel from "../components/TargetListPanel";
import type { Target } from "../api/targets";

const { Title } = Typography;

export default function CompletedProjects() {
  const navigate = useNavigate();
  const handleSelect = (target: Target) => navigate(`/bids/${target.bid_id}`);

  return (
    <div style={{ padding: 24 }}>
      <section style={{ background: "#fff", padding: 16, borderRadius: 8 }}>
        <Title level={5}>완료 프로젝트</Title>
        <TargetListPanel onSelect={handleSelect} filterStatus="완료" />
      </section>
    </div>
  );
}
