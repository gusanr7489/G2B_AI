import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Table,
  Tag,
  Select,
  InputNumber,
  Input,
  Button,
  Popconfirm,
  App,
} from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { targetsApi, type Target, type TargetUpdate } from "../api/targets";

const STATUS_OPTIONS = ["검토필요", "검토중", "진행중", "완료"];
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

interface Props {
  onSelect?: (target: Target) => void;
}

export default function TargetListPanel({ onSelect }: Props) {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const { data: targets, isLoading } = useQuery({
    queryKey: ["targets", statusFilter],
    queryFn: () => targetsApi.list(statusFilter || undefined),
    select: (res) => res.data,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: TargetUpdate }) =>
      targetsApi.update(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["targets"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => targetsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      message.success("삭제 완료");
    },
  });

  const handleUpdate = (id: number, field: string, value: unknown) => {
    updateMutation.mutate({ id, data: { [field]: value } as TargetUpdate });
  };

  const formatAmount = (amt: number | null) => {
    if (!amt) return "";
    if (amt >= 100_000_000) return `${(amt / 100_000_000).toFixed(1)}억`;
    if (amt >= 10_000) return `${(amt / 10_000).toFixed(0)}만`;
    return amt.toLocaleString();
  };

  const formatDate = (dt: string | null) => {
    if (!dt) return "-";
    return new Date(dt).toLocaleDateString("ko-KR", {
      month: "2-digit",
      day: "2-digit",
    });
  };

  const columns: ColumnsType<Target> = [
    {
      title: "공고명",
      dataIndex: "bid_ntce_nm",
      ellipsis: true,
      render: (text, record) => (
        <a onClick={() => onSelect?.(record)}>{text || "-"}</a>
      ),
    },
    {
      title: "담당",
      dataIndex: "assignee_name",
      width: 70,
      render: (v) => v || "-",
    },
    {
      title: "마감",
      dataIndex: "bid_close_dt",
      width: 70,
      render: formatDate,
    },
    {
      title: "위험",
      dataIndex: "risk_level",
      width: 55,
      render: (v: string | null) =>
        v && v !== "safe" ? (
          <Tag color={RISK_COLORS[v] || "default"}>{v}</Tag>
        ) : null,
    },
    {
      title: "상태",
      dataIndex: "status",
      width: 100,
      render: (v: string, record) => (
        <Select
          size="small"
          value={v}
          onChange={(val) => handleUpdate(record.id, "status", val)}
          options={STATUS_OPTIONS.map((s) => ({
            label: <Tag color={STATUS_COLORS[s]}>{s}</Tag>,
            value: s,
          }))}
          style={{ width: 95 }}
        />
      ),
    },
    {
      title: "인원",
      dataIndex: "required_staff",
      width: 65,
      render: (v, record) => (
        <InputNumber
          size="small"
          value={v}
          min={0}
          style={{ width: 55 }}
          onChange={(val) => handleUpdate(record.id, "required_staff", val)}
        />
      ),
    },
    {
      title: "비용",
      dataIndex: "estimated_cost",
      width: 70,
      render: (v) => formatAmount(v),
    },
    {
      title: "",
      width: 35,
      render: (_, record) => (
        <Popconfirm
          title="삭제하시겠습니까?"
          onConfirm={() => deleteMutation.mutate(record.id)}
        >
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Select
        placeholder="상태 필터"
        allowClear
        value={statusFilter || undefined}
        onChange={(v) => setStatusFilter(v || "")}
        options={STATUS_OPTIONS.map((s) => ({ label: s, value: s }))}
        style={{ width: 130, marginBottom: 16 }}
      />
      <Table
        columns={columns}
        dataSource={targets || []}
        rowKey="id"
        size="small"
        loading={isLoading}
        pagination={false}
      />
    </div>
  );
}
