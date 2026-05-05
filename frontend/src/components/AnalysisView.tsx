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
    { title: "요구사항명", dataIndex: "name", width: 180 },
    { title: "설명", dataIndex: "description" },
  ];

  // requirements가 그룹 형태인지 배열 형태인지 판별
  const isGrouped = analysis.requirements && !Array.isArray(analysis.requirements) && "groups" in analysis.requirements;
  const reqGroups = isGrouped
    ? (analysis.requirements as { groups: Array<{ group_name: string; items: Array<{ id: string; name: string; description: string }> }> }).groups
    : null;
  const reqFlat = !isGrouped && Array.isArray(analysis.requirements) ? analysis.requirements : null;
  const totalReqCount = reqGroups
    ? reqGroups.reduce((sum, g) => sum + g.items.length, 0)
    : reqFlat?.length || 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* 사업 개요 */}
      <Descriptions title="사업 개요" bordered column={2} size="small" labelStyle={{ whiteSpace: "nowrap", minWidth: 80 }}>
        <Descriptions.Item label="발주기관">
          {analysis.issuing_org || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="마감일시">
          {analysis.deadline
            ? new Date(analysis.deadline).toLocaleString("ko-KR")
            : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="사업 유형">
          {analysis.project_type || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="사업기간">
          {analysis.project_duration || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="추정가격">
          {analysis.estimated_price
            ? `${(analysis.estimated_price / 100_000_000).toFixed(2)}억원`
            : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="배정예산">
          {analysis.allocated_budget
            ? `${(analysis.allocated_budget / 100_000_000).toFixed(2)}억원`
            : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="계약방법" span={2}>
          {analysis.contract_method || "-"}
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
          <Paragraph style={{ margin: 0, whiteSpace: "pre-line" }}>
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
      {totalReqCount > 0 && (
        <div>
          <Text strong>요구사항 (총 {totalReqCount}건)</Text>
          {reqGroups ? (
            // 그룹 형태: 카테고리별로 분리 표시
            reqGroups.map((group, gi) => (
              <div key={gi} style={{ marginTop: 12 }}>
                <Tag color="blue" style={{ marginBottom: 8, fontSize: 13 }}>
                  {group.group_name} ({group.items.length}건)
                </Tag>
                <Table
                  columns={reqColumns}
                  dataSource={group.items}
                  rowKey="id"
                  size="small"
                  pagination={false}
                />
              </div>
            ))
          ) : reqFlat ? (
            // 배열 형태: 기존 방식 (하나의 테이블)
            <Table
              columns={[
                { title: "ID", dataIndex: "id", width: 90 },
                { title: "카테고리", dataIndex: "category", width: 100 },
                { title: "요구사항명", dataIndex: "name", width: 180 },
                { title: "설명", dataIndex: "description" },
              ]}
              dataSource={reqFlat}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 10, showSizeChanger: false }}
              style={{ marginTop: 8 }}
            />
          ) : null}
        </div>
      )}
    </div>
  );
}
