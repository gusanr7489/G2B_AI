import { Tree, Typography, Empty } from "antd";
import type { DataNode } from "antd/es/tree";
import type { Outline } from "../api/analyses";

const { Text } = Typography;

interface OutlineNode {
  level: number;
  number: string;
  title: string;
  eval_item?: string;
  eval_score?: number;
  children?: OutlineNode[];
}

interface Props {
  outline: Outline;
}

function convertToTreeData(nodes: OutlineNode[]): DataNode[] {
  return nodes.map((node) => ({
    key: node.number,
    title: (
      <span>
        <Text strong>{node.number}</Text> {node.title}
        {node.eval_item && (
          <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            [{node.eval_item} {node.eval_score}점]
          </Text>
        )}
      </span>
    ),
    children: node.children ? convertToTreeData(node.children) : [],
  }));
}

export default function OutlineView({ outline }: Props) {
  const data = outline.outline_data as { outline?: OutlineNode[]; is_ismp?: boolean };
  const nodes = data?.outline || [];

  if (!nodes.length) {
    return <Empty description="목차 데이터가 없습니다" />;
  }

  const treeData = convertToTreeData(nodes);

  return (
    <div>
      <Text type="secondary" style={{ marginBottom: 8, display: "block" }}>
        {outline.is_ismp ? "ISMP" : "ISP"} 제안목차 (L1~L4)
      </Text>
      <Tree
        treeData={treeData}
        defaultExpandAll
        showLine
        selectable={false}
      />
    </div>
  );
}
