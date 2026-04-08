import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Typography,
  Tabs,
  Button,
  Descriptions,
  Tag,
  Spin,
  App,
  Space,
} from "antd";
import { ArrowLeftOutlined, RobotOutlined, FileTextOutlined, CloudDownloadOutlined } from "@ant-design/icons";
import { bidsApi } from "../api/bids";
import { analysesApi, type Analysis, type Outline } from "../api/analyses";
import AnalysisView from "../components/AnalysisView";
import PoisonClauseView from "../components/PoisonClauseView";
import OutlineView from "../components/OutlineView";

const { Title, Text } = Typography;

const RISK_COLORS: Record<string, string> = {
  caution: "gold",
  warning: "orange",
  danger: "red",
};

export default function BidDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const bidId = Number(id);

  const { data: bid, isLoading: bidLoading } = useQuery({
    queryKey: ["bid", bidId],
    queryFn: () => bidsApi.detail(bidId),
    select: (res) => res.data,
    enabled: !!bidId,
  });

  const {
    data: analysis,
    isLoading: analysisLoading,
    refetch: refetchAnalysis,
  } = useQuery({
    queryKey: ["analysis", bidId],
    queryFn: () => analysesApi.get(bidId),
    select: (res) => res.data,
    enabled: !!bidId,
    retry: false,
  });

  const { data: outline, refetch: refetchOutline } = useQuery({
    queryKey: ["outline", bidId],
    queryFn: () => analysesApi.getOutline(bidId),
    select: (res) => res.data,
    enabled: !!bidId,
    retry: false,
  });

  const collectMutation = useMutation({
    mutationFn: () => bidsApi.collect(bidId),
    onSuccess: () => {
      message.success("첨부파일 수집 및 변환을 시작했습니다");
      setTimeout(() => {
        refetchAnalysis();
      }, 10000);
    },
    onError: () => message.error("수집 요청 실패"),
  });

  const analyzeMutation = useMutation({
    mutationFn: () => analysesApi.request(bidId),
    onSuccess: () => {
      message.success("AI 분석을 시작했습니다. 잠시 후 새로고침하세요.");
      setTimeout(() => refetchAnalysis(), 5000);
    },
    onError: () => message.error("분석 요청 실패"),
  });

  const outlineMutation = useMutation({
    mutationFn: () => analysesApi.requestOutline(bidId),
    onSuccess: () => {
      message.success("제안목차가 생성되었습니다");
      refetchOutline();
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || "목차 생성 실패");
    },
  });

  if (bidLoading) return <Spin style={{ margin: 100 }} />;
  if (!bid) return <Text>공고를 찾을 수 없습니다</Text>;

  const riskLevel = analysis?.risk_level;

  const tabItems = [
    {
      key: "analysis",
      label: "AI 분석",
      children: analysis ? (
        <AnalysisView analysis={analysis as Analysis} />
      ) : (
        <Text type="secondary">분석 결과가 없습니다. AI 분석을 요청하세요.</Text>
      ),
    },
    {
      key: "poison",
      label: (
        <span>
          독소조항{" "}
          {riskLevel && riskLevel !== "safe" && (
            <Tag color={RISK_COLORS[riskLevel] || "default"} style={{ marginLeft: 4 }}>
              {riskLevel}
            </Tag>
          )}
        </span>
      ),
      children: analysis ? (
        <PoisonClauseView analysis={analysis as Analysis} />
      ) : (
        <Text type="secondary">분석을 먼저 실행하세요.</Text>
      ),
    },
    {
      key: "outline",
      label: "제안목차",
      children: outline ? (
        <OutlineView outline={outline as Outline} />
      ) : (
        <Text type="secondary">생성된 목차가 없습니다. 분석 완료 후 목차 생성을 요청하세요.</Text>
      ),
    },
  ];

  const formatDate = (dt: string | null) =>
    dt ? new Date(dt).toLocaleString("ko-KR") : "-";

  const formatAmount = (amt: number | null) => {
    if (!amt) return "-";
    return `${(amt / 100_000_000).toFixed(2)}억원`;
  };

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate(-1)}
        type="text"
        style={{ marginBottom: 16 }}
      >
        뒤로
      </Button>

      {/* 기본 정보 */}
      <Descriptions
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              {bid.bid_ntce_nm}
            </Title>
            {riskLevel && riskLevel !== "safe" && (
              <Tag color={RISK_COLORS[riskLevel]} style={{ fontSize: 14 }}>
                {riskLevel.toUpperCase()}
              </Tag>
            )}
          </Space>
        }
        bordered
        column={2}
        size="small"
        style={{ marginBottom: 24 }}
      >
        <Descriptions.Item label="수요기관">
          {bid.dminstt_nm || bid.ntce_instt_nm || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="마감일시">
          {formatDate(bid.bid_close_dt)}
        </Descriptions.Item>
        <Descriptions.Item label="추정가격">
          {formatAmount(bid.presmpt_prce)}
        </Descriptions.Item>
        <Descriptions.Item label="배정예산">
          {formatAmount(bid.asign_bdgt_amt)}
        </Descriptions.Item>
        <Descriptions.Item label="공고번호">
          {bid.bid_ntce_no}-{bid.bid_ntce_ord}
        </Descriptions.Item>
        <Descriptions.Item label="상태">
          <Tag color={{
            new: "blue", collecting: "cyan", converting: "orange",
            analyzing: "purple", analyzed: "green", completed: "green",
            no_file: "default", failed: "red", analysis_failed: "red",
          }[bid.status] || "default"}>
            {{ new: "신규", collecting: "수집중", converting: "변환중",
               analyzing: "분석중", analyzed: "분석완료", completed: "완료",
               no_file: "첨부없음", failed: "실패", analysis_failed: "분석실패",
            }[bid.status] || bid.status}
          </Tag>
        </Descriptions.Item>
      </Descriptions>

      {/* 액션 버튼 */}
      <Space style={{ marginBottom: 24 }}>
        <Button
          icon={<CloudDownloadOutlined />}
          onClick={() => collectMutation.mutate()}
          loading={collectMutation.isPending}
          disabled={bid.status === "processing" || bid.status === "completed"}
        >
          첨부파일 수집
        </Button>
        <Button
          type="primary"
          icon={<RobotOutlined />}
          onClick={() => analyzeMutation.mutate()}
          loading={analyzeMutation.isPending}
          disabled={analysis?.analysis_status === "processing"}
        >
          AI 분석 요청
        </Button>
        <Button
          icon={<FileTextOutlined />}
          onClick={() => outlineMutation.mutate()}
          loading={outlineMutation.isPending}
          disabled={!analysis || analysis.analysis_status !== "completed"}
        >
          목차 생성
        </Button>
      </Space>

      {/* 탭 */}
      <Tabs items={tabItems} />
    </div>
  );
}
