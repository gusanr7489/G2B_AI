import { Tree, Typography, Empty, Descriptions, Table, Tag } from "antd";
import type { DataNode } from "antd/es/tree";
import type { ColumnsType } from "antd/es/table";
import type {
  Outline,
  OutlineDataV2,
  OutlineNode,
  OutlineRequirement,
} from "../api/analyses";

const { Title, Text, Paragraph } = Typography;

interface Props {
  outline: Outline;
}

function nodesToTreeData(nodes: OutlineNode[]): DataNode[] {
  return nodes.map((node, idx) => {
    const code = node.code || node.number || "";
    return {
      key: `${code || node.title}-${idx}`,
      title: (
        <span style={{ display: "inline-flex", gap: 8, alignItems: "baseline" }}>
          <Text strong>{code}</Text>
          <span>{node.title}</span>
          {node.page_count != null && (
            <Tag style={{ marginLeft: 4 }}>{node.page_count}p</Tag>
          )}
          {node.eval_mapping && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              [{node.eval_mapping}]
            </Text>
          )}
          {node.assignee && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              ({node.assignee})
            </Text>
          )}
        </span>
      ),
      children: node.children?.length ? nodesToTreeData(node.children) : undefined,
    };
  });
}

const reqColumns: ColumnsType<OutlineRequirement> = [
  { title: "분류", dataIndex: "category", width: 140 },
  { title: "CODE", dataIndex: "code", width: 100 },
  { title: "명칭", dataIndex: "name", width: 200 },
  { title: "정의", dataIndex: "definition", width: 220 },
  { title: "상세설명", dataIndex: "detail" },
  { title: "산출정보", dataIndex: "output", width: 160 },
];

export default function OutlineView({ outline }: Props) {
  const data = outline.outline_data as OutlineDataV2;
  const main = data.main;
  const nodes = data.outline ?? [];
  const requirements = data.requirements ?? [];

  if (!main && !nodes.length && !requirements.length) {
    return <Empty description="목차 데이터가 없습니다 (재생성하세요)" />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {main && (
        <section>
          <Title level={5}>사업 개요</Title>
          <Descriptions
            bordered
            column={2}
            size="small"
            styles={{ label: { width: 120, fontWeight: 600 } }}
          >
            <Descriptions.Item label="사업명" span={2}>
              {main.project_name || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="고객명">{main.client || "-"}</Descriptions.Item>
            <Descriptions.Item label="사업기간">{main.duration || "-"}</Descriptions.Item>
            <Descriptions.Item label="용역금액">{main.amount || "-"}</Descriptions.Item>
            <Descriptions.Item label="제출일">{main.submit_date || "-"}</Descriptions.Item>
            <Descriptions.Item label="제출장소" span={2}>
              {main.submit_place || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="비고/특이사항" span={2}>
              <Paragraph style={{ margin: 0, whiteSpace: "pre-wrap" }}>
                {main.notes || "-"}
              </Paragraph>
            </Descriptions.Item>
          </Descriptions>
        </section>
      )}

      <section>
        <Title level={5}>제안 목차</Title>
        {nodes.length > 0 ? (
          <Tree
            treeData={nodesToTreeData(nodes)}
            defaultExpandAll
            showLine
            selectable={false}
          />
        ) : (
          <Text type="secondary">생성된 목차가 없습니다</Text>
        )}
      </section>

      <section>
        <Title level={5}>RFP 요구사항 ({requirements.length}건)</Title>
        {requirements.length > 0 ? (
          <Table
            columns={reqColumns}
            dataSource={requirements}
            rowKey={(r, i) => `${r.code || ""}-${i}`}
            size="small"
            pagination={false}
            scroll={{ x: "max-content" }}
          />
        ) : (
          <Text type="secondary">정리된 요구사항이 없습니다</Text>
        )}
      </section>
    </div>
  );
}
