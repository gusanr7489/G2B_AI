import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Table,
  Tag,
  Select,
  Button,
  Popconfirm,
  App,
  Typography,
  Space,
  Input,
} from "antd";
import { DeleteOutlined, ArrowUpOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { targetsApi, type Target, type TargetUpdate } from "../api/targets";

const STATUS_OPTIONS = ["검토필요", "검토중", "진행중", "완료"];

const ANALYSIS_STATE_CONFIG: Record<string, { color: string; label: string }> = {
  completed: { color: "green", label: "분석완료" },
  processing: { color: "processing", label: "분석중" },
  failed: { color: "red", label: "분석실패" },
  pending: { color: "default", label: "대기중" },
};

const RISK_COLORS: Record<string, string> = {
  caution: "gold",
  warning: "orange",
  danger: "red",
};

interface Props {
  onSelect?: (target: Target) => void;
  /** 페이지에서 고정할 상태 필터. 지정 시 필터 UI 숨김. */
  filterStatus?: string | string[];
  /**
   * true이면 휴지통 클릭이 영구 삭제가 아닌 status='검토중' 으로 되돌리기로 동작.
   * 진행 프로젝트 페이지에서 사용.
   */
  demoteOnTrash?: boolean;
  /** 위험도 컬럼 표시 여부 (진행 프로젝트 페이지 등) */
  showRisk?: boolean;
  /** 메모 컬럼(인라인 편집) 표시 여부 (진행 프로젝트 페이지) */
  editableNotes?: boolean;
}

export default function TargetListPanel({
  onSelect,
  filterStatus,
  demoteOnTrash,
  showRisk,
  editableNotes,
}: Props) {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const fixedStatus = filterStatus
    ? Array.isArray(filterStatus)
      ? filterStatus.join(",")
      : filterStatus
    : undefined;
  const effectiveStatus = fixedStatus ?? (statusFilter || undefined);

  const { data: targets, isLoading } = useQuery({
    queryKey: ["targets", effectiveStatus],
    queryFn: () => targetsApi.list(effectiveStatus),
    select: (res) => res.data,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => targetsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      message.success("삭제 완료");
    },
  });

  const demoteMutation = useMutation({
    mutationFn: (id: number) => targetsApi.update(id, { status: "검토중" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      message.success("대상 리스트로 되돌렸습니다");
    },
    onError: (err: any) =>
      message.error(err?.response?.data?.detail || "되돌리기 실패"),
  });

  const promoteMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: TargetUpdate }) =>
      targetsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      message.success("진행 프로젝트로 이동했습니다");
    },
    onError: (err: any) =>
      message.error(err?.response?.data?.detail || "이동 실패"),
  });

  const updateFieldMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: TargetUpdate }) =>
      targetsApi.update(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["targets"] }),
    onError: (err: any) =>
      message.error(err?.response?.data?.detail || "저장 실패"),
  });

  // "2.4억", "5000만", "240000000" 같은 다양한 입력을 숫자로 파싱
  const parseAmount = (raw: string): number | null => {
    const s = raw.trim();
    if (!s) return null;
    const n = Number(s.replace(/[^0-9.]/g, ""));
    if (Number.isNaN(n)) return null;
    if (s.includes("억")) return Math.round(n * 100_000_000);
    if (s.includes("만")) return Math.round(n * 10_000);
    return Math.round(n);
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
      render: (text, record) => (
        <a
          onClick={() => onSelect?.(record)}
          style={{
            whiteSpace: "normal",
            wordBreak: "keep-all",
            overflowWrap: "anywhere",
            lineHeight: 1.5,
          }}
        >
          {text || "-"}
        </a>
      ),
    },
    {
      title: "담당",
      dataIndex: "assignee_name",
      width: 70,
      render: (v) => v || "-",
    },
    ...(showRisk
      ? [
          {
            title: "위험",
            dataIndex: "risk_level",
            width: 60,
            render: (v: string | null) =>
              v && v !== "safe" ? (
                <Tag color={RISK_COLORS[v] || "default"}>{v}</Tag>
              ) : (
                "-"
              ),
          } as ColumnsType<Target>[number],
        ]
      : []),
    {
      title: "추정가",
      dataIndex: "presmpt_prce",
      width: 70,
      render: (v: number | null) => formatAmount(v),
    },
    {
      title: "예상비용",
      dataIndex: "estimated_cost",
      width: 110,
      render: (v: number | null, record) => (
        <Input
          size="small"
          defaultValue={v ? formatAmount(v) : ""}
          placeholder="2.4억 / 5000만"
          onBlur={(e) => {
            const next = parseAmount(e.target.value);
            if (next !== (v ?? null)) {
              updateFieldMutation.mutate({
                id: record.id,
                data: { estimated_cost: next ?? undefined },
              });
            }
          }}
          style={{ width: 100 }}
        />
      ),
    },
    {
      title: "마감",
      dataIndex: "bid_close_dt",
      width: 70,
      render: formatDate,
    },
    {
      title: "상태",
      dataIndex: "analysis_status",
      width: 90,
      render: (v: string | null) => {
        const cfg = ANALYSIS_STATE_CONFIG[v ?? ""] ?? {
          color: "default",
          label: "미분석",
        };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    ...(editableNotes
      ? [
          {
            title: "메모",
            dataIndex: "notes",
            width: 260,
            render: (v: string | null, record: Target) => (
              <Input.TextArea
                size="small"
                defaultValue={v || ""}
                placeholder="필요 인력, 사무실 위치 등"
                autoSize={{ minRows: 1, maxRows: 4 }}
                onBlur={(e) => {
                  const next = e.target.value;
                  if (next !== (v || "")) {
                    updateFieldMutation.mutate({
                      id: record.id,
                      data: { notes: next },
                    });
                  }
                }}
              />
            ),
          } as ColumnsType<Target>[number],
        ]
      : []),
    {
      title: "",
      width: 70,
      render: (_, record) => (
        <Space size={4}>
          {!demoteOnTrash && (
            <Button
              type="text"
              size="small"
              icon={<ArrowUpOutlined />}
              title="진행 프로젝트로 이동"
              loading={
                promoteMutation.isPending && promoteMutation.variables?.id === record.id
              }
              onClick={() =>
                promoteMutation.mutate({
                  id: record.id,
                  data: { status: "진행중" },
                })
              }
            />
          )}
          {demoteOnTrash ? (
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              title="대상 리스트로 되돌리기"
              loading={
                demoteMutation.isPending && demoteMutation.variables === record.id
              }
              onClick={() => demoteMutation.mutate(record.id)}
            />
          ) : (
            <Popconfirm
              title="삭제하시겠습니까?"
              onConfirm={() => deleteMutation.mutate(record.id)}
            >
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  const totalCount = targets?.length ?? 0;

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 12,
          height: 32,
        }}
      >
        {!fixedStatus ? (
          <Select
            placeholder="상태 필터"
            allowClear
            value={statusFilter || undefined}
            onChange={(v) => setStatusFilter(v || "")}
            options={STATUS_OPTIONS.map((s) => ({ label: s, value: s }))}
            style={{ width: 130 }}
          />
        ) : (
          <span />
        )}
        <Typography.Text type="secondary">총 {totalCount}건</Typography.Text>
      </div>
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
