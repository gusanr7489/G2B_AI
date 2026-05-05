import { useNavigate } from "react-router-dom";
import { Typography } from "antd";
import TargetListPanel from "../components/TargetListPanel";
import type { Target } from "../api/targets";

const { Title } = Typography;

export default function ActiveProjects() {
  const navigate = useNavigate();
  const handleSelect = (target: Target) => navigate(`/bids/${target.bid_id}`);

  return (
    <div style={{ padding: 24 }}>
      <section style={{ background: "#fff", padding: 16, borderRadius: 8 }}>
        <Title level={5}>진행 프로젝트</Title>
        <TargetListPanel
          onSelect={handleSelect}
          filterStatus="진행중"
          demoteOnTrash
          showRisk
          editableNotes
        />
      </section>
    </div>
  );
}
