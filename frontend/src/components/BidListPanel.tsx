import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Table, Input, Tag, Space, Button, App } from "antd";
import { SearchOutlined, RightOutlined, SyncOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { bidsApi, type BidSummary } from "../api/bids";

interface Props {
  onSelect?: (bid: BidSummary) => void;
  onMoveToTarget?: (bid: BidSummary) => void;
}

export default function BidListPanel({ onSelect, onMoveToTarget }: Props) {
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState("");
  const [searchText, setSearchText] = useState("");
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  const collectMutation = useMutation({
    mutationFn: () => bidsApi.collectAll(),
    onSuccess: (res) => {
      message.success(res.data.message);
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["bids"] }), 3000);
    },
    onError: () => message.error("수집 요청 실패"),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["bids", page, keyword],
    queryFn: () => bidsApi.list({ page, size: 20, keyword }),
    select: (res) => res.data,
  });

  const handleSearch = () => {
    setKeyword(searchText);
    setPage(1);
  };

  const formatAmount = (amt: number | null) => {
    if (!amt) return "-";
    if (amt >= 100_000_000) return `${(amt / 100_000_000).toFixed(1)}억`;
    if (amt >= 10_000) return `${(amt / 10_000).toFixed(0)}만`;
    return amt.toLocaleString();
  };

  const formatDate = (dt: string | null) => {
    if (!dt) return "-";
    return new Date(dt).toLocaleDateString("ko-KR", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const statusColor: Record<string, string> = {
    new: "blue",
    collecting: "cyan",
    converting: "orange",
    analyzing: "purple",
    analyzed: "green",
    completed: "green",
    no_file: "default",
    failed: "red",
    analysis_failed: "red",
  };

  const statusLabel: Record<string, string> = {
    new: "신규",
    collecting: "수집중",
    converting: "변환중",
    analyzing: "분석중",
    analyzed: "분석완료",
    completed: "완료",
    no_file: "첨부없음",
    failed: "실패",
    analysis_failed: "분석실패",
  };

  const columns: ColumnsType<BidSummary> = [
    {
      title: "공고명",
      dataIndex: "bid_ntce_nm",
      ellipsis: true,
      render: (text, record) => (
        <a onClick={() => onSelect?.(record)}>{text}</a>
      ),
    },
    {
      title: "수요기관",
      dataIndex: "dminstt_nm",
      width: 120,
      ellipsis: true,
      render: (v, r) => v || r.ntce_instt_nm || "-",
    },
    {
      title: "마감일",
      dataIndex: "bid_close_dt",
      width: 110,
      render: formatDate,
    },
    {
      title: "예산",
      dataIndex: "presmpt_prce",
      width: 80,
      render: (v, r) => formatAmount(v ?? r.asign_bdgt_amt),
    },
    {
      title: "상태",
      dataIndex: "status",
      width: 70,
      render: (s: string) => <Tag color={statusColor[s] || "default"}>{statusLabel[s] || s}</Tag>,
    },
    {
      title: "",
      width: 40,
      render: (_, record) =>
        onMoveToTarget ? (
          <Button
            type="text"
            size="small"
            icon={<RightOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              onMoveToTarget(record);
              message.success("대상 리스트로 이동");
            }}
          />
        ) : null,
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, width: "100%" }}>
        <Input
          placeholder="공고명 검색"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          onPressEnter={handleSearch}
          prefix={<SearchOutlined />}
          style={{ width: 250 }}
        />
        <Button onClick={handleSearch}>검색</Button>
        <Button
          type="primary"
          icon={<SyncOutlined />}
          onClick={() => collectMutation.mutate()}
          loading={collectMutation.isPending}
        >
          공고 수집
        </Button>
      </Space>
      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        size="small"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: 20,
          total: data?.total || 0,
          onChange: setPage,
          showSizeChanger: false,
          showTotal: (total) => `총 ${total}건`,
        }}
      />
    </div>
  );
}
