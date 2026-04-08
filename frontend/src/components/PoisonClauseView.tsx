import { Table, Tag, Typography, Alert } from "antd";
import type { Analysis } from "../api/analyses";

const { Text } = Typography;

const SEVERITY_CONFIG: Record<string, { color: string; label: string }> = {
  safe: { color: "green", label: "정상" },
  caution: { color: "gold", label: "주의" },
  warning: { color: "orange", label: "경고" },
  danger: { color: "red", label: "위험" },
};

interface Props {
  analysis: Analysis;
}

export default function PoisonClauseView({ analysis }: Props) {
  const poison = analysis.poison_clauses;
  if (!poison) return <Text type="secondary">독소조항 분석 결과가 없습니다</Text>;

  const riskConfig = SEVERITY_CONFIG[poison.risk_level] || SEVERITY_CONFIG.safe;

  const columns = [
    {
      title: "카테고리",
      dataIndex: "category",
      width: 90,
    },
    {
      title: "조항 내용",
      dataIndex: "clause",
      ellipsis: true,
    },
    {
      title: "심각도",
      dataIndex: "severity",
      width: 75,
      render: (v: string) => {
        const cfg = SEVERITY_CONFIG[v] || SEVERITY_CONFIG.safe;
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: "판단 근거",
      dataIndex: "reason",
      ellipsis: true,
    },
    {
      title: "출처",
      dataIndex: "source",
      width: 110,
      ellipsis: true,
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Alert
        message={
          <span>
            종합 위험도:{" "}
            <Tag color={riskConfig.color} style={{ fontSize: 14 }}>
              {riskConfig.label.toUpperCase()}
            </Tag>
          </span>
        }
        description={poison.summary}
        type={
          poison.risk_level === "danger"
            ? "error"
            : poison.risk_level === "warning"
              ? "warning"
              : "info"
        }
        showIcon
      />

      {poison.items && poison.items.length > 0 && (
        <Table
          columns={columns}
          dataSource={poison.items}
          rowKey={(_, i) => String(i)}
          size="small"
          pagination={false}
        />
      )}
    </div>
  );
}
