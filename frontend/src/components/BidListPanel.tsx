import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Table, Input, Tag, Space, Button, App, Select, Switch, InputNumber, Row, Col } from "antd";
import { SearchOutlined, RightOutlined, SyncOutlined, FilterOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { bidsApi, type BidSummary } from "../api/bids";

interface Props {
  onSelect?: (bid: BidSummary) => void;
  onMoveToTarget?: (bid: BidSummary) => void;
}

export default function BidListPanel({ onSelect, onMoveToTarget }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [page, setPage] = useState(() => Number(searchParams.get("page")) || 1);
  const [keyword, setKeyword] = useState(() => searchParams.get("q") || "");
  const [searchText, setSearchText] = useState(() => searchParams.get("q") || "");
  const [org, setOrg] = useState(() => searchParams.get("org") || "");
  const [orgText, setOrgText] = useState(() => searchParams.get("org") || "");
  const [analysisStatus, setAnalysisStatus] = useState(() => searchParams.get("status") || "");
  const [hideExpired, setHideExpired] = useState(() => searchParams.get("hide_expired") === "true");
  const [showFilters, setShowFilters] = useState(false);
  const [minPrice, setMinPrice] = useState<number>(0);
  const [maxPrice, setMaxPrice] = useState<number>(0);

  const { message } = App.useApp();
  const queryClient = useQueryClient();

  // URL 쿼리 파라미터에 검색 상태 동기화
  useEffect(() => {
    const params: Record<string, string> = {};
    if (keyword) params.q = keyword;
    if (org) params.org = org;
    if (analysisStatus) params.status = analysisStatus;
    if (hideExpired) params.hide_expired = "true";
    if (page > 1) params.page = String(page);
    setSearchParams(params, { replace: true });
  }, [keyword, org, analysisStatus, hideExpired, page]);

  const collectMutation = useMutation({
    mutationFn: () => bidsApi.collectAll(),
    onSuccess: (res) => {
      message.success(res.data.message);
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["bids"] }), 3000);
    },
    onError: () => message.error("수집 요청 실패"),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["bids", page, keyword, org, analysisStatus, hideExpired, minPrice, maxPrice],
    queryFn: () =>
      bidsApi.list({
        page,
        size: 20,
        keyword,
        org,
        analysis_status: analysisStatus,
        hide_expired: hideExpired,
        min_price: minPrice,
        max_price: maxPrice,
      }),
    select: (res) => res.data,
    // 검토중인 공고가 있으면 5초마다 자동 갱신해 상태 변화 반영
    refetchInterval: (q) =>
      q.state.data?.data.items.some((b: BidSummary) => b.analysis_status === "processing")
        ? 5000
        : false,
  });

  const handleSearch = () => {
    setKeyword(searchText);
    setOrg(orgText);
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

  const formatShortDate = (dt: string | null) => {
    if (!dt) return "-";
    return new Date(dt).toLocaleDateString("ko-KR", {
      month: "2-digit",
      day: "2-digit",
    });
  };

  const statusColor: Record<string, string> = {
    분석완료: "green",
    목차완료: "blue",
    검토중: "processing",
    분석실패: "red",
  };

  const columns: ColumnsType<BidSummary> = [
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
          {text}
        </a>
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
      title: "등록일",
      dataIndex: "created_at",
      width: 65,
      render: formatShortDate,
    },
    {
      title: "마감일",
      dataIndex: "bid_close_dt",
      width: 110,
      render: formatDate,
    },
    {
      title: "추정가",
      dataIndex: "presmpt_prce",
      width: 70,
      render: (v, r) => formatAmount(v ?? r.asign_bdgt_amt),
    },
    {
      title: "상태",
      dataIndex: "display_status",
      width: 75,
      render: (s: string) =>
        s ? <Tag color={statusColor[s] || "default"}>{s}</Tag> : null,
    },
    {
      title: "",
      width: 36,
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
      <Space style={{ marginBottom: 12, width: "100%", flexWrap: "wrap" }}>
        <Input
          placeholder="공고명 검색"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          onPressEnter={handleSearch}
          prefix={<SearchOutlined />}
          style={{ width: 200 }}
          allowClear
        />
        <Button onClick={handleSearch} type="primary">검색</Button>
        <Button
          icon={<FilterOutlined />}
          onClick={() => setShowFilters(!showFilters)}
          type={showFilters ? "default" : "text"}
        >
          필터
        </Button>
        <Button
          icon={<SyncOutlined />}
          onClick={() => collectMutation.mutate()}
          loading={collectMutation.isPending}
        >
          공고 수집
        </Button>
      </Space>

      {showFilters && (
        <div style={{ marginBottom: 12, padding: 12, background: "#fafafa", borderRadius: 8 }}>
          <Row gutter={[12, 8]} align="middle">
            <Col>
              <Input
                placeholder="수요기관"
                value={orgText}
                onChange={(e) => setOrgText(e.target.value)}
                onPressEnter={handleSearch}
                style={{ width: 140 }}
                allowClear
              />
            </Col>
            <Col>
              <Select
                placeholder="상태"
                value={analysisStatus || undefined}
                onChange={(v) => { setAnalysisStatus(v || ""); setPage(1); }}
                allowClear
                style={{ width: 120 }}
                options={[
                  { value: "analyzed", label: "분석완료" },
                  { value: "unanalyzed", label: "미분석" },
                  { value: "outline", label: "목차완료" },
                ]}
              />
            </Col>
            <Col>
              <Space size={4}>
                <InputNumber
                  placeholder="최소 금액(만)"
                  value={minPrice > 0 ? minPrice / 10000 : undefined}
                  onChange={(v) => setMinPrice(v ? v * 10000 : 0)}
                  style={{ width: 115 }}
                />
                <span>~</span>
                <InputNumber
                  placeholder="최대 금액(만)"
                  value={maxPrice > 0 ? maxPrice / 10000 : undefined}
                  onChange={(v) => setMaxPrice(v ? v * 10000 : 0)}
                  style={{ width: 115 }}
                />
              </Space>
            </Col>
            <Col>
              <Space size={4}>
                <Switch
                  size="small"
                  checked={hideExpired}
                  onChange={(v) => { setHideExpired(v); setPage(1); }}
                />
                <span style={{ fontSize: 13 }}>마감 공고 숨김</span>
              </Space>
            </Col>
          </Row>
        </div>
      )}

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
