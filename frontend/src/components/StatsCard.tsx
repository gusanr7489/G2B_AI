import { Card, Statistic } from "antd";

interface Props {
  title: string;
  value: number | string;
  color?: string;
}

export default function StatsCard({ title, value, color }: Props) {
  return (
    <Card size="small" style={{ minWidth: 140 }}>
      <Statistic
        title={title}
        value={value}
        valueStyle={color ? { color } : undefined}
      />
    </Card>
  );
}
