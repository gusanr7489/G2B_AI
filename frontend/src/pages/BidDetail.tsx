import { useState, useEffect, useRef } from "react";
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
  Popconfirm,
  Timeline,
  Card,
  Result,
} from "antd";
import { ArrowLeftOutlined, RobotOutlined, FileTextOutlined, PaperClipOutlined, DownloadOutlined, ReloadOutlined, CloseCircleFilled } from "@ant-design/icons";
import { bidsApi } from "../api/bids";
import { analysesApi, type Analysis, type Outline, type ProgressLog } from "../api/analyses";
import AnalysisView from "../components/AnalysisView";
import PoisonClauseView from "../components/PoisonClauseView";
import OutlineView from "../components/OutlineView";
import client from "../api/client";

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

  const { data: bid, isLoading: bidLoading, refetch: refetchBid } = useQuery({
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

  const [analysisPolling, setAnalysisPolling] = useState(false);
  const [outlinePolling, setOutlinePolling] = useState(false);
  const [progressLogs, setProgressLogs] = useState<ProgressLog[]>([]);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const outlinePollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 목차 생성 지원 유형 (한 번만 fetch)
  const { data: supportedOutlineCodes } = useQuery({
    queryKey: ["outline-supported-types"],
    queryFn: () => analysesApi.supportedOutlineTypes(),
    select: (res) => res.data.map((t) => t.code),
    staleTime: 5 * 60 * 1000,
  });

  // 페이지 진입 시 이미 processing 상태이면 자동으로 폴링 재개
  useEffect(() => {
    if (analysis?.analysis_status === "processing" && !analysisPolling) {
      setAnalysisPolling(true);
    }
  }, [analysis?.analysis_status]);

  const analyzeMutation = useMutation({
    mutationFn: () => analysesApi.request(bidId),
    onSuccess: () => {
      message.success("AI 분석을 시작했습니다. 완료되면 자동으로 표시됩니다.");
      setProgressLogs([]);
      refetchAnalysis();
      refetchOutline();
      setAnalysisPolling(true);
    },
    onError: (err: any) => message.error(err?.response?.data?.detail || "분석 요청 실패"),
  });

  const deleteAnalysisMutation = useMutation({
    mutationFn: () => analysesApi.remove(bidId),
    onSuccess: () => {
      message.success("분석 결과를 삭제했습니다");
      refetchAnalysis();
      refetchOutline();
    },
    onError: (err: any) => message.error(err?.response?.data?.detail || "삭제 실패"),
  });

  useEffect(() => {
    if (!analysisPolling) return;
    pollingRef.current = setInterval(async () => {
      try {
        const res = await analysesApi.status(bidId);
        setProgressLogs(res.data.logs || []);
        const status = res.data.analysis_status;
        if (status === "completed") {
          setAnalysisPolling(false);
          refetchAnalysis();
          message.success("AI 분석이 완료되었습니다");
        } else if (status === "failed") {
          setAnalysisPolling(false);
          message.error("AI 분석에 실패했습니다");
        }
      } catch {
        // 무시
      }
    }, 2000);
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [analysisPolling]);

  const outlineMutation = useMutation({
    mutationFn: () => analysesApi.requestOutline(bidId),
    onSuccess: () => {
      message.success("목차 생성을 시작했습니다. 완료되면 자동으로 표시됩니다.");
      setProgressLogs([]);
      setOutlinePolling(true);
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || "목차 생성 실패");
    },
  });

  // 목차 생성 폴링 — outline GET이 200으로 응답하면 종료, 로그에 error 레벨이면 실패 처리
  useEffect(() => {
    if (!outlinePolling) return;
    outlinePollingRef.current = setInterval(async () => {
      try {
        const statusRes = await analysesApi.status(bidId);
        const logs = statusRes.data.logs || [];
        setProgressLogs(logs);

        const last = logs[logs.length - 1];
        if (last?.level === "error") {
          setOutlinePolling(false);
          message.error(last.message);
          return;
        }

        try {
          await analysesApi.getOutline(bidId);
          // 200이면 생성 완료
          setOutlinePolling(false);
          refetchOutline();
          message.success("제안목차가 생성되었습니다");
        } catch {
          // 404 → 아직 진행 중
        }
      } catch {
        // 네트워크 에러 무시
      }
    }, 2000);
    return () => {
      if (outlinePollingRef.current) clearInterval(outlinePollingRef.current);
    };
  }, [outlinePolling, bidId]);

  // 엑셀 다운로드
  const handleDownloadExcel = async () => {
    try {
      const res = await analysesApi.downloadOutlineExcel(bidId);
      const blob = new Blob([res.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `(제안목차) ${bid?.bid_ntce_nm || "outline"}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || "다운로드 실패");
    }
  };

  if (bidLoading) return <Spin style={{ margin: 100 }} />;
  if (!bid) return <Text>공고를 찾을 수 없습니다</Text>;

  const riskLevel = analysis?.risk_level;
  const analysisState: "none" | "processing" | "failed" | "completed" = !analysis
    ? "none"
    : analysis.analysis_status === "processing"
      ? "processing"
      : analysis.analysis_status === "failed"
        ? "failed"
        : "completed";

  const failureView = (
    <Result
      status="error"
      icon={<CloseCircleFilled style={{ color: "#ff4d4f" }} />}
      title="AI 분석에 실패했습니다"
      extra={
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          loading={analyzeMutation.isPending}
          onClick={() => analyzeMutation.mutate()}
        >
          다시 분석 요청
        </Button>
      }
    />
  );

  const processingView = (
    <Result
      icon={<Spin size="large" />}
      title="AI가 분석 중입니다"
      subTitle="완료되면 자동으로 결과가 표시됩니다. 페이지를 떠나도 진행됩니다."
    />
  );

  const tabItems = [
    {
      key: "analysis",
      label: "AI 분석",
      children:
        analysisState === "completed" ? (
          <AnalysisView analysis={analysis as Analysis} />
        ) : analysisState === "processing" ? (
          processingView
        ) : analysisState === "failed" ? (
          failureView
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
      children:
        analysisState === "completed" ? (
          <PoisonClauseView analysis={analysis as Analysis} />
        ) : analysisState === "processing" ? (
          processingView
        ) : analysisState === "failed" ? (
          failureView
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
            new: "blue", collecting: "cyan", collected: "geekblue", converting: "orange",
            analyzing: "purple", analyzed: "green", completed: "green",
            no_file: "default", failed: "red", analysis_failed: "red",
          }[bid.status] || "default"}>
            {{ new: "신규", collecting: "수집중", collected: "수집완료", converting: "변환중",
               analyzing: "분석중", analyzed: "분석완료", completed: "완료",
               no_file: "첨부없음", failed: "실패", analysis_failed: "분석실패",
            }[bid.status] || bid.status}
          </Tag>
        </Descriptions.Item>
      </Descriptions>

      {/* 분석 모델 정보 */}
      {analysis?.model_used && analysis.analysis_status === "completed" && (
        <div style={{ marginBottom: 12, fontSize: 12, color: "#888" }}>
          <Tag style={{ fontSize: 11 }}>분석 모델</Tag>
          <Text code style={{ fontSize: 12 }}>{analysis.model_used}</Text>
        </div>
      )}

      {/* 액션 버튼 */}
      <Space style={{ marginBottom: 24 }}>
        {analysis?.analysis_status === "completed" ? (
          <Popconfirm
            title="기존 분석 결과를 삭제하고 다시 분석하시겠습니까?"
            description="현재 분석 결과와 제안목차가 함께 삭제됩니다."
            okText="재분석"
            cancelText="취소"
            onConfirm={() => analyzeMutation.mutate()}
          >
            <Button
              type="primary"
              icon={<RobotOutlined />}
              loading={analyzeMutation.isPending}
              disabled={analysisPolling}
            >
              AI 재분석
            </Button>
          </Popconfirm>
        ) : (
          <Button
            type="primary"
            icon={<RobotOutlined />}
            onClick={() => analyzeMutation.mutate()}
            loading={analyzeMutation.isPending}
            disabled={analysisPolling || analysis?.analysis_status === "processing"}
          >
            AI 분석 요청
          </Button>
        )}
        {analysis && analysis.analysis_status !== "processing" && (
          <Popconfirm
            title="분석 결과를 삭제하시겠습니까?"
            description="제안목차도 함께 삭제됩니다."
            okText="삭제"
            okButtonProps={{ danger: true }}
            cancelText="취소"
            onConfirm={() => deleteAnalysisMutation.mutate()}
          >
            <Button
              danger
              loading={deleteAnalysisMutation.isPending}
              disabled={analysisPolling}
            >
              분석 결과 삭제
            </Button>
          </Popconfirm>
        )}
        {(() => {
          const projectType = analysis?.project_type ?? null;
          const outlineSupported =
            !!projectType && supportedOutlineCodes?.includes(projectType);
          const tooltipMsg = !analysis
            ? undefined
            : analysis.analysis_status !== "completed"
              ? "AI 분석 완료 후 사용 가능합니다"
              : !outlineSupported
                ? `${projectType || "미정"} 유형은 목차 생성을 지원하지 않습니다`
                : undefined;
          return (
            <Button
              icon={<FileTextOutlined />}
              onClick={() => outlineMutation.mutate()}
              loading={outlineMutation.isPending || outlinePolling}
              disabled={
                !analysis ||
                analysis.analysis_status !== "completed" ||
                !outlineSupported
              }
              title={tooltipMsg}
            >
              {outline ? "목차 재생성" : "목차 생성"}
            </Button>
          );
        })()}
        {outline && (
          <Button
            icon={<DownloadOutlined />}
            onClick={handleDownloadExcel}
            disabled={outlinePolling}
          >
            엑셀 다운로드
          </Button>
        )}
      </Space>

      {/* 진행 로그 */}
      {(analysisPolling || outlinePolling || progressLogs.length > 0) && (
        <Card
          size="small"
          title={
            <Space>
              {(analysisPolling || outlinePolling) && <Spin size="small" />}
              <Text strong>
                {outlinePolling ? "목차 생성 진행 로그" : "분석 진행 로그"}
              </Text>
              {!analysisPolling && !outlinePolling && progressLogs.length > 0 && (
                <Button
                  type="link"
                  size="small"
                  onClick={() => setProgressLogs([])}
                  style={{ padding: 0 }}
                >
                  지우기
                </Button>
              )}
            </Space>
          }
          style={{ marginBottom: 24, maxHeight: 280, overflowY: "auto" }}
        >
          {progressLogs.length === 0 ? (
            <Text type="secondary">대기 중...</Text>
          ) : (
            <Timeline
              items={progressLogs.map((log) => ({
                color:
                  log.level === "error"
                    ? "red"
                    : log.level === "warning"
                    ? "orange"
                    : log.level === "success"
                    ? "green"
                    : "blue",
                children: (
                  <Space size={8}>
                    <Text type="secondary" style={{ fontSize: 12, fontFamily: "monospace" }}>
                      {new Date(log.ts).toLocaleTimeString("ko-KR", { hour12: false })}
                    </Text>
                    <Text>{log.message}</Text>
                  </Space>
                ),
              }))}
            />
          )}
        </Card>
      )}

      {/* 첨부파일 목록 */}
      {bid.attachments && bid.attachments.length > 0 && (
        <div style={{ marginBottom: 24, background: "#fafafa", padding: 16, borderRadius: 8 }}>
          <Text strong><PaperClipOutlined /> 첨부파일 ({bid.attachments.length}건)</Text>
          <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
            {bid.attachments.map((att: { id: number; file_name: string; file_type: string; file_url: string; conversion_status: string }) => (
              <div key={att.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Button
                  type="link"
                  icon={<DownloadOutlined />}
                  onClick={() => {
                    const token = localStorage.getItem("access_token");
                    const url = `${client.defaults.baseURL}/bids/${bidId}/attachments/${att.id}/download`;
                    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
                      .then(res => {
                        if (!res.ok) throw new Error("다운로드 실패");
                        return res.blob();
                      })
                      .then(blob => {
                        const blobUrl = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = blobUrl;
                        a.download = att.file_name;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(blobUrl);
                      })
                      .catch(() => message.error("다운로드 실패"));
                  }}
                  style={{ padding: 0 }}
                >
                  {att.file_name}
                </Button>
                <Tag>{att.file_type?.toUpperCase()}</Tag>
                <Tag color={att.conversion_status === "completed" ? "green" : att.conversion_status === "failed" ? "red" : "default"}>
                  {att.conversion_status === "completed" ? "변환완료" : att.conversion_status === "failed" ? "변환실패" : att.conversion_status}
                </Tag>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 탭 */}
      <Tabs items={tabItems} />
    </div>
  );
}
