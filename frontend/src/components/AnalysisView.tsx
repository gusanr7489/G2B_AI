import { Descriptions, Table, Tag, Typography, List } from "antd";
import type { Analysis } from "../api/analyses";

const { Text, Paragraph } = Typography;

interface Props {
  analysis: Analysis;
}

export default function AnalysisView({ analysis }: Props) {
  const evalColumns = [
    { title: "대분류", dataIndex: "category", width: 120 },
    { title: "세부항목", dataIndex: "item" },
    {
      title: "배점",
      dataIndex: "score",
      width: 70,
      render: (v: number) => <Text strong>{v}</Text>,
    },
  ];

  const reqColumns = [
    { title: "ID", dataIndex: "id", width: 90 },
    { title: "카테고리", dataIndex: "category", width: 100 },
    { title: "요구사항명", dataIndex: "name", width: 180 },
    { title: "설명", dataIndex: "description", ellipsis: true },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* 사업 개요 */}
      <Descriptions title="사업 개요" bordered column={2} size="small">
        <Descriptions.Item label="발주기관">
          {analysis.issuing_org || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="마감일시">
          {analysis.deadline
            ? new Date(analysis.deadline).toLocaleString("ko-KR")
            : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="사업 개요" span={2}>
          <Paragraph style={{ margin: 0 }}>
            {analysis.project_summary || "-"}
          </Paragraph>
        </Descriptions.Item>
        <Descriptions.Item label="사업 범위" span={2}>
          <Paragraph style={{ margin: 0 }}>
            {analysis.project_scope || "-"}
          </Paragraph>
        </Descriptions.Item>
        <Descriptions.Item label="참가 자격" span={2}>
          <Paragraph style={{ margin: 0 }}>
            {analysis.qualification || "-"}
          </Paragraph>
        </Descriptions.Item>
      </Descriptions>

      {/* 기술 요구사항 */}
      {analysis.tech_requirements && analysis.tech_requirements.length > 0 && (
        <div>
          <Text strong>기술 요구사항</Text>
          <div style={{ marginTop: 8 }}>
            {analysis.tech_requirements.map((t, i) => (
              <Tag key={i} style={{ marginBottom: 4 }}>
                {t}
              </Tag>
            ))}
          </div>
        </div>
      )}

      {/* 평가항목 */}
      {analysis.eval_criteria && analysis.eval_criteria.length > 0 && (
        <div>
          <Text strong>평가항목/배점</Text>
          <Table
            columns={evalColumns}
            dataSource={analysis.eval_criteria}
            rowKey={(_, i) => String(i)}
            size="small"
            pagination={false}
            style={{ marginTop: 8 }}
          />
        </div>
      )}

      {/* 요구사항 */}
      {analysis.requirements && analysis.requirements.length > 0 && (
        <div>
          <Text strong>요구사항 ({analysis.requirements.length}건)</Text>
          <Table
            columns={reqColumns}
            dataSource={analysis.requirements}
            rowKey="id"
            size="small"
            pagination={{ pageSize: 10, showSizeChanger: false }}
            style={{ marginTop: 8 }}
          />
        </div>
      )}
    </div>
  );
}
